#!/usr/bin/env python3

import argparse
import yaml

from KicadModTree import *
from scripts.tools.drawing_tools import round_to_grid
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files import global_config as GC


series = "ZH"
manufacturer = 'JST'
orientation = 'V'
number_of_rows = 1
datasheet = 'http://www.jst-mfg.com/product/pdf/eng/eZH.pdf'


pitch = 1.50 # mm
pin_range = range(2,13)

fab_pin1_marker_type = 1
pin1_marker_offset = 0.2
pin1_marker_linelen = 0.8
inner_silkscreen_inset = 0.4 # how much inner silkscreen is inset from outer housing silkscreen
silkscreen_pin_delimiter_protrusion_length = 0.4

drill_size = 0.73 #Datasheet: 0.7 +0.03/-0.03
pad_to_pad_clearance = 0.8
pad_copper_y_solder_length = 0.5 #How much copper should be in y direction?
min_annular_ring = 0.15

# Y
# ^
# |  ___________
# | |_._._._._._|
# |__________> X
#    -0+

# Connector Parameters (housing dimensions compared to pin 1)
housing_width = 3.5 # mm
#housing_length = 1.5*2 + pincount*pitch  # not used, but good documentation.

# pin 1 is at (x=0, y=0)

x_min = -1.5 #housing length past pin 1 on each side (always negative)
y_max = 2.2
y_min = (y_max - housing_width)

def generate_one_footprint(global_config: GC.GlobalConfig, pincount, configuration):
    silk_x_min = x_min - configuration['silk_fab_offset']
    silk_y_min = y_min - configuration['silk_fab_offset']
    silk_y_max = y_max + configuration['silk_fab_offset']


    x_mid = (pincount-1)*pitch/2.0
    x_max = (pincount-1)*pitch + (-x_min)
    silk_x_max = x_max + configuration['silk_fab_offset']

    # Through-hole type shrouded header, Top entry type
    mpn = "B{n}B-ZR".format(n=pincount) #JST part number format string
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

    # create Silkscreen
    kicad_mod.append(RectLine(start=[silk_x_min,silk_y_min], end=[silk_x_max,silk_y_max],
        layer='F.SilkS', width=configuration['silk_line_width']))



    poly_silk_p1_protrusion=[
        {'x':-0.3, 'y':silk_y_min},
        {'x':-0.3, 'y':silk_y_min-0.2},
        {'x':-0.6, 'y':silk_y_min-0.2},
        {'x':-0.6, 'y':silk_y_min}
    ]
    kicad_mod.append(PolygonLine(shape=poly_silk_p1_protrusion, layer='F.SilkS', width=configuration['silk_line_width']))
    kicad_mod.append(Line(start=[-0.3, silk_y_min-0.1], end=[-0.6, silk_y_min-0.1], layer='F.SilkS', width=configuration['silk_line_width']))

    if configuration['allow_silk_below_part'] == 'tht' or configuration['allow_silk_below_part'] == 'both':
        # inner_silkscreen_inset = 0.5
        silk_inner_x_min= silk_x_min + inner_silkscreen_inset     # x pos of left inner silkscreeen box
        silk_inner_x_max= silk_x_max - inner_silkscreen_inset    # x pos of right inner silkscreeen box

        silk_inner_y_min= silk_y_min + inner_silkscreen_inset
        silk_inner_y_max= silk_y_max - inner_silkscreen_inset


        # inner outline
        # zh has full shroud, unlike ph, where there is a cutout.
        # poly_silk_inner_outline = [
        #     # {'x':0.5, 'y':silk_y_min},       #
        #     {'x':0.5, 'y':silk_y_min},             #
        #     {'x':silk_inner_x_min, 'y':-1.2}, #
        #     {'x':silk_inner_x_min, 'y':2.3},
        #     {'x':silk_inner_x_max, 'y':2.3},
        #     {'x':silk_inner_x_max, 'y':-1.2},
        #     {'x':x_max-2.45, 'y':-1.2},
        #     {'x':x_max-2.45, 'y':silk_y_min}
        # ]
        # kicad_mod.append(PolygonLine(shape=poly_silk_inner_outline, layer='F.SilkS', width=configuration['silk_line_width']))

        #use box for zh inner outline instead.
        kicad_mod.append(RectLine(start=[silk_inner_x_min,silk_inner_y_min], end=[silk_inner_x_max,silk_inner_y_max],
        layer='F.SilkS', width=configuration['silk_line_width']))

        # side gaps
        side_gap_width  = 1.0  # width on x from startx in + direction
        side_gap_startx = -0.5  # offset from pins. in this case -0.5 + 1.0 = 0.5: so goes from -0.5 to 0.5
        side_gap_endx   = side_gap_startx + side_gap_width
        kicad_mod.append(Line(start=[silk_x_min, side_gap_startx], end=[silk_inner_x_min, side_gap_startx], layer='F.SilkS', width=configuration['silk_line_width']))
        kicad_mod.append(Line(start=[silk_x_min, side_gap_endx], end=[silk_inner_x_min, side_gap_endx], layer='F.SilkS', width=configuration['silk_line_width']))

        kicad_mod.append(Line(start=[silk_x_max, side_gap_startx], end=[silk_inner_x_max, side_gap_startx], layer='F.SilkS', width=configuration['silk_line_width']))
        kicad_mod.append(Line(start=[silk_x_max, side_gap_endx], end=[silk_inner_x_max, side_gap_endx], layer='F.SilkS', width=configuration['silk_line_width']))

        # silkscreen pin delimiter protrusions
        inner_prot_ymax = silk_inner_y_max ## y position of inner silkscren box
        inner_prot_ymin = inner_prot_ymax - silkscreen_pin_delimiter_protrusion_length
        inner_prot_xwidth = 0.2
        for i in range(0, pincount-1):
            middle_x = pitch/2 + i*pitch  #x pos between pins
            start_x = middle_x - (inner_prot_xwidth/2)
            end_x = middle_x + (inner_prot_xwidth/2)
            poly_silk_inner_protrusion=[
                {'x':start_x, 'y':inner_prot_ymax},
                {'x':start_x, 'y':inner_prot_ymin},
                {'x':end_x, 'y':inner_prot_ymin},
                {'x':end_x, 'y':inner_prot_ymax}
            ]
            kicad_mod.append(PolygonLine(shape=poly_silk_inner_protrusion, layer='F.SilkS', width=configuration['silk_line_width']))
            kicad_mod.append(Line(start=[middle_x, inner_prot_ymax], end=[middle_x, inner_prot_ymin], layer='F.SilkS', width=configuration['silk_line_width']))

    ########################### Pin 1 marker ################################
    poly_pin1_marker = [
        {'x':silk_x_min-pin1_marker_offset+pin1_marker_linelen, 'y':silk_y_min-pin1_marker_offset},
        {'x':silk_x_min-pin1_marker_offset, 'y':silk_y_min-pin1_marker_offset},
        {'x':silk_x_min-pin1_marker_offset, 'y':silk_y_min-pin1_marker_offset+pin1_marker_linelen}
    ]
    kicad_mod.append(PolygonLine(shape=poly_pin1_marker, layer='F.SilkS', width=configuration['silk_line_width']))
    if fab_pin1_marker_type == 1:
        kicad_mod.append(PolygonLine(shape=poly_pin1_marker, layer='F.Fab', width=configuration['fab_line_width']))

    if fab_pin1_marker_type == 2:
        poly_pin1_marker_type2 = [
            {'x':-1, 'y':y_min},
            {'x':0, 'y':y_min+1},
            {'x':1, 'y':y_min}
        ]
        kicad_mod.append(PolygonLine(shape=poly_pin1_marker_type2, layer='F.Fab', width=configuration['fab_line_width']))

    ########################## Fab Outline ###############################
    kicad_mod.append(RectLine(start=[x_min,y_min], end=[x_max,y_max],
        layer='F.Fab', width=configuration['fab_line_width']))
    ############################# CrtYd ##################################
    part_x_min = x_min
    part_x_max = x_max
    part_y_min = y_min
    part_y_max = y_max

    cx1 = round_to_grid(part_x_min-configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])
    cy1 = round_to_grid(part_y_min-configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])

    cx2 = round_to_grid(part_x_max+configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])
    cy2 = round_to_grid(part_y_max+configuration['courtyard_offset']['connector'], configuration['courtyard_grid'])

    kicad_mod.append(RectLine(
        start=[cx1, cy1], end=[cx2, cy2],
        layer='F.CrtYd', width=configuration['courtyard_line_width']))


    ############################# Pads ##################################
    pad_size = [pitch - pad_to_pad_clearance, drill_size + 2*pad_copper_y_solder_length]
    if pad_size[0] - drill_size < 2*min_annular_ring:
        pad_size[0] = drill_size + 2*min_annular_ring

    # kicad_mod.append(Pad(number=1, type=Pad.TYPE_THT, shape=Pad.SHAPE_RECT,
    #                     at=[0, 0], size=pad_size,
    #                     drill=drill_size, layers=Pad.LAYERS_THT))

    optional_pad_params = {}
    optional_pad_params['tht_pad1_shape'] = Pad.SHAPE_ROUNDRECT

    kicad_mod.append(PadArray(initial=1, start=[0, 0],
        x_spacing=pitch, pincount=pincount,
        size=pad_size, drill=drill_size,
        type=Pad.TYPE_THT, shape=Pad.SHAPE_OVAL, layers=Pad.LAYERS_THT,
        round_radius_handler=global_config.roundrect_radius_handler,
        **optional_pad_params))

    ######################### Text Fields ###############################
    text_center_y = 1.5
    body_edge={'left':part_x_min, 'right':part_x_max, 'top':part_y_min, 'bottom':part_y_max}
    addTextFields(kicad_mod=kicad_mod, configuration=configuration, body_edges=body_edge,
        courtyard={'top':cy1, 'bottom':cy2}, fp_name=footprint_name, text_y_inside_position=text_center_y)

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

    for pincount in pin_range:
        generate_one_footprint(global_config, pincount, configuration)
