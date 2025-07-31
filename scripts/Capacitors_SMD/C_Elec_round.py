#!/usr/bin/env python

import os
import argparse
import yaml
import math

from kilibs.ipc_tools import ipc_rules
from kilibs.util.toleranced_size import TolerancedSize
from KicadModTree import *  # NOQA
from KicadModTree.nodes.base.Pad import Pad  # NOQA
from scripts.tools.ipc_pad_size_calculators import ipc_gull_wing
from scripts.tools.global_config_files.global_config import DefaultGlobalConfig


def create_footprint(name, configuration, **kwargs):
    global_config = DefaultGlobalConfig()
    kicad_mod = Footprint(name, FootprintType.SMD)

    # init kicad footprint
    datasheet = ", " + kwargs['datasheet'] if 'datasheet' in kwargs else ""
    description = "SMD capacitor, aluminum electrolytic"
    tags = 'capacitor electrolytic'
    if name[:2] == "C_":
        description += " nonpolar"
        tags += " nonpolar"
    if 'extra_description' in kwargs:
        description += ", " + kwargs['extra_description']

    # ensure all provided dimensions are fully toleranced
    device_dimensions = {
        'body_length': TolerancedSize.fromYaml(kwargs, base_name='body_length'),
        'body_width': TolerancedSize.fromYaml(kwargs, base_name='body_width'),
        'body_height': TolerancedSize.fromYaml(kwargs, base_name='body_height'),
        'body_diameter': TolerancedSize.fromYaml(kwargs, base_name='body_diameter')
    }

    # for ease of use, capture nominal body and pad sizes
    body_size = {
        'length': device_dimensions['body_length'].nominal,
        'width': device_dimensions['body_width'].nominal,
        'height': device_dimensions['body_height'].nominal,
        'diameter': device_dimensions['body_diameter'].nominal
    }

    description += ", " + str(body_size['diameter']) + "x" + str(body_size['height']) + "mm"
    kicad_mod.setDescription(description + datasheet)
    kicad_mod.setTags(tags)

    # set general values
    text_offset_y = body_size['width'] / 2.0 + configuration['courtyard_offset']['default'] + 0.8

    # silkscreen REF**
    silk_text_config = global_config.get_text_properties_for_layer("F.SilkS")
    silk_text_size = silk_text_config.size_nom
    silk_text_thickness = silk_text_size * silk_text_config.thickness_ratio
    kicad_mod.append(Property(name=Property.REFERENCE, text='REF**', at=[0, -text_offset_y], layer='F.SilkS', size=[
                     silk_text_size, silk_text_size], thickness=silk_text_thickness))
    # fab value
    fab_text_config = global_config.get_text_properties_for_layer("F.Fab")
    fab_text_size = fab_text_config.size_nom
    fab_text_thickness = fab_text_size * fab_text_config.thickness_ratio
    kicad_mod.append(Property(name=Property.VALUE, text=name, at=[0, text_offset_y], layer='F.Fab', size=[
                     fab_text_size, fab_text_size], thickness=fab_text_thickness))
    # fab REF**
    fab_text_size = device_dimensions["body_diameter"].nominal / 5.0
    fab_text_size = min(fab_text_size, fab_text_config.size_max)
    fab_text_size = max(fab_text_size, fab_text_config.size_min)
    fab_text_thickness = fab_text_size * fab_text_config.thickness_ratio
    kicad_mod.append(Text(text='${REFERENCE}', at=[0, 0], layer='F.Fab', size=[
                     fab_text_size, fab_text_size], thickness=fab_text_thickness))

    # create pads
    # all pads have these properties
    pad_params = {
        "type": Pad.TYPE_SMT,
        "layers": Pad.LAYERS_SMT,
        "shape": Pad.SHAPE_RECT,
    }

    # prefer IPC-7351C compliant rounded rectangle pads
    if not configuration['force_rectangle_pads']:
        pad_params['shape'] = Pad.SHAPE_ROUNDRECT
        pad_params['round_radius_handler'] = global_config.roundrect_radius_handler

    # prefer calculating pads from lead dimensions per IPC
    # fall back to using pad sizes directly if necessary
    if ('lead_length' in kwargs) and ('lead_width' in kwargs) and ('lead_spacing' in kwargs):
        # gather IPC data (unique parameters for >= 10mm tall caps)
        ipc_density_suffix = '' if body_size['height'] < 10 else '_ge_10mm'
        ipc_device_class = 'ipc_spec_capae_crystal' + ipc_density_suffix
        ipc_offsets = ipc_definitions.get_class(ipc_device_class).get_offsets(configuration['ipc_density'])
        ipc_round_base = ipc_definitions.get_class(ipc_device_class).roundoff

        manf_tol = ipc_rules.ManufacturingTolerance(
            manufacturing_tolerance=configuration.get("manufacturing_tolerance", 0.1),
            placement_tolerance=configuration.get("placement_tolerance", 0.05),
        )

        # # fully tolerance lead dimensions; leads are dimensioned like SOIC so use gullwing calculator
        device_dimensions['lead_width'] = TolerancedSize.fromYaml(kwargs, base_name='lead_width')
        device_dimensions['lead_spacing'] = TolerancedSize.fromYaml(kwargs, base_name='lead_spacing')
        device_dimensions['lead_length'] = TolerancedSize.fromYaml(kwargs, base_name='lead_length')
        device_dimensions['lead_outside'] = TolerancedSize(maximum =
            device_dimensions['lead_spacing'].maximum +
            device_dimensions.get('lead_length').maximum * 2,
            minimum = device_dimensions['lead_spacing'].minimum +
            device_dimensions.get('lead_length').minimum * 2)

        Gmin, Zmax, Xmax = ipc_gull_wing(ipc_offsets, ipc_round_base, manf_tol,
                device_dimensions['lead_width'], device_dimensions['lead_outside'],
                lead_len=device_dimensions.get('lead_length'))

        pad_params['size'] = [(Zmax - Gmin) / 2.0, Xmax]

        x_pad_spacing = (Zmax + Gmin) / 4.0
    elif ('pad_length' in kwargs) and ('pad_width' in kwargs) and ('pad_spacing' in kwargs):
        x_pad_spacing = kwargs['pad_spacing'] / 2.0 + kwargs['pad_length'] / 2.0
        pad_params['size'] = [kwargs['pad_length'], kwargs['pad_width']]
    else:
        raise KeyError("Provide all three 'pad' or 'lead' properties ('_spacing', '_length', and '_width')")

    kicad_mod.append(Pad(number=1, at=[-x_pad_spacing, 0], **pad_params))
    kicad_mod.append(Pad(number=2, at=[x_pad_spacing, 0], **pad_params))

    # create fabrication layer
    fab_x = body_size['length'] / 2.0
    fab_y = body_size['width'] / 2.0

    if kwargs['pin1_chamfer'] == 'auto':
        fab_edge = min(fab_x/2.0, fab_y/2.0, configuration['fab_pin1_marker_length'])
    else:
        fab_edge = kwargs['pin1_chamfer']
    fab_x_edge = fab_x - fab_edge
    fab_y_edge = fab_y - fab_edge
    kicad_mod.append(Line(start=[fab_x, -fab_y], end=[fab_x, fab_y], layer='F.Fab', width=configuration['fab_line_width']))
    kicad_mod.append(Line(start=[-fab_x_edge, -fab_y], end=[fab_x, -fab_y], layer='F.Fab', width=configuration['fab_line_width']))
    kicad_mod.append(Line(start=[-fab_x_edge, fab_y], end=[fab_x, fab_y], layer='F.Fab', width=configuration['fab_line_width']))
    if fab_edge > 0:
        kicad_mod.append(Line(start=[-fab_x, -fab_y_edge], end=[-fab_x, fab_y_edge], layer='F.Fab', width=configuration['fab_line_width']))
        kicad_mod.append(Line(start=[-fab_x, -fab_y_edge], end=[-fab_x_edge, -fab_y], layer='F.Fab', width=configuration['fab_line_width']))
    kicad_mod.append(Line(start=[-fab_x, fab_y_edge], end=[-fab_x_edge, fab_y], layer='F.Fab', width=configuration['fab_line_width']))
    kicad_mod.append(Circle(center=[0, 0], radius=body_size['diameter']/2.0, layer='F.Fab', width=configuration['fab_line_width']))

    # create silkscreen
    fab_to_silk_offset = configuration['silk_fab_offset']
    silk_x = body_size['length'] / 2.0 + fab_to_silk_offset
    silk_y = body_size['width'] / 2.0 + fab_to_silk_offset
    silk_y_start = pad_params['size'][1] / 2.0 + configuration['silk_pad_clearance'] + configuration['silk_line_width']/2.0
    silk_45deg_offset = fab_to_silk_offset*math.tan(math.radians(22.5))
    silk_x_edge = fab_x - fab_edge + silk_45deg_offset
    silk_y_edge = fab_y - fab_edge + silk_45deg_offset

    kicad_mod.append(Line(start=[silk_x, silk_y], end=[silk_x, silk_y_start], layer='F.SilkS', width=configuration['silk_line_width']))
    kicad_mod.append(Line(start=[silk_x, -silk_y], end=[silk_x, -silk_y_start], layer='F.SilkS', width=configuration['silk_line_width']))
    kicad_mod.append(Line(start=[-silk_x_edge, -silk_y], end=[silk_x, -silk_y], layer='F.SilkS', width=configuration['silk_line_width']))
    kicad_mod.append(Line(start=[-silk_x_edge, silk_y], end=[silk_x, silk_y], layer='F.SilkS', width=configuration['silk_line_width']))

    if silk_y_edge > silk_y_start:
        kicad_mod.append(Line(start=[-silk_x, silk_y_edge], end=[-silk_x, silk_y_start], layer='F.SilkS', width=configuration['silk_line_width']))
        kicad_mod.append(Line(start=[-silk_x, -silk_y_edge], end=[-silk_x, -silk_y_start], layer='F.SilkS', width=configuration['silk_line_width']))

        kicad_mod.append(Line(start=[-silk_x, -silk_y_edge], end=[-silk_x_edge, -silk_y], layer='F.SilkS', width=configuration['silk_line_width']))
        kicad_mod.append(Line(start=[-silk_x, silk_y_edge], end=[-silk_x_edge, silk_y], layer='F.SilkS', width=configuration['silk_line_width']))
    else:
        silk_x_cut = silk_x - (silk_y_start - silk_y_edge) # because of the 45 degree edge we can user a simple apporach
        silk_y_edge_cut = silk_y_start

        kicad_mod.append(Line(start=[-silk_x_cut, -silk_y_edge_cut], end=[-silk_x_edge, -silk_y], layer='F.SilkS', width=configuration['silk_line_width']))
        kicad_mod.append(Line(start=[-silk_x_cut, silk_y_edge_cut], end=[-silk_x_edge, silk_y], layer='F.SilkS', width=configuration['silk_line_width']))

    # create courtyard
    courtyard_offset = configuration['courtyard_offset']['default']
    courtyard_x = body_size['length'] / 2.0 + courtyard_offset
    courtyard_y = body_size['width'] / 2.0 + courtyard_offset
    courtyard_pad_x = x_pad_spacing + pad_params['size'][0] / 2.0 + courtyard_offset
    courtyard_pad_y = pad_params['size'][1] / 2.0 + courtyard_offset
    courtyard_45deg_offset = courtyard_offset*math.tan(math.radians(22.5))
    courtyard_x_edge = fab_x - fab_edge + courtyard_45deg_offset
    courtyard_y_edge = fab_y - fab_edge + courtyard_45deg_offset
    courtyard_x_lower_edge = courtyard_x
    if courtyard_y_edge < courtyard_pad_y:
        courtyard_x_lower_edge = courtyard_x_lower_edge - courtyard_pad_y + courtyard_y_edge
        courtyard_y_edge = courtyard_pad_y
    # rounding
    courtyard_x = float(format(courtyard_x, ".2f"))
    courtyard_y = float(format(courtyard_y, ".2f"))
    courtyard_pad_x = float(format(courtyard_pad_x, ".2f"))
    courtyard_pad_y = float(format(courtyard_pad_y, ".2f"))
    courtyard_x_edge = float(format(courtyard_x_edge, ".2f"))
    courtyard_y_edge = float(format(courtyard_y_edge, ".2f"))
    courtyard_x_lower_edge = float(format(courtyard_x_lower_edge, ".2f"))

    # drawing courtyard
    kicad_mod.append(Line(start=[courtyard_x, -courtyard_y], end=[courtyard_x, -courtyard_pad_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    kicad_mod.append(Line(start=[courtyard_x, -courtyard_pad_y], end=[courtyard_pad_x, -courtyard_pad_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    kicad_mod.append(Line(start=[courtyard_pad_x, -courtyard_pad_y], end=[courtyard_pad_x, courtyard_pad_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    kicad_mod.append(Line(start=[courtyard_pad_x, courtyard_pad_y], end=[courtyard_x, courtyard_pad_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    kicad_mod.append(Line(start=[courtyard_x, courtyard_pad_y], end=[courtyard_x, courtyard_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))

    kicad_mod.append(Line(start=[-courtyard_x_edge, courtyard_y], end=[courtyard_x, courtyard_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    kicad_mod.append(Line(start=[-courtyard_x_edge, -courtyard_y], end=[courtyard_x, -courtyard_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    if fab_edge > 0:
        kicad_mod.append(Line(start=[-courtyard_x_lower_edge, courtyard_y_edge], end=[-courtyard_x_edge, courtyard_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
        kicad_mod.append(Line(start=[-courtyard_x_lower_edge, -courtyard_y_edge], end=[-courtyard_x_edge, -courtyard_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    if courtyard_y_edge > courtyard_pad_y:
        kicad_mod.append(Line(start=[-courtyard_x, -courtyard_y_edge], end=[-courtyard_x, -courtyard_pad_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
        kicad_mod.append(Line(start=[-courtyard_x, courtyard_pad_y], end=[-courtyard_x, courtyard_y_edge], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    kicad_mod.append(Line(start=[-courtyard_x_lower_edge, -courtyard_pad_y], end=[-courtyard_pad_x, -courtyard_pad_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    kicad_mod.append(Line(start=[-courtyard_pad_x, -courtyard_pad_y], end=[-courtyard_pad_x, courtyard_pad_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))
    kicad_mod.append(Line(start=[-courtyard_pad_x, courtyard_pad_y], end=[-courtyard_x_lower_edge, courtyard_pad_y], layer='F.CrtYd', width=configuration['courtyard_line_width']))

    lib_name ='Capacitor_SMD'
    # add model
    modelname = name.replace("_HandSoldering", "")
    kicad_mod.append(Model(filename="{model_prefix:s}{lib_name:s}.3dshapes/{name:s}{suffix:s}".format(model_prefix=configuration['3d_model_prefix'], lib_name=lib_name, name=modelname, suffix=global_config.model_3d_suffix),
                            at=[0, 0, 0], scale=[1, 1, 1], rotate=[0, 0, 0]))

    # write file
    lib = KicadPrettyLibrary(lib_name, None)
    lib.save(kicad_mod)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse *.kicad_mod.yml file(s) and create matching footprints')
    parser.add_argument('files', metavar='file', type=str, nargs='+', help='yml-files to parse')
    parser.add_argument('--global_config', type=str, nargs='?', help='the config file defining how the footprint will look like. (KLC)', default='../tools/global_config_files/config_KLCv3.0.yaml')
    parser.add_argument('--series_config', type=str, nargs='?', help='the config file defining series parameters.', default='../SMD_2terminal_chip_molded/package_config_KLCv3.0.yaml')
    parser.add_argument('--ipc_definition', type=str, nargs='?', help='the IPC definition file', default='ipc7351B_capae_crystal')
    parser.add_argument('--ipc_density', type=str, nargs='?', help='the IPC density', default='nominal')
    parser.add_argument('--force_rectangle_pads', action='store_true', help='Force the generation of rectangle pads instead of rounded rectangle (KiCad 4.x compatibility.)')
    #parser.add_argument('-v', '--verbose', help='show more information when creating footprint', action='store_true')
    # TODO: allow writing into sub file

    args = parser.parse_args()
    with open(args.global_config, 'r') as config_stream:
        try:
            configuration = yaml.safe_load(config_stream)
        except yaml.YAMLError as exc:
            print(exc)

    with open(args.series_config, 'r') as config_stream:
        try:
            configuration.update(yaml.safe_load(config_stream))
        except yaml.YAMLError as exc:
            print(exc)

    ipc_defs = ipc_rules.IpcRules.from_file(args.ipc_definition)
    ipc_definitions = ipc_defs

    configuration['ipc_density'] = ipc_rules.IpcDensity(args.ipc_density)
    configuration['force_rectangle_pads'] = args.force_rectangle_pads

    for filepath in args.files:
        with open(filepath, 'r') as stream:
            try:
                yaml_parsed = yaml.safe_load(stream)
                for footprint in yaml_parsed:
                    print("generate {name}.kicad_mod".format(name=footprint))
                    create_footprint(footprint, configuration , **yaml_parsed.get(footprint))
            except yaml.YAMLError as exc:
                print(exc)
