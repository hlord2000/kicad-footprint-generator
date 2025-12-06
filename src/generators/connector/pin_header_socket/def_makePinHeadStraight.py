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
    Rectangle,
    Text,
    Translation,
)
from kilibs.geom import Vec2DCompatible, Vector2D
from .spec import FPconfiguration
from generators.tools.footprint.drawing_tools import roundCrt
from generators.tools.footprint.save_footprint import write_footprint
from kilibs.config import global_config as GC

txt_offset = 1


# THT Straight (Vertical) Pinheader:
#####################################
# <--------------> body_width
#    <--------> row_pitch
# +--------------+
# | OOO      OOO |     ^
# | OOO ==== OOO |  ^  pin_width
# | OOO      OOO |  |  v
# +--------------+  pin_pitch
# | OOO      OOO |  |
# | OOO ==== OOO |  v
# | OOO      OOO |
# +--------------+
#
def makePinHeadStraight(cfg: FPconfiguration, generator_name: str):
    gc = GC.GLOBAL_CONFIG
    pos_count = cfg.pos_count
    row_count = cfg.row_count
    pin_pitch = cfg.pin_pitch
    row_pitch = cfg.row_pitch
    body_width = cfg.body_width
    body_overlength = cfg.body_overlength
    pins_drill = cfg.pins_drill

     # assemble library and footprint name:
    cfg.lib_name 	= cfg.getLibraryName()	
    cfg.footpr_name = cfg.getFootprintName()
    # information about what is generated:
    # import pprint
    # pprint.pprint(cfg)

    # body_overlength is symetrical but keep separated as top/bottom internally.
    overlen_top = pin_pitch/2 + body_overlength
    overlen_bot = pin_pitch/2 + body_overlength

    if cfg.class_name == "PinSocket":
        isSocket: bool = True
    else:
        isSocket: bool = False

    # init kicad footprint
    kicad_mod = Footprint(cfg.footpr_name, cfg.footpr_type)
    kicad_mod.description = cfg.getDescription()
    #if isSocket and cfg.datasheet != None:
    #    kicad_mod.description += " (" + cfg.datasheet + "), script generated"
    kicad_mod.tags = cfg.getBaseTags()

    # instantiate footprint (SMD origin at center, THT at pin 1)
    offset = Vector2D(0, 0)
    if isSocket and row_count > 1:
        offset.x = -row_pitch
    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    pad = Vector2D(cfg.pads_length, cfg.pads_width) # x=length, y=width

    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    # This is set a bit further out than normal, not quite clear why.
    # silk_pad_offset = gc.silk_pad_offset
    silk_pad_offset = gc.silk_pad_clearance + gc.silk_fab_offset

    silk_line_width = gc.silk_line_width

    h_fab = (pos_count - 1) * pin_pitch + overlen_top + overlen_bot
    w_fab = body_width
    l_fab = (row_pitch * (row_count - 1) - w_fab) / 2
    t_fab = -overlen_top

    h_slk = h_fab + 2 * gc.silk_fab_offset
    w_slk = max(
        w_fab + 2 * gc.silk_fab_offset,
        row_pitch * (row_count - 1) - pad.x - 4 * gc.silk_fab_offset,
    )
    l_slk = (row_pitch * (row_count - 1) - w_slk) / 2
    t_slk = -overlen_top - gc.silk_fab_offset

    w_crt = max(body_width, row_pitch * (row_count - 1) + pad.x) + 2 * crtyd_offset
    h_crt = max(h_fab, (pos_count - 1) * pin_pitch + pad.y) + 2 * crtyd_offset
    l_crt = row_pitch * (row_count - 1) / 2 - w_crt / 2
    t_crt = (pos_count - 1) * pin_pitch / 2 - h_crt / 2

    fab_text_props = gc.get_text_properties_for_layer("F.Fab")
    fabref_text_size, fabref_text_thickness = fab_text_props.clamp_size(w_fab * 0.6)
    # That causes diffs, use the old unrounded calc for now
    fabref_text_thickness = fabref_text_size.y * 0.15

    # set general values
    kicad_modg.append(
        Property(name=Property.REFERENCE, text='REF**', at=[row_pitch * (row_count - 1) / 2, t_slk - txt_offset], layer='F.SilkS'))
    kicad_modg.append(
        Text(text='${REFERENCE}', at=[pin_pitch/2*(row_count-1), t_crt + offset.x + (h_crt/2)], rotation=90, layer='F.Fab', size=fabref_text_size, thickness=fabref_text_thickness))
    kicad_modg.append(
        Property(name=Property.VALUE, text=cfg.footpr_name, at=[row_pitch * (row_count - 1) / 2, t_slk + h_slk + txt_offset], layer='F.Fab'))

    # create FAB-layer
    chamfer = w_fab/4
    kicad_modg.append(Line(start=[l_fab + chamfer, t_fab], end=[l_fab + w_fab, t_fab], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fab + w_fab, t_fab], end=[l_fab + w_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fab + w_fab, t_fab+h_fab], end=[l_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fab, t_fab+h_fab], end=[l_fab, t_fab+chamfer], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fab, t_fab+chamfer], end=[l_fab + chamfer, t_fab], layer='F.Fab', width=gc.fab_line_width))

    # create SILKSCREEN-layer + pin1 marker

    # Silkscreen body
    body_min_x_square = pad.x / 2 + silk_pad_offset
    body_min_y_square = pad.y / 2 + silk_pad_offset
    # drawin bottom line

    if (pos_count-1)*pin_pitch + body_min_y_square < t_slk + h_slk:
        kicad_modg.append(Line(start=[l_slk, t_slk + h_slk], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
    else:
        if pos_count == 1:
            kicad_modg.append(Line(start=[l_slk, body_min_y_square], end=[l_slk + w_slk, body_min_y_square], layer='F.SilkS', width=silk_line_width))
        else:
            body_min_x_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (overlen_bot + gc.silk_fab_offset) * (overlen_bot + gc.silk_fab_offset)))
            kicad_modg.append(Line(start=[l_slk, t_slk + h_slk], end=[-body_min_x_round, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
            kicad_modg.append(Line(start=[(row_count-1)*row_pitch+body_min_x_round, t_slk + h_slk], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
            for x in range(0, (row_count-1)):
                kicad_modg.append(Line(start=[x*row_pitch+body_min_x_round, t_slk + h_slk], end=[(x+1)*row_pitch-body_min_x_round, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
    # drawin sidelines
    # calculate top Y position
    if pin_pitch < body_min_y_square * 2:
        shoulder_y_pos = body_min_y_square
        shoulder_y_lines = 2
    else:
        shoulder_y_pos = pin_pitch / 2
        shoulder_y_lines = 1
    if row_pitch < body_min_x_square * 2:
        top_x_pos = body_min_x_square
        top_x_lines = 2
    else:
        top_x_pos = row_pitch / 2
        top_x_lines = 1
    if l_slk + w_slk  > body_min_x_square+(row_count-1)*row_pitch:
        kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[l_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
        if row_count == 1:
            kicad_modg.append(Line(start=[l_slk + w_slk, shoulder_y_pos], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
        else:
            kicad_modg.append(Line(start=[l_slk + w_slk, t_slk], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
    elif pos_count != 1:
        body_min_y_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - l_slk * l_slk))
        kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[l_slk, pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
        kicad_modg.append(Line(start=[l_slk, (pos_count-1)*pin_pitch+body_min_y_round], end=[l_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
        if row_count == 1:
            kicad_modg.append(Line(start=[l_slk + w_slk, shoulder_y_pos], end=[l_slk + w_slk, pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
        else:
            kicad_modg.append(Line(start=[l_slk + w_slk, body_min_y_square], end=[l_slk + w_slk, pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
        kicad_modg.append(Line(start=[l_slk + w_slk, (pos_count-1)*pin_pitch+body_min_y_round], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
        for x in range(1, (pos_count-1)):
            kicad_modg.append(Line(start=[l_slk, x*pin_pitch+body_min_y_round], end=[l_slk, (x+1)*pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
            kicad_modg.append(Line(start=[l_slk + w_slk, x*pin_pitch+body_min_y_round], end=[l_slk + w_slk, (x+1)*pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
    # drawin top

    if row_count == 1:
        if shoulder_y_lines == 1:
            kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[l_slk + w_slk, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
        elif shoulder_y_lines == 2:
            top_x_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (shoulder_y_pos-pin_pitch) * (shoulder_y_pos-pin_pitch)))
            kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[l_slk + w_slk/2-top_x_round, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
            kicad_modg.append(Line(start=[l_slk + w_slk/2 + top_x_round, shoulder_y_pos], end=[l_slk + w_slk, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
    else:
        if shoulder_y_lines == 1:
            kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[top_x_pos, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
        elif shoulder_y_lines == 2:
            top_x_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (shoulder_y_pos-pin_pitch) * (shoulder_y_pos-pin_pitch)))
            if top_x_pos > row_pitch-top_x_round:
                top_x_end = row_pitch-top_x_round
            else:
                top_x_end = top_x_pos
            kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[-top_x_round, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
            if top_x_round*2 + gc.silk_line_width*2 < pad.x:
                kicad_modg.append(Line(start=[top_x_round, shoulder_y_pos], end=[top_x_end, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
        if top_x_lines == 1:
            kicad_modg.append(Line(start=[top_x_pos, shoulder_y_pos], end=[top_x_pos, t_slk], layer='F.SilkS', width=silk_line_width))
        elif top_x_lines == 2:
            shoulder_y_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (row_pitch-top_x_pos) * (row_pitch-top_x_pos)))
            if shoulder_y_pos > pin_pitch-shoulder_y_round:
                shoulder_y_pos = pin_pitch-shoulder_y_round
            if shoulder_y_round*2 + silk_line_width*2 < pad.y:
                kicad_modg.append(Line(start=[top_x_pos, shoulder_y_pos], end=[top_x_pos, shoulder_y_round], layer='F.SilkS', width=silk_line_width))
                kicad_modg.append(Line(start=[top_x_pos, -shoulder_y_round], end=[top_x_pos, t_slk], layer='F.SilkS', width=silk_line_width))
        # highest horizontal line
        if abs(t_slk) > body_min_y_square:
            kicad_modg.append(Line(start=[top_x_pos, t_slk], end=[l_slk + w_slk, t_slk], layer='F.SilkS', width=silk_line_width))
        else:
            top_x_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (abs(t_slk)) * (abs(t_slk))))
            if top_x_pos > row_pitch-top_x_round + 2*silk_line_width:
                kicad_modg.append(Line(start=[top_x_pos, t_slk], end=[row_pitch-top_x_round, t_slk], layer='F.SilkS', width=silk_line_width))
            kicad_modg.append(Line(start=[row_pitch+top_x_round, t_slk], end=[l_slk + w_slk, t_slk], layer='F.SilkS', width=silk_line_width))

    """
    if row_count == 1:
        kicad_modg.append(
            Rectangle(start=[l_slk, 0.5 * pin_pitch], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=gc.silk_line_width))
    else:
        if isSocket and row_count>1:
            kicad_modg.append(PolygonLine(
                shape=[[l_slk+w_slk, 0.5 * pin_pitch], [l_slk+w_slk, t_slk + h_slk], [l_slk , t_slk + h_slk], [l_slk , t_slk],
                          [l_slk+w_slk/2, t_slk], [l_slk+w_slk/2, 0.5 * pin_pitch], [l_slk+w_slk, 0.5 * pin_pitch]], layer='F.SilkS', width=lw_slk))
        else:
            kicad_modg.append(PolygonLine(
                shape=[[l_slk, 0.5 * pin_pitch], [l_slk, t_slk + h_slk], [l_slk + w_slk, t_slk + h_slk], [l_slk + w_slk, t_slk],
                          [0.5 * pin_pitch, t_slk], [0.5 * pin_pitch, 0.5 * pin_pitch], [l_slk, 0.5 * pin_pitch]], layer='F.SilkS', width=lw_slk))
    """
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
    if isSocket and row_count>1:
        kicad_modg.append(PolygonLine(shape=[[pin1_x + w_slk, 0], [pin1_x + w_slk, pin1_y], [pin1_x + w_slk - pin_pitch / 2, pin1_y]], layer='F.SilkS', width=silk_line_width))
    else:
        kicad_modg.append(PolygonLine(shape=[[pin1_x, 0], [pin1_x, pin1_y], [0, pin1_y]], layer='F.SilkS', width=silk_line_width))

    # create courtyard
    crt_rect = Rectangle(
        start=Vector2D(l_crt, t_crt),
        size=Vector2D(w_crt, h_crt),
    ).round_to_grid(outwards=True, grid=gc.courtyard_grid)

    kicad_modg.append(
        Rectangle(
            start=crt_rect.top_left,
            end=crt_rect.bottom_right,
            layer="F.CrtYd",
            width=gc.courtyard_line_width,
        )
    )

    # create pads
    x1 = 0
    y1 = 0

    pad_type = Pad.TYPE_THT
    pad_shape1 = Pad.SHAPE_RECT
    pad_shapeother = Pad.SHAPE_OVAL
    pad_layers = Pad.LAYERS_THT

    p = 1

    for r in range(1, pos_count + 1):  # type: ignore

        if isSocket and row_count > 1:
            x1 = row_pitch
        else:
            x1 = 0
        for c in range(1, row_count + 1):  # type: ignore
            if p == 1:
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[x1, y1], size=pad, drill=pins_drill,
                                      layers=pad_layers))
            else:
                kicad_modg.append(
                    Pad(number=p, type=pad_type, shape=pad_shapeother, at=[x1, y1], size=pad, drill=pins_drill,
                        layers=pad_layers))

            p = p + 1
            if isSocket and row_count > 1:
                x1 = x1 - row_pitch
            else:
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
