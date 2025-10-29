#!/usr/bin/env python3

import argparse
import yaml

from KicadModTree import *
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files import global_config as GC
from KicadModTree.util.courtyard_builder import CourtyardBuilder


# Function used to generate footprint
def generate_footprint(global_config: GC.GlobalConfig, params, part_params, mpn, configuration):

    # Build footprint name
    fp_name = "Wuerth_{series_prefix}_{mpn}_{type}_{rows}x{pins:02d}_P{pitch}mm_{orientation}".format(
        series_prefix=params['series_prefix'], mpn=mpn, type=params['type'], rows=part_params['rows'], pins=part_params['pins']//2, pitch=params['pitch'], orientation=params['orientation'])

    # Create footprint
    if params['type'] == 'SMD':
        kicad_mod = Footprint(fp_name, FootprintType.SMD)
    else:
        kicad_mod = Footprint(fp_name, FootprintType.THT)

    # Description
    kicad_mod.setDescription("Connector Wuerth, WR-PHD {pitch}mm Dual Socket Header Bottom Entry {type}, Wuerth electronics {mpn} ({datasheet}), generated with kicad-footprint-generator".format(
        pitch=params['pitch'], type=params['type'], mpn=mpn, datasheet=part_params['datasheet']))

    # Keywords
    kicad_mod.setTags("Connector Wuerth WR-PHD {pitch}mm {mpn}".format(
        pitch=params['pitch'], mpn=mpn))

    # Pads
    if params['type'] == 'SMD':
        kicad_mod.append(PadArray(initial=1, start=[-params['pitch']/2-params['holes']['offset'], -params['pitch']*(part_params['pins']//2-1)/2], y_spacing=params['pitch'], pincount=part_params['pins']//2, increment=2,
            size=[params['pads']['x'], params['pads']['y']], type=Pad.TYPE_SMT, shape=Pad.SHAPE_RECT, layers=['F.Cu', 'F.Paste', 'F.Mask']))
        kicad_mod.append(PadArray(initial=2, start=[params['pitch']/2+params['holes']['offset'], -params['pitch']*(part_params['pins']//2-1)/2], y_spacing=params['pitch'], pincount=part_params['pins']//2, increment=2,
            size=[params['pads']['x'], params['pads']['y']], type=Pad.TYPE_SMT, shape=Pad.SHAPE_RECT, layers=['F.Cu', 'F.Paste', 'F.Mask']))
    else:
        kicad_mod.append(PadArray(initial=1, start=[0, 0], y_spacing=params['pitch'], pincount=part_params['pins']//2, increment=2,
            size=[params['pads']['diameter'], params['pads']['diameter']], drill=params['pads']['drill'], type=Pad.TYPE_THT, tht_pad1_shape=Pad.SHAPE_RECT, shape=Pad.SHAPE_OVAL, layers=['*.Cu', '*.Mask']))
        kicad_mod.append(PadArray(initial=2, start=[params['pitch']+2*params['holes']['offset'], 0], y_spacing=params['pitch'], pincount=part_params['pins']//2, increment=2,
            size=[params['pads']['diameter'], params['pads']['diameter']], drill=params['pads']['drill'], type=Pad.TYPE_THT, tht_pad1_shape=Pad.SHAPE_RECT, shape=Pad.SHAPE_OVAL, layers=['*.Cu', '*.Mask']))

    # Bottom entry holes
    if params['type'] == 'SMD':
        kicad_mod.append(PadArray(initial="", start=[params['pitch']/2, -params['pitch']*(part_params['pins']//2-1)/2], y_spacing=params['pitch'], pincount=part_params['pins']//2, increment="",
            size=params['holes']['drill'], drill=params['holes']['drill'], type=Pad.TYPE_NPTH, shape=Pad.SHAPE_CIRCLE, layers=Pad.LAYERS_NPTH))
        kicad_mod.append(PadArray(initial="", start=[-params['pitch']/2, -params['pitch']*(part_params['pins']//2-1)/2], y_spacing=params['pitch'], pincount=part_params['pins']//2, increment="",
            size=params['holes']['drill'], drill=params['holes']['drill'], type=Pad.TYPE_NPTH, shape=Pad.SHAPE_CIRCLE, layers=Pad.LAYERS_NPTH))
    else:
        kicad_mod.append(PadArray(initial="", start=[params['holes']['offset'], 0], y_spacing=params['pitch'], pincount=part_params['pins']//2, increment="",
            size=params['holes']['drill'], drill=params['holes']['drill'], type=Pad.TYPE_NPTH, shape=Pad.SHAPE_CIRCLE, layers=Pad.LAYERS_NPTH))
        kicad_mod.append(PadArray(initial="", start=[params['pitch']+params['holes']['offset'], 0], y_spacing=params['pitch'], pincount=part_params['pins']//2, increment="",
            size=params['holes']['drill'], drill=params['holes']['drill'], type=Pad.TYPE_NPTH, shape=Pad.SHAPE_CIRCLE, layers=Pad.LAYERS_NPTH))

    # Add fab layer
    if params['type'] == 'SMD':
        body_top_left = [-params['width']/2, -params['top']-params['pitch']*(part_params['pins']//2-1)/2]
        body_bottom_right = [params['width']/2, params['top']+params['pitch']*(part_params['pins']//2-1)/2]
    else:
        body_top_left = [(-params['width']+params['pitch'])/2+params['holes']['offset'], -params['top']]
        body_bottom_right = [(-params['width']+params['pitch'])/2+params['width']+params['holes']['offset'], params['top']+params['pitch']*(part_params['pins']//2-1)]
    kicad_mod.append(RectLine(start=body_top_left, end=body_bottom_right, layer='F.Fab', width=configuration['fab_line_width']))

    # Add silkscreen layer
    silk_top_left = [body_top_left[0] - configuration['silk_fab_offset'], body_top_left[1] - configuration['silk_fab_offset']]
    silk_bottom_right = [body_bottom_right[0] + configuration['silk_fab_offset'], body_bottom_right[1] + configuration['silk_fab_offset']]
    # -> Top part
    kicad_mod.append(Line(start=[silk_top_left[0], silk_top_left[1]], end=[silk_bottom_right[0], silk_top_left[1]], layer='F.SilkS', width=configuration['silk_line_width']))
    kicad_mod.append(Line(start=[silk_top_left[0], silk_top_left[1]], end=[silk_top_left[0], silk_top_left[1] + 1.27/2], layer='F.SilkS', width=configuration['silk_line_width']))
    kicad_mod.append(Line(start=[silk_bottom_right[0], silk_top_left[1]], end=[silk_bottom_right[0], silk_top_left[1] + 1.27/2], layer='F.SilkS', width=configuration['silk_line_width']))
    kicad_mod.append(Line(start=[silk_top_left[0], silk_top_left[1] + 1.27/2], end=[silk_top_left[0] - 1.27/2, silk_top_left[1] + 1.27/2], layer='F.SilkS', width=configuration['silk_line_width']))
    # -> Dashes between the pads
    for x in range(0, part_params['pins']//2-1):
        if params['type'] == 'SMD':
            kicad_mod.append(Line(start=[silk_bottom_right[0], -params['pitch']*(part_params['pins']//2-1)/2 + 3*params['pitch']/8 + x * params['pitch']], end=[silk_bottom_right[0], -params['pitch']*(part_params['pins']//2-1)/2 + 3*params['pitch']/8 + params['pitch']/4 + x * params['pitch']], layer='F.SilkS', width=configuration['silk_line_width']))
            kicad_mod.append(Line(start=[silk_top_left[0], -params['pitch']*(part_params['pins']//2-1)/2 + 3*params['pitch']/8 + x * params['pitch']], end=[silk_top_left[0], -params['pitch']*(part_params['pins']//2-1)/2 + 3*params['pitch']/8 + params['pitch']/4 + x * params['pitch']], layer='F.SilkS', width=configuration['silk_line_width']))
        else:
            kicad_mod.append(Line(start=[silk_bottom_right[0], 3*params['pitch']/8 + x * params['pitch']], end=[silk_bottom_right[0], 3*params['pitch']/8 + params['pitch']/4 + x * params['pitch']], layer='F.SilkS', width=configuration['silk_line_width']))
            kicad_mod.append(Line(start=[silk_top_left[0], 3*params['pitch']/8 + x * params['pitch']], end=[silk_top_left[0], 3*params['pitch']/8 + params['pitch']/4 + x * params['pitch']], layer='F.SilkS', width=configuration['silk_line_width']))
    # -> Bottom part
    kicad_mod.append(Line(start=[silk_bottom_right[0], silk_bottom_right[1]], end=[silk_bottom_right[0], silk_bottom_right[1] - 1.27/2], layer='F.SilkS', width=configuration['silk_line_width']))
    kicad_mod.append(Line(start=[silk_top_left[0], silk_bottom_right[1]], end=[silk_top_left[0], silk_bottom_right[1] - 1.27/2], layer='F.SilkS', width=configuration['silk_line_width']))
    kicad_mod.append(Line(start=[silk_top_left[0], silk_bottom_right[1]], end=[silk_bottom_right[0], silk_bottom_right[1]], layer='F.SilkS', width=configuration['silk_line_width']))

    # Add courtyard layer
    crt_offset = global_config.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)
    cb = CourtyardBuilder.from_node(
        node=kicad_mod,
        global_config=global_config,
        offset_fab=crt_offset
        )
    kicad_mod += cb.node

    # Add texts
    body_edge={'left': body_top_left[0], 'right': body_bottom_right[0], 'top': body_top_left[1], 'bottom': body_bottom_right[1]}
    addTextFields(kicad_mod=kicad_mod, configuration=configuration, body_edges=body_edge, fp_name=fp_name, text_y_inside_position='top',
        courtyard={'top': body_edge['top'] - crt_offset, 'bottom': body_edge['bottom'] + crt_offset + 0.2})

    # 3D model definition
    lib_name = "Connector_Wuerth"
    model3d_path_prefix = configuration.get('3d_model_prefix', global_config.model_3d_prefix)
    model3d_path_suffix = configuration.get('3d_model_suffix', global_config.model_3d_suffix)
    model_name = "{model3d_path_prefix:s}{lib_name:s}.3dshapes/{fp_name:s}{model3d_path_suffix:s}".format(
        model3d_path_prefix=model3d_path_prefix, fp_name=fp_name, lib_name=lib_name,
        model3d_path_suffix=model3d_path_suffix)
    kicad_mod.append(Model(filename=model_name))

    # Create output directory

    lib = KicadPrettyLibrary(lib_name, None)
    lib.save(kicad_mod)


if __name__ == "__main__":

    # Parse arguments
    parser = argparse.ArgumentParser(description='use config .yaml files to create footprints.')
    parser.add_argument('--global_config', type=str, nargs='?', help='the config file defining how the footprint will look like. (KLC)', default='../../tools/global_config_files/config_KLCv3.0.yaml')
    parser.add_argument('--params', type=str, nargs='?', help='the part definition file', default='./wuerth_wr_phd_bottom_entry.yaml')
    args = parser.parse_args()

    # Load configuration
    with open(args.global_config, 'r') as config_stream:
        try:
            configuration = yaml.safe_load(config_stream)
            global_config = GC.GlobalConfig(configuration)
        except yaml.YAMLError as exc:
            print(exc)

    # Load yaml file for this library
    with open(args.params, 'r') as params_stream:
        try:
            params = yaml.safe_load(params_stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Create each part
    for series in params:
        for mpn in params[series]['parts']:
            generate_footprint(global_config, params[series], params[series]['parts'][mpn], mpn, configuration)
