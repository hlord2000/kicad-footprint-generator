#!/usr/bin/env python

import os
import argparse
import yaml
import math

from kilibs.geom import Vector2D, GeomRectangle
from kilibs.ipc_tools import ipc_rules
from kilibs.util.toleranced_size import TolerancedSize
from KicadModTree import Footprint, FootprintType, \
    PolygonLine, Pad
from KicadModTree.nodes.specialized.PadArray import PadArray
from scripts.tools.declarative_def_tools import common_metadata
from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.footprint_text_fields import addTextFields


ipc_density = 'nominal'
category = 'LCC'


def roundToBase(value, base):
    return round(value/base) * base


def params_inch_to_metric(device_params):
    for key in device_params:
        if type(device_params[key]) in [int, float] and 'num_' not in key:
            device_params[key] = device_params[key]*25.4


class PLCCConfiguration:
    """
    A type that represents the configuration of a PLCC footprint
    (probably from a YAML config block).

    Over time, add more type-safe accessors to this class, and replace
    use of the raw dictionary.
    """

    _spec_dictionary: dict
    metadata: common_metadata.CommonMetadata

    def __init__(self, spec: dict):
        self.metadata = common_metadata.CommonMetadata(spec)
        self.device_type = str(spec["device_type"])

        self.num_pins_x = int(spec["num_pins_x"])
        self.num_pins_y = int(spec["num_pins_y"])
        self.pitch = float(spec["pitch"])

        unit = spec.get("units", "mm")

        self.lead_width = TolerancedSize.fromYaml(spec, base_name='lead_width', unit=unit)

        self.pad_length_addition = float(spec.get("pad_length_addition", 0))

        self.overall_x = TolerancedSize.fromYaml(spec, base_name='overall_size_x', unit=unit)
        self.overall_y = TolerancedSize.fromYaml(spec, base_name='overall_size_y', unit=unit)

        self.body_x = TolerancedSize.fromYaml(spec, base_name='body_size_x', unit=unit)
        self.body_y = TolerancedSize.fromYaml(spec, base_name='body_size_y', unit=unit)

        self.lead_inside_x = None
        self.lead_inside_y = None
        self.lead_center_distance_x = None
        self.lead_center_distance_y = None
        self.lead_length = None

        if "lead_inside_x" in spec:
            self.lead_inside_x = TolerancedSize.fromYaml(spec, base_name='lead_inside_x', unit=unit)
            self.lead_inside_y = TolerancedSize.fromYaml(spec, base_name='lead_inside_y', unit=unit)
        elif "lead_center_distance_x" in spec:
            self.lead_center_distance_x = TolerancedSize.fromYaml(spec, base_name='lead_center_distance_x', unit=unit)
            self.lead_center_distance_y = TolerancedSize.fromYaml(spec, base_name='lead_center_distance_y', unit=unit)
        else:
            self.lead_length = TolerancedSize.fromYaml(spec, base_name="lead_len", unit=unit)

        self.body_chamfer = float(spec["body_chamfer"])

        self.suffix = spec.get("suffix", None)
        self.include_suffix_in_3dpath = spec.get("include_suffix_in_3dpath", True)


class PLCCGenerator(FootprintGenerator):
    def __init__(self, configuration, ipc_rules: ipc_rules.IpcRules, **kwargs):
        super().__init__(**kwargs)

        self.configuration = configuration

        # For now, just use the legacy dict data
        self.ipc_definitions = ipc_rules.raw_data

    def calcPadDetails(self, device_config: PLCCConfiguration, ipc_data, ipc_round_base):
        # Zmax = Lmin + 2JT + √(CL^2 + F^2 + P^2)
        # Gmin = Smax − 2JH − √(CS^2 + F^2 + P^2)
        # Xmax = Wmin + 2JS + √(CW^2 + F^2 + P^2)

        # Some manufacturers do not list the terminal spacing (S) in their datasheet but list the terminal length (T)
        # Then one can calculate
        # Stol(RMS) = √(Ltol^2 + 2*^2)
        # Smin = Lmin - 2*Tmax
        # Smax(RMS) = Smin + Stol(RMS)

        F = self.configuration.get('manufacturing_tolerance', 0.1)
        P = self.configuration.get('placement_tolerance', 0.05)

        lead_width_tol = device_config.lead_width.ipc_tol

        def calcPadLength(
            overall: TolerancedSize,
            body: TolerancedSize,
            lead_inside: TolerancedSize | None = None,
            lead_center: TolerancedSize | None = None,
        ):
            overall_tol = overall.ipc_tol
            if lead_inside:
                Tmin = (overall.maximum - lead_inside.maximum)/2
                Stol_RMS = math.sqrt(overall_tol**2+lead_inside.ipc_tol**2)
                Smax_RMS = lead_inside.minimum + Stol_RMS
            elif lead_center:
                Tmin = (body.maximum - lead_center.maximum)
                Stol_RMS = math.sqrt(body.ipc_tol**2+lead_center.ipc_tol**2)
                Smax_RMS = body.maximum - 2*Tmin + Stol_RMS
            else:
                lead_len_tol = device_config.lead_length.ipc_tol
                Stol_RMS = math.sqrt(overall_tol**2+2*(lead_len_tol**2))
                Smin = overall.minimum - 2 * device_config.lead_length.maximum
                Smax_RMS = Smin + Stol_RMS

            Gmin = Smax_RMS - 2*ipc_data['heel'] - math.sqrt(Stol_RMS**2 + F**2 + P**2)

            Zmax = overall.minimum + 2*ipc_data['toe'] + math.sqrt(overall_tol**2 + F**2 + P**2)

            Zmax = roundToBase(Zmax, ipc_round_base['toe'])
            Gmin = roundToBase(Gmin, ipc_round_base['heel'])

            Zmax += device_config.pad_length_addition

            return Gmin, Zmax

        if device_config.lead_inside_x:
            Gmin_x, Zmax_x = calcPadLength(
                overall=device_config.overall_x,
                body=device_config.body_x,
                lead_inside=device_config.lead_inside_x,
            )
            Gmin_y, Zmax_y = calcPadLength(
                overall=device_config.overall_y,
                body=device_config.body_y,
                lead_inside=device_config.lead_inside_y,
            )
        elif device_config.lead_center_distance_x:
            Gmin_x, Zmax_x = calcPadLength(
                overall=device_config.overall_x,
                body=device_config.body_x,
                lead_center=device_config.lead_center_distance_x,
            )
            Gmin_y, Zmax_y = calcPadLength(
                overall=device_config.overall_y,
                body=device_config.body_y,
                lead_center=device_config.lead_center_distance_y,
            )
        else:
            Gmin_x, Zmax_x = calcPadLength(
                overall=device_config.overall_x,
                body=device_config.body_x
            )

            Gmin_y, Zmax_y = calcPadLength(
                overall=device_config.overall_y,
                body=device_config.body_y
            )

        Xmax = device_config.lead_width.minimum + 2*ipc_data['side'] + math.sqrt(lead_width_tol**2 + F**2 + P**2)
        Xmax = roundToBase(Xmax, ipc_round_base['side'])

        Pad = {}
        Pad['first'] = {'start': [-((device_config.num_pins_x-1) % 2)/2 *
                                  device_config.pitch, -(Zmax_y+Gmin_y)/4], 'size': [Xmax, (Zmax_y-Gmin_y)/2]}

        Pad['left'] = {'center': [-(Zmax_x+Gmin_x)/4, 0], 'size': [(Zmax_x-Gmin_x)/2, Xmax]}
        Pad['right'] = {'center': [(Zmax_x+Gmin_x)/4, 0], 'size': [(Zmax_x-Gmin_x)/2, Xmax]}
        Pad['top'] = {'start': [(device_config.num_pins_x-1)/2*device_config.pitch, -
                                (Zmax_y+Gmin_y)/4], 'size': [Xmax, (Zmax_y-Gmin_y)/2]}
        Pad['bottom'] = {'center': [0, (Zmax_y+Gmin_y)/4], 'size': [Xmax, (Zmax_y-Gmin_y)/2]}

        return Pad

    def generateFootprint(self, device_params: dict, pkg_id: str, header_info: dict = None):
        if device_params.get('units', 'mm') == 'inch':
            params_inch_to_metric(device_params)

        device_config = PLCCConfiguration(device_params)

        fab_line_width = self.global_config.fab_line_width
        silk_line_width = self.global_config.silk_line_width

        lib_name = self.configuration['lib_name_format_string'].format(category=category)

        size_y = device_config.body_y.nominal
        size_x = device_config.body_x.nominal

        pincount = device_config.num_pins_x*2 + device_config.num_pins_y*2

        ipc_reference = 'ipc_spec_j_lead'

        ipc_data_set = self.ipc_definitions[ipc_reference][ipc_density]
        ipc_round_base = self.ipc_definitions[ipc_reference]['round_base']

        pad_details = self.calcPadDetails(device_config, ipc_data_set, ipc_round_base)

        suffix = (device_config.suffix or "").format(pad_x=pad_details['left']['size'][0],
                                                        pad_y=pad_details['left']['size'][1])
        suffix_3d = suffix if device_config.include_suffix_in_3dpath else ""

        name_format = self.configuration['fp_name_format_string']

        fp_name = name_format.format(
            man=device_config.metadata.manufacturer or "",
            mpn=device_config.metadata.part_number or "",
            pkg=device_config.device_type,
            pincount=pincount,
            size_y=size_y,
            size_x=size_x,
            pitch=device_config.pitch,
            suffix=suffix
        ).replace('__', '_').lstrip('_')

        fp_name_2 = name_format.format(
            man=device_config.metadata.manufacturer or "",
            mpn=device_config.metadata.part_number or "",
            pkg=device_config.device_type,
            pincount=pincount,
            size_y=size_y,
            size_x=size_x,
            pitch=device_config.pitch,
            suffix=suffix_3d
        ).replace('__', '_').lstrip('_')

        model_name = fp_name_2

        kicad_mod = Footprint(fp_name, FootprintType.SMD)

        description = "{manufacturer} {mpn} {package}, {pincount} Pin".format(
            manufacturer=device_config.metadata.manufacturer or "",
            package=device_config.device_type,
            mpn=device_config.metadata.part_number or "",
            pincount=pincount,
        ).lstrip()

        if device_config.metadata.datasheet:
            description += f" ({device_config.metadata.datasheet})"

        description += ", " + self.global_config.get_generated_by_description(
            generator_name=os.path.basename(__file__)
        )

        kicad_mod.description = description

        kicad_mod.tags = (
            self.configuration["keyword_fp_string"]
            .format(
                man=device_config.metadata.manufacturer or "",
                package=device_config.device_type,
                category=category,
            )
            .lstrip()
        )

        pad_shape_details = {}
        pad_shape_details['shape'] = Pad.SHAPE_ROUNDRECT
        pad_shape_details['round_radius_handler'] = self.global_config.roundrect_radius_handler

        init = 1
        kicad_mod.append(PadArray(
            initial=init,
            type=Pad.TYPE_SMT,
            layers=Pad.LAYERS_SMT,
            pincount=int(math.ceil(device_config.num_pins_x/2)),
            x_spacing=-device_config.pitch, y_spacing=0,
            **pad_details['first'], **pad_shape_details))

        init += int(math.ceil(device_config.num_pins_x/2))
        kicad_mod.append(PadArray(
            initial=init,
            type=Pad.TYPE_SMT,
            layers=Pad.LAYERS_SMT,
            pincount=device_config.num_pins_y,
            x_spacing=0, y_spacing=device_config.pitch,
            **pad_details['left'], **pad_shape_details))

        init += device_config.num_pins_y
        kicad_mod.append(PadArray(
            initial=init,
            type=Pad.TYPE_SMT,
            layers=Pad.LAYERS_SMT,
            pincount=device_config.num_pins_x,
            y_spacing=0, x_spacing=device_config.pitch,
            **pad_details['bottom'], **pad_shape_details))

        init += device_config.num_pins_x
        kicad_mod.append(PadArray(
            initial=init,
            type=Pad.TYPE_SMT,
            layers=Pad.LAYERS_SMT,
            pincount=device_config.num_pins_y,
            x_spacing=0, y_spacing=-device_config.pitch,
            **pad_details['right'], **pad_shape_details))

        init += device_config.num_pins_y
        kicad_mod.append(PadArray(
            initial=init,
            type=Pad.TYPE_SMT,
            layers=Pad.LAYERS_SMT,
            pincount=int(math.floor(device_config.num_pins_x/2)),
            y_spacing=0, x_spacing=-device_config.pitch,
            **pad_details['top'], **pad_shape_details))

        body_rect = GeomRectangle(center=Vector2D(0,0), size=Vector2D(size_x, size_y))

        bounding_box = {
            'left': pad_details['left']['center'][0] - pad_details['left']['size'][0]/2,
            'right': pad_details['right']['center'][0] + pad_details['right']['size'][0]/2,
            'top': pad_details['top']['start'][1] - pad_details['top']['size'][1]/2,
            'bottom': pad_details['bottom']['center'][1] + pad_details['bottom']['size'][1]/2
        }

        pad_width = pad_details['top']['size'][0]
        p1_x = pad_details['first']['start'][0]

        # ############################ SilkS ##################################

        silk_offset = self.global_config.silk_fab_offset

        sx1 = -(device_config.pitch*(device_config.num_pins_x-1)/2.0
                + pad_width/2.0 + self.global_config.silk_pad_offset)

        sy1 = -(device_config.pitch*(device_config.num_pins_y-1)/2.0
                + pad_width/2.0 + self.global_config.silk_pad_offset)

        poly_silk = [
            [sx1, body_rect.top-silk_offset],
            [body_rect.left-silk_offset, body_rect.top-silk_offset],
            [body_rect.left-silk_offset, sy1]
        ]
        kicad_mod.append(PolygonLine(
            shape=poly_silk,
            width=silk_line_width,
            layer="F.SilkS", x_mirror=0))
        kicad_mod.append(PolygonLine(
            shape=poly_silk,
            width=silk_line_width,
            layer="F.SilkS", y_mirror=0))
        kicad_mod.append(PolygonLine(
            shape=poly_silk,
            width=silk_line_width,
            layer="F.SilkS", x_mirror=0, y_mirror=0))

        silk_off_45 = silk_offset / math.sqrt(2)
        poly_silk_tl = [
            [sx1, body_rect.top-silk_offset],
            [body_rect.left+device_config.body_chamfer-silk_off_45, body_rect.top-silk_offset],
            [body_rect.left-silk_offset, body_rect.top+device_config.body_chamfer-silk_off_45],
            [body_rect.left-silk_offset, sy1]
        ]

        kicad_mod.append(PolygonLine(
            shape=poly_silk_tl,
            width=silk_line_width,
            layer="F.SilkS"))

        # # ######################## Fabrication Layer ###########################

        fab_bevel_size = self.global_config.fab_bevel.get_chamfer_size(
            min(size_x, size_y)
        )
        fab_bevel_y = fab_bevel_size / math.sqrt(2)
        poly_fab = [
            [p1_x, body_rect.top+fab_bevel_y],
            [p1_x+fab_bevel_size/2, body_rect.top],
            [body_rect.right, body_rect.top],
            [body_rect.right, body_rect.bottom],
            [body_rect.left, body_rect.bottom],
            [body_rect.left, body_rect.top+device_config.body_chamfer],
            [body_rect.left+device_config.body_chamfer, body_rect.top],
            [p1_x-fab_bevel_size/2, body_rect.top],
            [p1_x, body_rect.top+fab_bevel_y]
        ]

        kicad_mod.append(PolygonLine(
            shape=poly_fab,
            width=fab_line_width,
            layer="F.Fab")
        )

        # # ############################ CrtYd ##################################

        off = ipc_data_set['courtyard']
        grid = self.global_config.courtyard_grid
        off_45 = off*math.tan(math.radians(45.0/2))

        cy1 = roundToBase(bounding_box['top']-off, grid)
        cy2 = roundToBase(body_rect.top-off, grid)
        cy3 = -roundToBase(
            device_config.pitch*(device_config.num_pins_y-1)/2.0
            + pad_width/2.0 + off, grid)
        cy4 = roundToBase(body_rect.top+device_config.body_chamfer-off_45, grid)

        cx1 = -roundToBase(
            device_config.pitch*(device_config.num_pins_x-1)/2.0
            + pad_width/2.0 + off, grid)
        cx2 = roundToBase(body_rect.left-off, grid)
        cx3 = roundToBase(bounding_box['left']-off, grid)
        cx4 = roundToBase(body_rect.left+device_config.body_chamfer-off_45, grid)

        crty_poly_tl = [
            [0, cy1],
            [cx1, cy1],
            [cx1, cy2],
            [cx2, cy2],
            [cx2, cy3],
            [cx3, cy3],
            [cx3, 0]
        ]

        kicad_mod.append(PolygonLine(shape=crty_poly_tl,
                                     layer='F.CrtYd', width=self.global_config.courtyard_line_width,
                                     x_mirror=0))
        kicad_mod.append(PolygonLine(shape=crty_poly_tl,
                                     layer='F.CrtYd', width=self.global_config.courtyard_line_width,
                                     y_mirror=0))
        kicad_mod.append(PolygonLine(shape=crty_poly_tl,
                                     layer='F.CrtYd', width=self.global_config.courtyard_line_width,
                                     x_mirror=0, y_mirror=0))

        crty_poly_tl_ch = [
            [0, cy1],
            [cx1, cy1],
            [cx1, cy2],
            [cx4, cy2],
            [cx2, cy4],
            [cx2, cy3],
            [cx3, cy3],
            [cx3, 0]
        ]
        kicad_mod.append(PolygonLine(shape=crty_poly_tl_ch,
                                     layer='F.CrtYd', width=self.global_config.courtyard_line_width))

        # ######################### Text Fields ###############################

        cy_bbox = GeomRectangle(center=Vector2D(0, 0), size=Vector2D(cx3 * 2, cy1 * 2))

        addTextFields(kicad_mod=kicad_mod, configuration=self.global_config, body_edges=body_rect,
                      courtyard=cy_bbox, fp_name=fp_name, text_y_inside_position='center')

        # #################### Output and 3d model ############################
        self.add_standard_3d_model_to_footprint(kicad_mod, lib_name, model_name)
        self.write_footprint(kicad_mod, lib_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='use confing .yaml files to create footprints.')
    parser.add_argument('files', metavar='file', type=str, nargs='*',
                        help='list of files holding information about what devices should be created.')
    parser.add_argument('--series_config', type=str, nargs='?',
                        help='the config file defining series parameters.', default='../package_config_KLCv3.yaml')
    parser.add_argument('--density', type=str, nargs='?', help='Density level (L,N,M)', default='N')
    parser.add_argument('--ipc_doc', type=str, nargs='?', help='IPC definition document',
                        default='ipc_7351b')

    args = FootprintGenerator.add_standard_arguments(parser)

    if args.density == 'L':
        ipc_density = 'least'
    elif args.density == 'M':
        ipc_density = 'most'

    with open(args.series_config, 'r') as config_stream:
        try:
            configuration = yaml.safe_load(config_stream)
        except yaml.YAMLError as exc:
            print(exc)

    ipc_rule_defs = ipc_rules.IpcRules.from_file(args.ipc_doc)

    FootprintGenerator.run_on_files(
        PLCCGenerator,
        args,
        file_autofind_dir='size_definitions',
        configuration=configuration,
        ipc_rules=ipc_rule_defs,
    )
