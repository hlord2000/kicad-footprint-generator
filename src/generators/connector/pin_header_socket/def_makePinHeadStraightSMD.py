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
from .temp_tools import Pad2DArrayFromPads, DrawPinArray
from kilibs.config import global_config as GC


# SMD Straight (Vertical) Pinheader:
#####################################
# <----------------------> body_width
#        <--------> row_pitch
#     <--> pads_offset
# +----------------------+
# | OOOOOOO              |     ^
# | OOOOOOO ====         |  ^  pads_width
# | OOOOOOO              |  |  v
# +                      +  pin_pitch
# |              OOOOOOO |  |
# |         ==== OOOOOOO |  v
# |              OOOOOOO |
# +                      +
# | OOOOOOO              |
# | OOOOOOO ====         |
def makePinHeadStraightSMD(cfg: FPconfiguration, generator_name: str):
    # Abbreviations: fab, slk and crt for fabrication, silk and coutryard.
    # fabb/fabp and slkb/slkp for drawing body and pins (b or p after fab/slk).
    # _h, _w, _t, _b, _l, _r, _c for height, width, top, bottom, left, right, center (vector)
    gc = GC.GLOBAL_CONFIG

    # assemble library and footprint name:
    cfg.lib_name = cfg.getLibraryName()
    cfg.footpr_name = cfg.getFootprintName()

    # --- Settings:
    txt_offset = 1 # similar to text_edge_offset = size / 2 + 0.2 in addTextFields()->_getTextFieldDetails()
    # fab_text properties (fab_txt_size, fab_txt_thick) are calculated/clamped further down.
    # silk_pad_offset = gc.silk_pad_offset # = clearance + line_width/2 = 0.2 + 0.06
    silk_pad_offset = gc.silk_pad_clearance + gc.silk_fab_offset # 0.2 + 0.11
    # This is set a bit further out than normal, not quite clear why.
    silk_fab_offset = gc.silk_fab_offset # 0.11
    crt_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR) # 0.5

    # --- init kicad footprint (SMD origin at center, THT at pin 1):
    kicad_mod = Footprint(cfg.footpr_name, cfg.footpr_type)
    kicad_mod.description = cfg.getDescription()
    #if cfg.isSocket and cfg.datasheet != None:
    #    kicad_mod.description += " (" + cfg.datasheet + "), script generated"
    kicad_mod.tags = cfg.getBaseTags()

    offset = Vector2D(-(cfg.row_count-1)*cfg.row_pitch/2, -(cfg.pos_count-1)*cfg.pin_pitch/2.0) # -half_rows_x, -half_posn_y
    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    # --- Calculate pads center and pin1 offset from origin:
    half_rows_x = (cfg.row_count - 1) / 2 * cfg.row_pitch
    half_posn_y = (cfg.pos_count - 1) / 2 * cfg.pin_pitch
    pad = Vector2D(cfg.pads_length, cfg.pads_width) # x=length, y=width

    if cfg.mount_type == "SMD":
        p1offset = (Vector2D(-half_rows_x, -half_posn_y)
                    if cfg.pin1_left else
                    Vector2D(half_rows_x, -half_posn_y)
                    )

    # --- Calculate body, fabrication, silk and courtyard dimensions/positions:
    # anchor for SMD-footprints is in the center, for THT-footprints at pin1
    # See Abbreviations at the top.

    # body_overlength is symetrical but keep separated as top/bottom internally.
    overlen_top = cfg.pin_pitch / 2 + cfg.body_overlength
    overlen_bot = cfg.pin_pitch / 2 + cfg.body_overlength

    fabb_h = (cfg.pos_count - 1) * cfg.pin_pitch + overlen_top + overlen_bot
    fabb_w = cfg.body_width
    fabb_t = -(cfg.pin_pitch / 2) - cfg.body_overlength
    fabb_l = -(cfg.body_width / 2) + half_rows_x + cfg.body_offset
    fabb_b = fabb_t + fabb_h
    fabb_r = fabb_l + fabb_w

    slkb_h = fabb_h + 2 * silk_fab_offset
    slkb_w = fabb_w + 2 * silk_fab_offset
    slkb_t = fabb_t - silk_fab_offset
    slkb_l = fabb_l - silk_fab_offset
    slkb_b = fabb_b + silk_fab_offset
    slkb_r = fabb_r + silk_fab_offset

    crt_h = max(fabb_h, (cfg.pos_count - 1) * cfg.pin_pitch + pad.y) + 2 * crt_offset
    crt_w = max(
        cfg.body_width,
		(cfg.row_count - 1) * cfg.row_pitch + (2 * cfg.pads_offset) + pad.x + (cfg.row_pitch if cfg.row_count>1 else 0)
    ) + 2 * crt_offset
    crt_t = -(crt_h / 2) + half_posn_y 
    crt_l = -(crt_w / 2) + half_rows_x
    crt_r = crt_l + crt_w
    crt_b = crt_t + crt_h
    crt_c = Vector2D(crt_l + crt_w / 2, crt_t + crt_h / 2)

    # --- Create pads:
    pad_1 = Pad(type=Pad.TYPE_SMT, shape=Pad.SHAPE_RECT, layers=Pad.LAYERS_SMT, at=[0, 0], size=pad, drill=0)
    pad_n = Pad(type=Pad.TYPE_SMT, shape=Pad.SHAPE_RECT, layers=Pad.LAYERS_SMT, at=[0, 0], size=pad, drill=0)

    padlist = Pad2DArrayFromPads(p1offset, cfg.pos_count, cfg.row_count, cfg.pin_pitch, pad_n, pad_1,
        pads_offset=cfg.pads_offset, pin1_left=cfg.pin1_left, staggered=cfg.isStaggered
    )
    kicad_mod.extend(padlist)
    keepouts_silk = DT.getKeepoutsForPads(pads=padlist, clearance=silk_pad_offset) # ToDo: gc.silk_pad_clearance should be enough

    # --- set general values
    kicad_modg.append(
        Property(name=Property.REFERENCE, text='REF**', at=[half_rows_x, slkb_t - txt_offset], layer='F.SilkS'))
    kicad_modg.append(
        Text(text='${REFERENCE}', at=[half_rows_x, half_posn_y], rotation=90, layer='F.Fab'))
    kicad_modg.append(
        Property(name=Property.VALUE, text=cfg.footpr_name, at=[half_rows_x, slkb_b + txt_offset], layer='F.Fab'))

    # --- create FAB-layer
    chamfer = (cfg.pin_pitch - cfg.pins_width) / 2
    kicad_modg.append(Line(start=[fabb_r, fabb_b], end=[fabb_l, fabb_b], layer='F.Fab', width=gc.fab_line_width))
    if cfg.pin1_left:
        kicad_modg.append(Line(start=[fabb_l + chamfer, fabb_t], end=[fabb_r, fabb_t], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[fabb_l, fabb_b], end=[fabb_l, fabb_t + chamfer], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[fabb_l, fabb_t + chamfer], end=[fabb_l + chamfer, fabb_t], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[fabb_r, fabb_t], end=[fabb_r, fabb_b], layer='F.Fab', width=gc.fab_line_width))
    else:
        kicad_modg.append(Line(start=[fabb_l, fabb_t], end=[fabb_r - chamfer, fabb_t], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[fabb_r, fabb_b], end=[fabb_r, fabb_t + chamfer], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[fabb_r, fabb_t + chamfer], end=[fabb_r - chamfer, fabb_t], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[fabb_l, fabb_t], end=[fabb_l, fabb_b], layer='F.Fab', width=gc.fab_line_width))

    # ToDo: body_width/2 component should be removed from pins_smd_length in yaml's:
    # calculate adjusted lenght for sticking out part:
    length_adj = half_rows_x + cfg.pins_smd_length - cfg.body_width / 2 # + cfg.pins_offset
    DrawPinArray(
        kicad_modg, size=[length_adj, cfg.pins_width], count=cfg.pos_count, pitch=cfg.pin_pitch, rows=cfg.row_count,
        start_r=[fabb_r, 0], start_l=[fabb_l, 0], staggered=True, start_left=cfg.pin1_left,
        layer='F.Fab', linewidth=gc.fab_line_width, grid=0.001
    )

    # --- create SILKSCREEN-layer + pin1 marker
    slk_offset_pad = pad.y/2 + silk_pad_offset
    kicad_modg.append(Line(start=[slkb_l, slkb_t], end=[slkb_r, slkb_t], layer='F.SilkS', width=gc.silk_line_width))
    kicad_modg.append(Line(start=[slkb_l, slkb_b], end=[slkb_r, slkb_b], layer='F.SilkS', width=gc.silk_line_width))

    posleft = range(0, cfg.pos_count, 2)
    posright = range(1, cfg.pos_count, 2)
    if not cfg.pin1_left:
        posleft = range(1, cfg.pos_count, 2)
        posright = range(0, cfg.pos_count, 2)

    if cfg.row_count == 1:
        for pos in posleft:
            if pos == 0:
                kicad_modg.append(Line(start=[slkb_l , -slk_offset_pad], end=[-cfg.pads_offset-pad.x/2+gc.silk_line_width/2 , -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[slkb_l , slkb_t], end=[slkb_l, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[slkb_r, (cfg.pos_count-1)*cfg.pin_pitch+slk_offset_pad],end=[slkb_r, slkb_b],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[slkb_r, -slk_offset_pad], end=[slkb_r, min(slkb_b,(pos+1) * cfg.pin_pitch - slk_offset_pad)], layer='F.SilkS', width=gc.silk_line_width))
            elif pos == cfg.pos_count-1:
                kicad_modg.append(Line(start=[slkb_r, max(slkb_t, (pos-1) * cfg.pin_pitch + slk_offset_pad)], end=[slkb_r, slkb_b], layer='F.SilkS', width=gc.silk_line_width))
            else:
                kicad_modg.append(Line(start=[slkb_r, max(slkb_t, (pos-1) * cfg.pin_pitch + slk_offset_pad)], end=[slkb_r, min(slkb_b,(pos+1) * cfg.pin_pitch - slk_offset_pad)], layer='F.SilkS', width=gc.silk_line_width))
        for pos in posright:
            if pos == 0:
                kicad_modg.append(Line(start=[slkb_r, -slk_offset_pad],end=[cfg.pads_offset+pad.x/2-gc.silk_line_width/2, -slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[slkb_r, slkb_t],end=[slkb_r, -slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[slkb_l, (cfg.pos_count-1)*cfg.pin_pitch+slk_offset_pad],end=[slkb_l, slkb_b],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[slkb_l , -slk_offset_pad],end=[slkb_l, min(slkb_b,(pos+1) * cfg.pin_pitch - slk_offset_pad)], layer='F.SilkS',width=gc.silk_line_width))
            if pos == cfg.pos_count-1:
                kicad_modg.append(Line(start=[slkb_l , max(slkb_t, (pos-1) * cfg.pin_pitch + slk_offset_pad)],end=[slkb_l, slkb_b], layer='F.SilkS',width=gc.silk_line_width))
            else:
                kicad_modg.append(Line(start=[slkb_l , max(slkb_t, (pos-1) * cfg.pin_pitch + slk_offset_pad)],end=[slkb_l, min(slkb_b,(pos+1) * cfg.pin_pitch - slk_offset_pad)], layer='F.SilkS',width=gc.silk_line_width))
    if (cfg.row_count==2):
        if cfg.isSocket:
            # print(pad.x/2+cfg.pads_offset,pad.x/2,cfg.pads_offset)
            kicad_modg.append(Line(start=[pad.x/2+cfg.pads_offset+cfg.row_pitch*1.5, -(pad.y / 2 + 2*gc.silk_line_width + silk_fab_offset)], end=[slkb_r, -(pad.y / 2 + 2*gc.silk_line_width + silk_fab_offset)], layer='F.SilkS', width=gc.silk_line_width))
        else:
            kicad_modg.append(Line(start=[-cfg.pads_offset-pad.x/2+gc.silk_line_width/2, -slk_offset_pad], end=[slkb_l, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[slkb_l , slkb_t], end=[slkb_l, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[slkb_r , slkb_t], end=[slkb_r, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[slkb_l, (cfg.pos_count-1)*cfg.pin_pitch+slk_offset_pad],end=[slkb_l, slkb_b],layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[slkb_r, (cfg.pos_count-1)*cfg.pin_pitch+slk_offset_pad],end=[slkb_r, slkb_b],layer='F.SilkS', width=gc.silk_line_width))
        if slk_offset_pad*2 < cfg.pin_pitch - gc.silk_line_width*2:
            for pos in range(0,cfg.pos_count-1):
                kicad_modg.append(Line(start=[slkb_l, pos*cfg.pin_pitch+slk_offset_pad],end=[slkb_l, (pos+1)*cfg.pin_pitch-slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[slkb_r, pos*cfg.pin_pitch+slk_offset_pad],end=[slkb_r, (pos+1)*cfg.pin_pitch-slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))

	# --- create courtyard:
    kicad_mod.append(Rectangle(start=[DT.roundCrt(crt_l + offset.x), DT.roundCrt(crt_t + offset.y)],
                              end=[DT.roundCrt(crt_r + offset.x), DT.roundCrt(crt_b + offset.y)],
                              layer='F.CrtYd', width=gc.courtyard_line_width
        )
    )

    # --- add model
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
