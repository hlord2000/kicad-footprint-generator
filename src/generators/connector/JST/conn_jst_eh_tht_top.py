#!/usr/bin/env python3


import argparse
import yaml

from KicadModTree import *
from scripts.tools.drawing_tools import round_to_grid
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files import global_config as GC

series = "EH"
manufacturer = 'JST'
orientation = 'V'
number_of_rows = 1
datasheet = 'http://www.jst-mfg.com/product/pdf/eng/eEH.pdf'

pitch = 2.50
pad_to_pad_clearance = 0.8
pad_copper_y_solder_length = 0.5 #How much copper should be in y direction?
min_annular_ring = 0.15

def generate_one_footprint(global_config: GC.GlobalConfig, pincount, configuration):
    mpn = "B{pincount}B-EH-A".format(pincount=pincount)
    orientation_str = configuration['orientation_options'][orientation]
    footprint_name = configuration['fp_name_format_string'].format(man=manufacturer,
        series=series,
        mpn=mpn, num_rows=number_of_rows, pins_per_row=pincount, mounting_pad = "",
        pitch=pitch, orientation=orientation_str)

    kicad_mod = Footprint(footprint_name, FootprintType.THT)
    kicad_mod.setDescription("JST {:s} series connector, {:s} ({:s}), generated with kicad-footprint-generator".format(series, mpn, datasheet))
    kicad_mod.setTags(configuration['keyword_fp_string'].format(series=series,
        orientation=orientation_str, man=manufacturer,
        entry=configuration['entry_direction'][orientation]))


    A = (pincount - 1) * pitch
    B = A + 5.0

    # set general values


    if pincount == 2:
        drill = 1.0
    else:
        drill = 0.95

    pad_size = [pitch - pad_to_pad_clearance, drill + 2*pad_copper_y_solder_length]
    if pad_size[0] - drill < 2*min_annular_ring:
        pad_size[0] = drill + 2*min_annular_ring

    # create pads
    # kicad_mod.append(Pad(number=1, type=Pad.TYPE_THT, shape=Pad.SHAPE_RECT,
    #                     at=[0, 0], size=pad_size,
    #                     drill=drill, layers=Pad.LAYERS_THT))

    optional_pad_params = {}
    optional_pad_params['tht_pad1_shape'] = Pad.SHAPE_ROUNDRECT

    kicad_mod.append(PadArray(initial=1, start=[0, 0],
        x_spacing=pitch, pincount=pincount,
        size=pad_size, drill=drill,
        type=Pad.TYPE_THT, shape=Pad.SHAPE_OVAL, layers=Pad.LAYERS_THT,
        round_radius_handler=global_config.roundrect_radius_handler,
        **optional_pad_params))



    x1 = -2.5
    y1 = -1.6
    x2 = x1 + B
    y2 = y1 + 3.8
    body_edge={'left':x1, 'right':x2, 'top':y1, 'bottom':y2}

    #draw the main outline on F.Fab layer
    kicad_mod.append(RectLine(start={'x':x1,'y':y1}, end={'x':x2,'y':y2}, layer='F.Fab', width=configuration['fab_line_width']))
    ########################### CrtYd #################################
    cx1 = round_to_grid(x1-configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])
    cy1 = round_to_grid(y1-configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])

    cx2 = round_to_grid(x2+configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])
    cy2 = round_to_grid(y2+configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])

    kicad_mod.append(RectLine(
        start=[cx1, cy1], end=[cx2, cy2],
        layer='F.CrtYd', width=configuration['courtyard_line_width']))

    #line offset
    off = configuration['silk_fab_offset']

    x1 -= off
    y1 -= off

    x2 += off
    y2 += off

    #draw the main outline around the footprint
    kicad_mod.append(RectLine(start={'x':x1,'y':y1},end={'x':x2,'y':y2}, layer='F.SilkS', width=configuration['silk_line_width']))

    T = 0.5

    #add top line
    kicad_mod.append(PolygonLine(shape=[{ 'x': x1, 'y': 0 },
                                           {'x': x1 + T,'y': 0},
                                           {'x': x1 + T,'y': y1 + T},
                                           {'x': x2 - T,'y': y1 + T},
                                           {'x': x2 - T,'y': 0},
                                           {'x': x2,'y':0}], layer='F.SilkS', width=configuration['silk_line_width']))

    #add bottom line (left)
    kicad_mod.append(PolygonLine(shape=[{ 'x':x1, 'y': y2 - 3 * T },
                                           {'x':x1+2*T,'y':y2-3*T},
                                           {'x':x1+2*T,'y':y2}], layer='F.SilkS', width=configuration['silk_line_width']))

    #add bottom line (right)
    kicad_mod.append(PolygonLine(shape=[{ 'x':x2, 'y': y2 - 3 * T },
                                           {'x':x2-2*T,'y':y2-3*T},
                                           {'x':x2-2*T,'y':y2}], layer='F.SilkS', width=configuration['silk_line_width']))

    #add pin-1 marker
    D = 0.3
    L = 2.5
    pin = [
        {'x': x1-D,'y': y2+D-L},
        {'x': x1-D,'y': y2+D},
        {'x': x1-D+L,'y': y2+D},
    ]

    kicad_mod.append(PolygonLine(shape=pin, layer="F.SilkS", width=configuration["silk_line_width"]))
    kicad_mod.append(PolygonLine(shape=pin, layer='F.Fab', width=configuration['fab_line_width']))

    ######################### Text Fields ###############################
    addTextFields(kicad_mod=kicad_mod, configuration=configuration, body_edges=body_edge,
        courtyard={'top':cy1, 'bottom':cy2}, fp_name=footprint_name, text_y_inside_position='bottom')

    ##################### Output and 3d model ############################
    model3d_path_prefix = configuration.get('3d_model_prefix',global_config.model_3d_prefix)
    model3d_path_suffix = configuration.get('3d_model_suffix',global_config.model_3d_suffix)

    lib_name = configuration['lib_name_format_string'].format(series=series, man=manufacturer)
    model_name = '{model3d_path_prefix:s}{lib_name:s}.3dshapes/{fp_name:s}{model3d_path_suffix:s}'.format(
        model3d_path_prefix=model3d_path_prefix, lib_name=lib_name, fp_name=footprint_name,
        model3d_path_suffix=model3d_path_suffix)
    kicad_mod.append(Model(filename=model_name))

    lib = KicadPrettyLibrary(lib_name, None)
    lib.save(kicad_mod)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='use confing .yaml files to create footprints.')
    parser.add_argument('--global_config', type=str, nargs='?', help='the config file defining how the footprint will look like. (KLC)', default='../../tools/global_config_files/config_KLCv3.0.yaml')
    parser.add_argument('--series_config', type=str, nargs='?', help='the config file defining series parameters.', default='../conn_config_KLCv3.yaml')
    args = parser.parse_args()

    with open(args.global_config, 'r') as config_stream:
        try:
            configuration = yaml.safe_load(config_stream)
            global_config = GC.GlobalConfig(configuration)
        except yaml.YAMLError as exc:
            print(exc)

    with open(args.series_config, 'r') as config_stream:
        try:
            configuration.update(yaml.safe_load(config_stream))
        except yaml.YAMLError as exc:
            print(exc)

    for pincount in range(2, 16):
        generate_one_footprint(global_config, pincount, configuration)
