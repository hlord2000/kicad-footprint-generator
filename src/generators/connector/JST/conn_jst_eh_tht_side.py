#!/usr/bin/env python3

import argparse
import yaml
from math import sqrt

from KicadModTree import *
from scripts.tools.drawing_tools import round_to_grid
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files import global_config as GC


series = "EH"
manufacturer = 'JST'
orientation = 'H'
number_of_rows = 1
datasheet = 'http://www.jst-mfg.com/product/pdf/eng/eEH.pdf'

pitch = 2.50
pad_to_pad_clearance = 0.8
pad_copper_y_solder_length = 0.5 #How much copper should be in y direction?
min_annular_ring = 0.15

def generate_one_footprint(global_config: GC.GlobalConfig, pincount, configuration):
    mpn = "S{pincount}B-EH".format(pincount=pincount) #JST part number format string
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

    A = (pincount - 1) * pitch
    B = A + 5.0

    x1 = -2.5
    y1 = -6.7
    x2 = x1 + B
    y21 = y1 + 6
    y2 = 1.5
    x11 = x1+1
    x21 = x2-1
    body_edge={'left':x1, 'right':x2, 'top':y1, 'bottom':y2}

    #draw the main outline around the footprint
    # kicad_mod.append(RectLine(start={'x':x1,'y':y1}, end={'x':x2,'y':y2}, layer='F.Fab', width=configuration['fab_line_width']))
    fab_outline=[
        {'x': x11, 'y': y21},
        {'x': x11, 'y': y2},
        {'x': x1, 'y': y2},
        {'x': x1, 'y': y1},
        {'x': x2, 'y': y1},
        {'x': x2, 'y': y2},
        {'x': x21, 'y': y2},
        {'x': x21, 'y': y21},
        {'x': x11, 'y': y21}
    ]
    kicad_mod.append(PolygonLine(shape=fab_outline,
                                 layer='F.Fab', width=configuration['fab_line_width']))
    ########################### CrtYd #################################
    cx1 = round_to_grid(x1-configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])
    cy1 = round_to_grid(y1-configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])

    cx2 = round_to_grid(x2+configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])
    cy2 = round_to_grid(y2+configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])

    kicad_mod.append(RectLine(
        start=[cx1, cy1], end=[cx2, cy2],
        layer='F.CrtYd', width=configuration['courtyard_line_width']))

    ########################### SilkS #################################

    #line offset
    off = configuration['silk_fab_offset']

    x1 -= off
    y1 -= off

    x2 += off
    y2 += off


    T = 1 + 2*configuration['silk_fab_offset']

    y3 = y21 + off

    kicad_mod.append(PolygonLine(shape=[{ 'x': x1 + T, 'y':y3 },
                                           {'x':x1+T,'y':y2},
                                           {'x':x1,'y':y2},
                                           {'x':x1,'y':y1},
                                           {'x':x2,'y':y1},
                                           {'x':x2,'y':y2},
                                           {'x':x2-T,'y':y2},
                                           {'x':x2-T,'y':y3}], layer='F.SilkS', width=configuration['silk_line_width']))

    kicad_mod.append(PolygonLine(shape=[{ 'x':x1, 'y': y1 + T },
                                           {'x':x1+T,'y':y1+T},
                                           {'x':x1+T,'y':y3},
                                           {'x':x1,'y':y3}], layer='F.SilkS', width=configuration['silk_line_width']))

    kicad_mod.append(PolygonLine(shape=[{ 'x':x2, 'y': y1 + T },
                                           {'x':x2-T,'y':y1+T},
                                           {'x':x2-T,'y':y3},
                                           {'x':x2,'y':y3}], layer='F.SilkS', width=configuration['silk_line_width']))



    #add pictures of pins
    #pin-width w
    #pin-length l
    w = 0.32
    l = 3.5

    py = y3-1

    kicad_mod.append(Line(start={'x':x1+T,'y':py},end={'x':x2-T,'y':py}, layer='F.SilkS', width=configuration['silk_line_width']))

    # kicad_mod.append(Line(start={'x':x1+T,'y':py+1},end={'x':x2-T,'y':py+1}, layer='F.SilkS', width=configuration['silk_line_width']))
    pcs_x = pad_size[0]/2 + configuration['silk_pad_clearance'] + configuration['silk_line_width']
    for p in range(pincount):

        px = p * pitch

        kicad_mod.append(PolygonLine(shape=[{ 'x': px, 'y': py },
                                               {'x': px-w,'y': py},
                                               {'x': px-w,'y': py-l+0.25*w},
                                               {'x': px,'y': py-l},
                                               {'x': px+w,'y': py-l+0.25*w},
                                               {'x': px+w,'y': py},
                                               {'x': px,'y': py}], layer='F.SilkS', width=configuration['silk_line_width']))

        if p < pincount-1:
            kicad_mod.append(Line(start=[px + pcs_x, y3], end=[px + pitch - pcs_x, y3],
                layer='F.SilkS', width=configuration['silk_line_width']))

    ######################### Pin 1 marker ##############################

    xm = 0
    ym = 1.5

    m = 0.3

    pin = [{'x':xm,'y':ym},
           {'x':xm - m,'y':ym + 2 * m},
           {'x':xm + m,'y':ym + 2 * m},
           {'x':xm,'y':ym}]
    kicad_mod.append(PolygonLine(shape=pin, layer='F.SilkS', width=configuration['silk_line_width']))

    sl = 1
    pin = [
        {'x':xm-sl/2,'y':y21},
        {'x':xm,'y':y21-sl/sqrt(2)},
        {'x':xm+sl/2,'y':y21}
    ]
    kicad_mod.append(PolygonLine(shape=pin, layer='F.Fab', width=configuration['fab_line_width']))

    ######################### Text Fields ###############################
    addTextFields(kicad_mod=kicad_mod, configuration=configuration, body_edges=body_edge,
        courtyard={'top':cy1, 'bottom':cy2}, fp_name=footprint_name, text_y_inside_position='center')

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
