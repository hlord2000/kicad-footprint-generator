#!/usr/bin/env python3

#####
#
# Based on conn_ffc_molex_502250.py script
#
#####

from math import sqrt
import argparse
import yaml

from KicadModTree import (
    Footprint,
    FootprintType,
    Pad,
    PadArray,
    Model,
    RectLine,
    PolygonLine,
    KicadPrettyLibrary,
)
from scripts.tools.drawing_tools import round_to_grid
from scripts.tools.global_config_files import global_config as GC
from scripts.tools.footprint_text_fields import addTextFields

pinrange = [13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 45, 51, 55, 57, 61, 71]

series = ""
series_long = '0.30mm Pitch FFC/FPC'
manufacturer = 'Hirose'
orientation = 'H'
number_of_rows = 2

conn_category = "FFC-FPC"

lib_by_conn_category = True

part_code = "FH26-{0}S-0.3SHW"

cable_pitch = 0.3		# OK!
odd_pad_size = (0.80, 0.3) # bottom	OK!
even_pad_size = (0.65, 0.3) # top	OK!
anchor_pad_size = (0.95, 0.4)	# MP size OK!

def make_module(global_config: GC.GlobalConfig, pin_count, configuration):
    pad_silk_off = configuration['silk_line_width']/2 + configuration['silk_pad_clearance']
    off_sf = configuration['silk_fab_offset']

    datasheet='https://www.hirose.com/en/product/document?clcode=&productname=&series=FH26&documenttype=Catalog&lang=en&documentid=D49355_en'

    mpn = part_code.format(pin_count)

    orientation_str = configuration['orientation_options'][orientation]
    footprint_name = configuration['fp_name_unequal_row_format_string'].format(man=manufacturer,
        series=series,
        mpn=mpn, num_rows=number_of_rows, pins=pin_count, mounting_pad = "-1MP",
        pitch=cable_pitch*2, orientation=orientation_str)

    footprint_name = footprint_name.replace("__",'_')

    kicad_mod = Footprint(footprint_name, FootprintType.SMD)
    kicad_mod.setDescription("Hirose {:s}, {:s}, {:d} Circuits ({:s}), generated with kicad-footprint-generator".format(series_long, mpn, pin_count, datasheet))
    kicad_mod.setTags(configuration['keyword_fp_string'].format(series=series,
        orientation=orientation_str, man=manufacturer,
        entry=configuration['entry_direction'][orientation]))

    right_cutout = 0.5
    cutout = [
        [0.3,  0.6],
        [0.1,  0.45],
        [0.70, 0.19]
    ]

    silk_right_cutout = [
        [0.45, 0.4],
        [0.40, 0.65]
    ]

    pad_to_pad_outside = 3.6		# row 1 and row 2 distance outside	OK!
    row_spacing = pad_to_pad_outside - odd_pad_size[0]/2 - even_pad_size[0]/2

    odd_pad_x = -pad_to_pad_outside/2 + odd_pad_size[0]/2
    even_pad_x = odd_pad_x + row_spacing
    even_pad_right = even_pad_x + even_pad_size[0]/2

    pins_width = cable_pitch * (pin_count - 1)
    anchor_pad_spacing = pins_width + 1.4

    anchor_pad_x = odd_pad_x - odd_pad_size[0]/2 + anchor_pad_size[0]/2 + 0.2

    width = pins_width + 1.8		# overall width OK!

    body_edge = {
        'top': -width/2,
        'bottom': width/2,
        'right': even_pad_right - 0.45,
        'left': odd_pad_x - 0.5
    }

    silk_edge = {
        'top': -anchor_pad_spacing/2-anchor_pad_size[1]/2-pad_silk_off,
        'bottom': anchor_pad_spacing/2+anchor_pad_size[1]/2+pad_silk_off,
        'left': odd_pad_x-odd_pad_size[0]/2-pad_silk_off,
        'right': even_pad_right+pad_silk_off
    }

    silk_left_cutout = [-silk_edge['left']+anchor_pad_x-anchor_pad_size[0]/2-pad_silk_off, 0.75]

    bar_edge_right_delta = 1.25

    ctyd_width = anchor_pad_spacing + anchor_pad_size[1]
    bounding_box = {
        'top': -ctyd_width/2,
        'bottom': ctyd_width/2,
        'left': odd_pad_x - odd_pad_size[0]/2-0.35,
        'right': even_pad_x + even_pad_size[0]/2
    }

    # draw the bottom half of the fab layer
    # this will be mirrored later
    fab_outline = [
        {'x': body_edge['left'], 'y':0},
        {'x': body_edge['left'], 'y':body_edge['bottom']-cutout[0][1]-cutout[1][1]-cutout[2][1]},
        {'x': body_edge['left']+cutout[0][0], 'y':body_edge['bottom']-cutout[0][1]-cutout[1][1]-cutout[2][1]},
        {'x': body_edge['left']+cutout[0][0], 'y':body_edge['bottom']-cutout[1][1]-cutout[2][1]},
        {'x': body_edge['left']+cutout[0][0]+cutout[1][0], 'y':body_edge['bottom']-cutout[1][1]-cutout[2][1]},
        {'x': body_edge['left']+cutout[0][0]+cutout[1][0], 'y':body_edge['bottom']-cutout[2][1]},
        {'x': body_edge['left']+cutout[0][0]+cutout[1][0]+cutout[2][0], 'y':body_edge['bottom']-cutout[2][1]},
        {'x': body_edge['left']+cutout[0][0]+cutout[1][0]+cutout[2][0], 'y':body_edge['bottom']},
        {'x': body_edge['right'] - right_cutout, 'y':body_edge['bottom']},
        {'x': body_edge['right'] - right_cutout, 'y':body_edge['bottom'] - right_cutout},
        {'x': body_edge['right'], 'y':body_edge['bottom'] - right_cutout},
        {'x': body_edge['right'], 'y':0}
    ]

    kicad_mod.append(PolygonLine(
        shape=fab_outline,
        layer="F.Fab", width=configuration['fab_line_width']
    ))
    kicad_mod.append(PolygonLine(
        shape=fab_outline, y_mirror=0,
        layer="F.Fab", width=configuration['fab_line_width']
    ))

    # draw the bar
    bar_fab_outline = [
        {'x': body_edge['right']-bar_edge_right_delta, 'y':0},
        {'x': body_edge['right']-bar_edge_right_delta, 'y': body_edge['bottom']-cutout[2][1]},
        {'x': body_edge['left']+cutout[0][0]+cutout[1][0]+cutout[2][0], 'y': body_edge['bottom']-cutout[2][1]},
    ]

    kicad_mod.append(PolygonLine(
        shape=bar_fab_outline,
        layer="F.Fab", width=configuration['fab_line_width']
    ))
    kicad_mod.append(PolygonLine(
        shape=bar_fab_outline, y_mirror=0,
        layer="F.Fab", width=configuration['fab_line_width']
    ))

    silk_outline = [
        {'x': silk_edge['right'], 'y':0},
        {'x': silk_edge['right'], 'y':silk_edge['bottom']-silk_right_cutout[0][1]-silk_right_cutout[1][1]},
        {'x': silk_edge['right']-silk_right_cutout[0][0], 'y':silk_edge['bottom']-silk_right_cutout[0][1]-silk_right_cutout[1][1]},
        {'x': silk_edge['right']-silk_right_cutout[0][0], 'y':silk_edge['bottom']-silk_right_cutout[1][1]},
        {'x': silk_edge['right']-silk_right_cutout[0][0]-silk_right_cutout[1][0], 'y':silk_edge['bottom']-silk_right_cutout[1][1]},
        {'x': silk_edge['right']-silk_right_cutout[0][0]-silk_right_cutout[1][0], 'y':silk_edge['bottom']},
        {'x': silk_edge['left']+silk_left_cutout[0], 'y':silk_edge['bottom']},
        {'x': silk_edge['left']+silk_left_cutout[0], 'y':silk_edge['bottom']-silk_left_cutout[1]},
        {'x': silk_edge['left'], 'y':silk_edge['bottom']-silk_left_cutout[1]},
        {'x': silk_edge['left'], 'y': 0}
    ]

    kicad_mod.append(PolygonLine(
        shape=silk_outline,
        layer="F.SilkS", width=configuration['silk_line_width']
    ))
    kicad_mod.append(PolygonLine(
        shape=silk_outline, y_mirror=0,
        layer="F.SilkS", width=configuration['silk_line_width']
    ))

    even_pins = pin_count//2
    odd_pins = pin_count - even_pins
    kicad_mod.append(PadArray(
            center=[odd_pad_x,0], pincount=odd_pins,
            initial=1, increment=2, y_spacing=2*cable_pitch,
            type=Pad.TYPE_SMT, shape=Pad.SHAPE_RECT,
            size=odd_pad_size, layers=Pad.LAYERS_SMT))
    kicad_mod.append(PadArray(
            center=[even_pad_x, 0], pincount=even_pins,
            initial=2, increment=2, y_spacing=2*cable_pitch,
            type=Pad.TYPE_SMT, shape=Pad.SHAPE_RECT,
            size=even_pad_size, layers=Pad.LAYERS_SMT))

    def anchor_pad(direction):
        pad_number = global_config.get_pad_name(GC.PadName.MECHANICAL)
        kicad_mod.append(Pad(number=pad_number, type=Pad.TYPE_SMT, shape=Pad.SHAPE_RECT,
                        at=[anchor_pad_x, anchor_pad_spacing / 2 * direction],
                        size=anchor_pad_size, layers=Pad.LAYERS_SMT))
    anchor_pad(-1)
    anchor_pad(1)

    pin1_y = -pins_width/2
    ps1_m = 0.3
    p1s_x = bounding_box['left'] - pad_silk_off
    pin = [
        {'x': p1s_x -  ps1_m/sqrt(2), 'y': pin1_y-ps1_m/2},
        {'x': p1s_x, 'y': pin1_y},
        {'x': p1s_x -  ps1_m/sqrt(2), 'y': pin1_y+ps1_m/2},
        {'x': p1s_x -  ps1_m/sqrt(2), 'y': pin1_y-ps1_m/2}
    ]
    kicad_mod.append(
        PolygonLine(shape=pin, layer="F.SilkS", width=configuration["silk_line_width"])
    )

    sl=0.4
    pin1x=-0.6
    pin = [
        {'x': pin1x, 'y': pin1_y-sl/2},
        {'x': pin1x - sl/sqrt(2), 'y': pin1_y},
        {'x': pin1x, 'y': pin1_y+sl/2},
        {'x': pin1x, 'y': pin1_y-sl/2}

    ]
    kicad_mod.append(
        PolygonLine(shape=pin, width=configuration["fab_line_width"], layer="F.Fab")
    )

    ########################### CrtYd #################################
    cx1 = round_to_grid(bounding_box['left']-configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])
    cy1 = round_to_grid(bounding_box['top']-configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])

    cx2 = round_to_grid(bounding_box['right']+configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])
    cy2 = round_to_grid(bounding_box['bottom']+configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])

    kicad_mod.append(RectLine(
        start=[cx1, cy1], end=[cx2, cy2],
        layer='F.CrtYd', width=configuration['courtyard_line_width']))

    ######################### Text Fields ###############################
    addTextFields(kicad_mod=kicad_mod, configuration=configuration, body_edges=body_edge,
        courtyard={'top':cy1, 'bottom':cy2}, fp_name=footprint_name, text_y_inside_position='right')

    ##################### Output and 3d model ############################
    if lib_by_conn_category:
        lib_name = configuration['lib_name_specific_function_format_string'].format(category=conn_category)
    else:
        lib_name = configuration['lib_name_format_string'].format(series=series, man=manufacturer)

    model_name = '{model3d_path_prefix:s}{lib_name:s}.3dshapes/{fp_name:s}{model3d_path_suffix:s}'.format(
        model3d_path_prefix=global_config.model_3d_prefix, lib_name=lib_name, fp_name=footprint_name,
        model3d_path_suffix=global_config.model_3d_suffix)
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

    for pincount in pinrange:
        make_module(global_config, pincount, configuration)
