#!/usr/bin/env python3

import os
import argparse
import yaml

from KicadModTree import *
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files import global_config as GC


def roundToBase(value, base):
    return round(value/base) * base

def generate_footprint(global_config: GC.GlobalConfig, params, mpn, configuration):
    fp_params = params['footprint']
    mech_params = params['mechanical']
    part_params = params['parts'][mpn]

    if 'id' in mech_params:
        size = str(mech_params['id'])
    elif 'ext_thread' in mech_params:
        size = str(mech_params['ext_thread']['od'])

    if 'M' not in size:
        size = "{}mm".format(size)

    td = ""
    size_prefix = ""
    hole_type = "inside through hole"
    if 'thread_depth' in part_params:
        hole_type = "inside blind hole"
        td = "_ThreadDepth{}mm".format(part_params['thread_depth'])
    elif 'ext_thread' in mech_params:
        hole_type = "external"
        size_prefix = 'External'

    h = part_params['h'] if 'h' in part_params else part_params['h1']

    suffix = ''
    if 'suffix' in params:
        suffix = '_{}'.format(params['suffix'])

    fp_name = "Mounting_Wuerth_{series}-{size_prefix}{size}_H{h}mm{td}{suffix}_{mpn}".format(
                    size=size, h=h, mpn=mpn, td=td, size_prefix=size_prefix,
                    series=params['series_prefix'], suffix=suffix)

    kicad_mod = Footprint(fp_name, FootprintType.SMD)

    kicad_mod.setDescription("Mounting Hardware, {hole_type} {size}, height {h}, Wuerth electronics {mpn} ({ds:s}), generated with kicad-footprint-generator".format(size=size, h=h, mpn=mpn, ds=part_params['datasheet'], hole_type=hole_type))

    kicad_mod.setTags('Mounting {} {}'.format(size, mpn))

    kicad_mod.allow_soldermask_bridges = True

    paste_count = fp_params['ring']['paste'].get('paste_count', 4)

    kicad_mod.append(
        RingPad(
            number='1', at=(0, 0),
            size=fp_params['ring']['od'], inner_diameter=fp_params['ring']['id'],
            num_anchor=4, anchor_to_edge_clearance=0.254,
            num_paste_zones=paste_count,
            paste_round_radius_radio=0.25,
            paste_max_round_radius=0.1,
            paste_to_paste_clearance=fp_params['ring']['paste']['clearance'],
            paste_inner_diameter=fp_params['ring']['paste']['id'],
            paste_outer_diameter=fp_params['ring']['paste']['od']
            ))
    if 'npth' in fp_params:
        kicad_mod.append(
            Pad(at=[0, 0], number="",
                type=Pad.TYPE_NPTH, shape=Pad.SHAPE_CIRCLE, size=fp_params['npth'],
                drill=fp_params['npth'], layers=Pad.LAYERS_NPTH))

    kicad_mod.append(
        Circle(
            center=[0, 0], radius=mech_params['od']/2,
            layer='F.Fab', width=configuration['fab_line_width']
            ))

    ########################### CrtYd #################################
    rc = max(mech_params['od'], fp_params['ring']['od'])/2+configuration['courtyard_offset']['default']
    rc = roundToBase(rc, configuration['courtyard_grid'])


    kicad_mod.append(
        Circle(
            center=[0, 0], radius=rc,
            layer='F.CrtYd', width=configuration['courtyard_line_width']
            ))

    ########################### SilkS #################################



    ######################### Text Fields ###############################
    rb = mech_params['od']/2
    body_edge={'left':-rb, 'right':rb, 'top':-rb, 'bottom':rb}
    addTextFields(kicad_mod=kicad_mod, configuration=configuration, body_edges=body_edge,
        courtyard={'top':-rc, 'bottom':rc}, fp_name=fp_name, text_y_inside_position='center')

    ##################### Output and 3d model ############################
    model3d_path_prefix = configuration.get('3d_model_prefix',global_config.model_3d_prefix)
    model3d_path_suffix = configuration.get('3d_model_suffix',global_config.model_3d_suffix)

    lib_name = "Mounting_Wuerth"
    model_name = '{model3d_path_prefix:s}{lib_name:s}.3dshapes/{fp_name:s}{model3d_path_suffix:s}'.format(
        model3d_path_prefix=model3d_path_prefix, lib_name=lib_name, fp_name=fp_name,
        model3d_path_suffix=model3d_path_suffix)
    kicad_mod.append(Model(filename=model_name))

    lib = KicadPrettyLibrary(lib_name, None)
    lib.save(kicad_mod)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='use confing .yaml files to create footprints.')
    parser.add_argument('--global_config', type=str, nargs='?', help='the config file defining how the footprint will look like. (KLC)', default='../tools/global_config_files/config_KLCv3.0.yaml')
    parser.add_argument('--params', type=str, nargs='?',
                        default='./size_definitions/wuerth_smt_spacer.yaml',
                        help='the part definition file')
    args = parser.parse_args()

    with open(args.global_config, 'r') as config_stream:
        try:
            configuration = yaml.safe_load(config_stream)
            global_config = GC.GlobalConfig(configuration)
        except yaml.YAMLError as exc:
            print(exc)

    with open(args.params, 'r') as params_stream:
        try:
            params = yaml.safe_load(params_stream)
        except yaml.YAMLError as exc:
            print(exc)

    for series in params:
        for mpn in params[series]['parts']:
            generate_footprint(global_config, params[series], mpn, configuration)
