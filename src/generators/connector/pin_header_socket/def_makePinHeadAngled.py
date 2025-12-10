#!/usr/bin/env python

from math import sqrt

from KicadModTree import (
    Footprint,
    FootprintType,
    Line,
    Model,
    Pad,
    PadArray,
    PolygonLine,
    Property,
    Rectangle,
    Text,
    Translation,
)
from kilibs.geom import Vec2DCompatible, Vector2D
from .spec import FPconfiguration
import generators.tools.footprint.drawing_tools as DT
from generators.tools.footprint.save_footprint import write_footprint
from kilibs.config import global_config as GC

txt_offset = 1


# THT Angled (Horizontal) Pinheader:
#####################################
#             <--> body_offset
#                 <-------> body_width
#                          <------------------------------> pin_length
#    <--------> row_pitch
# +---            +-------+
# | OOO      OOO  |       +-------------------------------+            ^
# | OOO ==== OOO  |       |                               +    ^       pin_width
#   OOO      OOO  |       +-------------------------------+    |       v
#                 +-------+                                    pin_pitch
#   OOO      OOO  |       +-------------------------------+    |
#   OOO ==== OOO  |       |                               +    v
#   OOO      OOO  |       +-------------------------------+
#                 +-------+
#
def makePinHeadAngled(cfg: FPconfiguration, generator_name: str):
    gc = GC.GLOBAL_CONFIG
    pos_count = cfg.pos_count
    row_count = cfg.row_count
    pin_pitch = cfg.pin_pitch
    row_pitch = cfg.row_pitch
    body_width = cfg.body_width
    body_offset = cfg.body_offset
    pin_length = cfg.pins_length
    pin_width = cfg.pins_width
    pins_drill = cfg.pins_drill

     # assemble library and footprint name:
    cfg.lib_name 	= cfg.getLibraryName()	
    cfg.footpr_name = cfg.getFootprintName()
    # information about what is generated:
    # import pprint
    # pprint.pprint(cfg)

    # init kicad footprint
    kicad_mod = Footprint(cfg.footpr_name, cfg.footpr_type)
    kicad_mod.description = cfg.getDescription()
    # if cfg.datasheet != None:
    #     kicad_mod.description += ", " + cfg.datasheet
    kicad_mod.tags = cfg.getBaseTags()

    # instantiate footprint (SMD origin at center, THT at pin 1)
    offset = Vector2D(0, 0)
    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    pad = Vector2D(cfg.pads_length, cfg.pads_width) # x=length, y=width

    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    # This is set a bit further out than normal, not quite clear why.
    # silk_pad_offset = gc.silk_pad_offset
    silk_pad_offset = gc.silk_pad_clearance + gc.silk_fab_offset

    h_fabb = (pos_count - 1) * pin_pitch + pin_pitch / 2 + pin_pitch / 2
    w_fabb = body_width
    l_fabb = row_pitch * (row_count - 1) + body_offset
    t_fabb = -pin_pitch / 2
    l_fabp = l_fabb + w_fabb
    t_fabp = -pin_width / 2

    fab_text_props = gc.get_text_properties_for_layer("F.Fab")
    fabref_text_size, fabref_text_thickness = fab_text_props.clamp_size(w_fabb * 0.6)
    # That causes diffs, use the old unrounded calc for now
    fabref_text_thickness = fabref_text_size.y * 0.15

    w_slkb = w_fabb + 2 * gc.silk_fab_offset
    l_slkb = l_fabb - gc.silk_fab_offset
    t_slkb = t_fabb - gc.silk_fab_offset
    l_slkp = l_slkb + w_slkb
    l_slk = -pin_pitch / 2
    t_slk = -pin_pitch / 2
    body_lines_y = False

    w_crt = pin_pitch / 2 + (row_count - 1) * row_pitch + body_offset + body_width + pin_length + 2 * crtyd_offset
    h_crt = h_fabb + 2 * crtyd_offset
    l_crt = -pin_pitch / 2 - crtyd_offset
    t_crt = -pin_pitch / 2 - crtyd_offset

    # set general values
    kicad_modg.append(
        Property(name=Property.REFERENCE, text='REF**', at=[l_crt + w_crt / 2, t_crt + crtyd_offset - txt_offset], layer='F.SilkS'))
    kicad_modg.append(
        Text(text='${REFERENCE}', at=[l_fabb + (w_fabb/2), t_crt + offset.y + (h_crt/2)], rotation=90, layer='F.Fab', size=fabref_text_size, thickness=fabref_text_thickness))
    kicad_modg.append(
        Property(name=Property.VALUE, text=cfg.footpr_name, at=[l_crt + w_crt / 2, t_crt + h_crt - crtyd_offset + txt_offset],
             layer='F.Fab'))

    # create FAB-layer
    chamfer = w_fabb/4
    kicad_modg.append(Line(start=[l_fabb + chamfer, t_fabb], end=[l_fabb + w_fabb, t_fabb], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fabb + w_fabb, t_fabb], end=[l_fabb + w_fabb, t_fabb+pin_pitch*pos_count], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fabb + w_fabb, t_fabb+pin_pitch*pos_count], end=[l_fabb, t_fabb+pin_pitch*pos_count], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fabb, t_fabb+pin_pitch*pos_count], end=[l_fabb, t_fabb+chamfer], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fabb, t_fabb+chamfer], end=[l_fabb + chamfer, t_fabb], layer='F.Fab', width=gc.fab_line_width))
    y1 = t_fabb
    yp = t_fabp
    for r in range(1, pos_count + 1):
        kicad_modg.append(Line(start=[-pin_width/2, yp], end=[l_fabb, yp], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[-pin_width/2, yp], end=[-pin_width/2, yp + pin_width], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[-pin_width/2, yp + pin_width], end=[l_fabb, yp + pin_width], layer='F.Fab', width=gc.fab_line_width))

        kicad_modg.append(Line(start=[l_fabb + w_fabb, yp], end=[l_fabp + pin_length, yp], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fabp + pin_length, yp], end=[l_fabp + pin_length, yp + pin_width], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fabb + w_fabb, yp + pin_width], end=[l_fabp + pin_length, yp + pin_width], layer='F.Fab', width=gc.fab_line_width))

        y1 = y1 + pin_pitch
        yp = yp + pin_pitch

    # create SILKSCREEN-layer + pin1 marker

    # calculate point to avoid collision with pad clearance
    pin_line_x = sqrt(((pad.x/2+ silk_pad_offset) * (pad.x/2+ silk_pad_offset) - (pin_width/2+gc.silk_fab_offset) * (pin_width/2+gc.silk_fab_offset)))
    # Silkscreen body
    body_min_x_square = pad.x/2+ silk_pad_offset
    body_min_y_square = pad.y/2+ silk_pad_offset

    if pin_pitch/2 < body_min_y_square:
        body_min_x_round = sqrt((((pad.x/2+ silk_pad_offset) * (pad.x/2+ silk_pad_offset)) - (pin_pitch/2 * pin_pitch/2)))
        if l_slkb > body_min_x_round + (row_count-1)*row_pitch and l_slkb < body_min_x_square +(row_count-1)*row_pitch:
            body_lines_y = sqrt((((pad.x/2+ silk_pad_offset) * (pad.x/2+ silk_pad_offset)) - ((l_slkb-(row_count-1)*row_pitch) * (l_slkb-(row_count-1)*row_pitch))))
    else:
        body_min_x_round  = 0
    if pin_pitch/2+gc.silk_fab_offset < body_min_y_square:
        bodyend_min_x_round = sqrt((((pad.x/2+ silk_pad_offset) * (pad.x/2+ silk_pad_offset)) - ((pin_pitch/2+gc.silk_fab_offset) * (pin_pitch/2+gc.silk_fab_offset))))
    else:
        bodyend_min_x_round = 0
    # if body is starting outside the pads
    if l_slkb-gc.silk_fab_offset > pad.x/2 + gc.silk_pad_clearance + (row_count-1)*row_pitch:
        kicad_modg.append(Rectangle(start=[l_slkb, t_slkb], end=[l_slkp, t_slkb+pin_pitch*pos_count+gc.silk_fab_offset*2], layer='F.SilkS', width=gc.silk_line_width))
    else:
        if l_slkb < body_min_x_square + (row_count-1)*row_pitch and t_slkb-gc.silk_fab_offset > -(body_min_y_square + (row_count-1)*row_pitch):
            if row_count == 1:
                upper_body_x = body_min_x_square
            else:
                upper_body_x = bodyend_min_x_round + (row_count-1)*row_pitch
        else:
            upper_body_x = l_slkb
        if pos_count == 1 and row_count == 1:
            lower_body_x = body_min_x_square  + (row_count-1)*row_pitch
        elif l_slkb < bodyend_min_x_round + (row_count-1)*row_pitch and t_slkb-gc.silk_fab_offset > -(body_min_y_square + (row_count-1)*row_pitch):
            lower_body_x = bodyend_min_x_round + (row_count-1)*row_pitch
        else:
            lower_body_x = l_slkb
        if body_lines_y != False:
            if row_count == 1:
                kicad_modg.append(PolygonLine(shape=[[upper_body_x, t_slkb], [l_slkp, t_slkb], [l_slkp, t_slkb + pin_pitch * pos_count + gc.silk_fab_offset * 2],
                                                        [lower_body_x, t_slkb+pin_pitch*pos_count+gc.silk_fab_offset*2], [lower_body_x, t_slkb+pin_pitch*pos_count-pin_pitch/2+gc.silk_fab_offset+body_lines_y]], layer='F.SilkS', width=gc.silk_line_width))
            else:
                kicad_modg.append(PolygonLine(shape=[[upper_body_x, -body_lines_y], [upper_body_x, t_slkb], [l_slkp, t_slkb], [l_slkp, t_slkb + pin_pitch * pos_count + gc.silk_fab_offset * 2],
                                                        [lower_body_x, t_slkb+pin_pitch*pos_count+gc.silk_fab_offset*2], [lower_body_x, t_slkb+pin_pitch*pos_count-pin_pitch/2+gc.silk_fab_offset+body_lines_y]], layer='F.SilkS', width=gc.silk_line_width))
        else:
            kicad_modg.append(PolygonLine(shape=[[upper_body_x, t_slkb], [l_slkp, t_slkb], [l_slkp, t_slkb + pin_pitch * pos_count + gc.silk_fab_offset * 2],
                                                    [lower_body_x, t_slkb+pin_pitch*pos_count+gc.silk_fab_offset*2]], layer='F.SilkS', width=gc.silk_line_width))

    for r in range(0, pos_count):
        if r != 0:
            if r == 1 and pin_pitch / 2 < body_min_y_square and row_count == 1:
                if l_slkb < body_min_x_square:
                    kicad_modg.append(Line(start=[body_min_x_square, (r-1)*pin_pitch+pin_pitch/2], end=[l_slkp, (r-1)*pin_pitch+pin_pitch/2], layer='F.SilkS',width=gc.silk_line_width))
                else:
                    kicad_modg.append(Line(start=[l_slkb, (r-1)*pin_pitch+pin_pitch/2], end=[l_slkp, (r-1)*pin_pitch+pin_pitch/2], layer='F.SilkS',width=gc.silk_line_width))
            else:
                # add line between rows
                if l_slkb < body_min_x_round + (row_count-1)*row_pitch:
                    kicad_modg.append(Line(start=[body_min_x_round+ (row_count-1)*row_pitch, (r-1)*pin_pitch+pin_pitch/2], end=[l_slkp, (r-1)*pin_pitch+pin_pitch/2], layer='F.SilkS',width=gc.silk_line_width))
                else:
                    kicad_modg.append(Line(start=[l_slkb, (r-1)*pin_pitch+pin_pitch/2], end=[l_slkp, (r-1)*pin_pitch+pin_pitch/2], layer='F.SilkS',width=gc.silk_line_width))
                    if body_lines_y != False:
                        kicad_modg.append(Line(start=[l_slkb, (r-1)*pin_pitch+body_lines_y], end=[l_slkb, (r)*pin_pitch-body_lines_y], layer='F.SilkS',width=gc.silk_line_width))

        # pin outline
        if r != 0:
            kicad_modg.append(
                PolygonLine(
                    shape=[
                        [l_slkp, r * pin_pitch - pin_width / 2 - gc.silk_fab_offset],
                        [l_slkp + pin_length, r * pin_pitch - pin_width / 2 - gc.silk_fab_offset],
                        [l_slkp + pin_length, r * pin_pitch + pin_width / 2 + gc.silk_fab_offset],
                        [l_slkp, r * pin_pitch + pin_width / 2 + gc.silk_fab_offset],
                    ],
                    layer="F.SilkS",
                    width=gc.silk_line_width,
                )
            )
        else:
            # color the first pin
            kicad_modg.append(
                Rectangle(
                    start=Vector2D(l_slkp, -pin_width / 2 - gc.silk_fab_offset),
                    end=Vector2D(l_slkp + pin_length, pin_width / 2 + gc.silk_fab_offset),
                    layer="F.SilkS",
                    width=gc.silk_line_width,
                    fill=True,
                )
            )

        # if body is starting at the pads
        if l_slkb-gc.silk_fab_offset > pad.x/2 + gc.silk_pad_clearance + (row_count-1)*row_pitch:
            if r == 0 and row_count == 1:
                # add the lines between pads and silkscreenbody
                kicad_modg.append(Line(start=[pad.x/2+ silk_pad_offset, r*pin_pitch-pin_width/2-gc.silk_fab_offset],
                    end=[l_slkb, r*pin_pitch-pin_width/2-gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[pad.x/2+ silk_pad_offset, r*pin_pitch+pin_width/2+gc.silk_fab_offset],
                    end=[l_slkb, r*pin_pitch+pin_width/2+gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
            else:
                # add the lines between pads and silkscreenbody
                kicad_modg.append(Line(start=[(row_count-1)*row_pitch + pin_line_x, r*pin_pitch-pin_width/2-gc.silk_fab_offset],
                    end=[l_slkb, r*pin_pitch-pin_width/2-gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[(row_count-1)*row_pitch + pin_line_x, r*pin_pitch+pin_width/2+gc.silk_fab_offset],
                    end=[l_slkb, r*pin_pitch+pin_width/2+gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))

        if row_count > 1:
            for c in range(1, row_count):
                # add the lines between pads
                start_point_x = (c - 1) * row_pitch + pin_line_x
                end_point_x = c * row_pitch - pin_line_x
                if start_point_x < end_point_x - gc.silk_line_width:
                    if r == 0 and c == 1:
                        kicad_modg.append(Line(start=[pad.x/2 + silk_pad_offset, r*pin_pitch-pin_width/2-gc.silk_fab_offset],
                            end=[end_point_x, r*pin_pitch-pin_width/2-gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                        kicad_modg.append(Line(start=[pad.x/2 + silk_pad_offset, r*pin_pitch+pin_width/2+gc.silk_fab_offset],
                            end=[end_point_x, r*pin_pitch+pin_width/2+gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                    else:
                        kicad_modg.append(Line(start=[start_point_x, r*pin_pitch-pin_width/2-gc.silk_fab_offset],
                        end=[end_point_x, r*pin_pitch-pin_width/2-gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                        kicad_modg.append(Line(start=[start_point_x, r*pin_pitch+pin_width/2+gc.silk_fab_offset],
                        end=[end_point_x, r*pin_pitch+pin_width/2+gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))

    # pin 1 marker
    pin1_min = -(pad.x / 2 + silk_pad_offset)
    if pin1_min < l_slk:
        pin1_x = pin1_min
    else:
        pin1_x = l_slk
    if pin1_min < t_slk:
        pin1_y = pin1_min
    else:
        pin1_y = t_slk
    kicad_modg.append(PolygonLine(shape=[[pin1_x, 0], [pin1_x, pin1_y], [0, pin1_y]], layer='F.SilkS', width=gc.silk_line_width))

    # create courtyard
    kicad_mod.append(Rectangle(start=[DT.roundCrt(l_crt + offset.x), DT.roundCrt(t_crt + offset.y)],
                              end=[DT.roundCrt(l_crt + offset.x + w_crt), DT.roundCrt(t_crt + offset.y + h_crt)],
                              layer='F.CrtYd', width=gc.courtyard_line_width))

    # create pads
    x1 = 0
    y1 = 0

    pad_type = Pad.TYPE_THT
    pad_shape1 = Pad.SHAPE_RECT
    pad_shapeother = Pad.SHAPE_OVAL
    pad_layers = Pad.LAYERS_THT

    p = 1

    for r in range(1, pos_count + 1):
        x1 = 0
        for c in range(1, row_count + 1):
            if p == 1:
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[x1, y1], size=pad, drill=pins_drill,
                                      layers=pad_layers))
            else:
                kicad_modg.append(
                    Pad(number=p, type=pad_type, shape=pad_shapeother, at=[x1, y1], size=pad, drill=pins_drill,
                        layers=pad_layers))

            p = p + 1
            x1 = x1 + row_pitch

        y1 = y1 + pin_pitch

    # add model
    kicad_modg.append(
        Model(
            filename=gc.model_3d_prefix
            + cfg.lib_name
            + ".3dshapes/"
            + cfg.footpr_name
            + gc.model_3d_suffix
        )
    )
    write_footprint(kicad_mod, cfg.lib_name, generator_name)
