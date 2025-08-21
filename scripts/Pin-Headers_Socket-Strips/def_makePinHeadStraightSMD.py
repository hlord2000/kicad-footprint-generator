#!/usr/bin/env python

from math import sqrt

from KicadModTree import (
    Footprint,
    FootprintType,
    KicadPrettyLibrary,
    Line,
    Model,
    Pad,
    PadArray,
    PolygonLine,
    Property,
    Rectangle,
    RectLine,
    Text,
    Translation,
)
from kilibs.geom import Vec2DCompatible, Vector2D
from scripts.tools.drawing_tools import roundCrt
from scripts.tools.global_config_files import global_config as GC

txt_offset = 1


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
def makePinHeadStraightSMD(
    global_config: GC.GlobalConfig,
    pos_count: int,
    row_count: int,
    pin_pitch: float,
    row_pitch: float,
    smd_pad_offset: float,
    posx_pin_length: float,
    pin_width: float,
    body_width: float,
    body_overlength: float,
    pad: Vec2DCompatible,
    start_left: bool = True,
    tags_additional: list[str] = [],
    lib_name: str = "Pin_Headers",
    classname: str = "Pin_Header",
    class_description: str = "pin header",
    isSocket: bool = False,
):
    gc = global_config
    overlen_top = pin_pitch/2 + body_overlength
    overlen_bot = pin_pitch/2 + body_overlength

    pad = Vector2D(pad)
    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    # This is set a bit further out than normal, not quite clear why.
    # silk_pad_offset = gc.silk_pad_offset
    silk_pad_offset = gc.silk_pad_clearance + gc.silk_fab_offset

    pins_drill = 0.5
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

    w_crt = (
        max(body_width, row_pitch * (row_count - 1) + 2 * smd_pad_offset + pad.x)
        + 2 * crtyd_offset
    )
    h_crt = max(h_fab, (pos_count - 1) * pin_pitch + pad.y) + 2 * crtyd_offset
    l_crt = row_pitch * (row_count - 1) / 2 - w_crt / 2
    t_crt = (pos_count - 1) * pin_pitch / 2 - h_crt / 2

    # if pin_pitch == 2.54:
    #    footprint_name = "Pin_Header_Straight_{0}x{1:02}".format(row_count, pos_count)
    # else:
    footprint_name = "{3}_{0}x{1:02}_P{2:03.2f}mm_Vertical_SMD".format(row_count, pos_count, pin_pitch,classname)

    description = "surface-mounted straight {3}, {0}x{1:02}, {2:03.2f}mm pitch".format(row_count, pos_count, pin_pitch,class_description)
    tags = "Surface mounted {3} SMD {0}x{1:02} {2:03.2f}mm".format(row_count, pos_count, pin_pitch,class_description)
    if row_count == 1:
        description = description + ", single row"
        tags = tags + " single row"
        if start_left:
            description = description + ", style 1 (pin 1 left)"
            tags = tags + " style1 pin1 left"
            footprint_name = footprint_name + "_Pin1Left"
        else:
            description = description + ", style 2 (pin 1 right)"
            tags = tags + " style2 pin1 right"
            footprint_name = footprint_name + "_Pin1Right"
    elif row_count == 2:
        description = description + ", double rows"
        tags = tags + " double row"

    if len(tags_additional) > 0:
        for t in tags_additional:
            footprint_name = footprint_name + "_" + t
            description = description + ", " + t
            tags = tags + " " + t

    print(footprint_name)

    # init kicad footprint
    kicad_mod = Footprint(footprint_name, FootprintType.SMD)
    kicad_mod.description = description
    kicad_mod.tags = tags

    # anchor for SMD-symbols is in the center, for THT-sybols at pin1
    offset = Vector2D(-(row_count-1)*row_pitch/2, -(pos_count-1)*pin_pitch/2.0)

    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    # set general values
    kicad_modg.append(
        Property(name=Property.REFERENCE, text='REF**', at=[row_pitch * (row_count - 1) / 2, t_slk - txt_offset], layer='F.SilkS'))
    kicad_modg.append(
        Text(text='${REFERENCE}', at=[pin_pitch/2*(row_count-1),(pos_count-1)*pin_pitch/2.0], rotation=90, layer='F.Fab'))
    kicad_modg.append(
        Property(name=Property.VALUE, text=footprint_name, at=[row_pitch * (row_count - 1) / 2, t_slk + h_slk + txt_offset], layer='F.Fab'))

    cleft = range(0, pos_count, 2)
    cright = range(1, pos_count, 2)
    if not start_left:
        cleft = range(1, pos_count, 2)
        cright = range(0, pos_count, 2)

    # create FAB-layer
    chamfer = (pin_pitch - pin_width) / 2
    kicad_modg.append(Line(start=[l_fab + w_fab, t_fab+h_fab], end=[l_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))
    if start_left == True:
        kicad_modg.append(Line(start=[l_fab + chamfer, t_fab], end=[l_fab + w_fab, t_fab], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab, t_fab+h_fab], end=[l_fab, t_fab+chamfer], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab, t_fab+chamfer], end=[l_fab + chamfer, t_fab], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab + w_fab, t_fab], end=[l_fab + w_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))
    else:
        kicad_modg.append(Line(start=[l_fab, t_fab], end=[l_fab + w_fab - chamfer, t_fab], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab + w_fab, t_fab+h_fab], end=[l_fab + w_fab, t_fab+chamfer], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab + w_fab, t_fab+chamfer], end=[l_fab + w_fab - chamfer, t_fab], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab, t_fab], end=[l_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))

    if row_count == 1:
        for c in cleft:
            kicad_modg.append(Line(start=[l_fab, c*pin_pitch-pin_width/2], end=[-posx_pin_length, c*pin_pitch-pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[-posx_pin_length, c*pin_pitch-pin_width/2], end=[-posx_pin_length, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[-posx_pin_length, c*pin_pitch+pin_width/2], end=[l_fab, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
        for c in cright:
            kicad_modg.append(Line(start=[l_fab + w_fab, c*pin_pitch-pin_width/2], end=[posx_pin_length, c*pin_pitch-pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[posx_pin_length, c*pin_pitch-pin_width/2], end=[posx_pin_length, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[posx_pin_length, c*pin_pitch+pin_width/2], end=[l_fab + w_fab, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
    elif row_count == 2:
        for c in range(0,pos_count):
            kicad_modg.append(Line(start=[l_fab, c*pin_pitch-pin_width/2], end=[-posx_pin_length+pin_pitch/2, c*pin_pitch-pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[-posx_pin_length+pin_pitch/2, c*pin_pitch-pin_width/2], end=[-posx_pin_length+pin_pitch/2, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[-posx_pin_length+pin_pitch/2, c*pin_pitch+pin_width/2], end=[l_fab, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[l_fab + w_fab, c*pin_pitch-pin_width/2], end=[pin_pitch/2+posx_pin_length, c*pin_pitch-pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[pin_pitch/2+posx_pin_length, c*pin_pitch-pin_width/2], end=[pin_pitch/2+posx_pin_length, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[pin_pitch/2+posx_pin_length, c*pin_pitch+pin_width/2], end=[l_fab + w_fab, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))

    # create SILKSCREEN-layer + pin1 marker
    slk_offset_pad = pad.y/2 + silk_pad_offset
    kicad_modg.append(Line(start=[l_slk, t_slk], end=[l_slk + w_slk, t_slk], layer='F.SilkS', width=gc.silk_line_width))
    kicad_modg.append(Line(start=[l_slk, t_slk+h_slk], end=[l_slk + w_slk, t_slk+h_slk], layer='F.SilkS', width=gc.silk_line_width))

    if row_count == 1:
        for c in cleft:
            if c == 0:
                kicad_modg.append(Line(start=[l_slk , -slk_offset_pad], end=[-smd_pad_offset-pad.x/2+gc.silk_line_width/2 , -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk , t_slk], end=[l_slk, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk+w_slk, (pos_count-1)*pin_pitch+slk_offset_pad],end=[l_slk+w_slk, t_slk+h_slk],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk+w_slk, -slk_offset_pad], end=[l_slk+w_slk, min(t_slk+h_slk,(c+1) * pin_pitch - slk_offset_pad)], layer='F.SilkS', width=gc.silk_line_width))
            elif c == pos_count-1:
                kicad_modg.append(Line(start=[l_slk+w_slk, max(t_slk, (c-1) * pin_pitch + slk_offset_pad)], end=[l_slk+w_slk, t_slk+h_slk], layer='F.SilkS', width=gc.silk_line_width))
            else:
                kicad_modg.append(Line(start=[l_slk+w_slk, max(t_slk, (c-1) * pin_pitch + slk_offset_pad)], end=[l_slk+w_slk, min(t_slk+h_slk,(c+1) * pin_pitch - slk_offset_pad)], layer='F.SilkS', width=gc.silk_line_width))
        for c in cright:
            if c == 0:
                kicad_modg.append(Line(start=[l_slk+w_slk, -slk_offset_pad],end=[smd_pad_offset+pad.x/2-gc.silk_line_width/2, -slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk+w_slk, t_slk],end=[l_slk+w_slk, -slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk, (pos_count-1)*pin_pitch+slk_offset_pad],end=[l_slk, t_slk+h_slk],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk , -slk_offset_pad],end=[l_slk, min(t_slk+h_slk,(c+1) * pin_pitch - slk_offset_pad)], layer='F.SilkS',width=gc.silk_line_width))
            if c == pos_count-1:
                kicad_modg.append(Line(start=[l_slk , max(t_slk, (c-1) * pin_pitch + slk_offset_pad)],end=[l_slk, t_slk+h_slk], layer='F.SilkS',width=gc.silk_line_width))
            else:
                kicad_modg.append(Line(start=[l_slk , max(t_slk, (c-1) * pin_pitch + slk_offset_pad)],end=[l_slk, min(t_slk+h_slk,(c+1) * pin_pitch - slk_offset_pad)], layer='F.SilkS',width=gc.silk_line_width))
    if (row_count==2):
        if isSocket:
            # print(pad.x/2+smd_pad_offset,pad.x/2,smd_pad_offset)
            kicad_modg.append(Line(start=[pad.x/2+smd_pad_offset+row_pitch, -(pad.y / 2 + 2*gc.silk_line_width + gc.silk_fab_offset)], end=[l_slk+w_slk, -(pad.y / 2 + 2*gc.silk_line_width + gc.silk_fab_offset)], layer='F.SilkS', width=gc.silk_line_width))
        else:
            kicad_modg.append(Line(start=[-smd_pad_offset+pin_pitch/2-pad.x/2+gc.silk_line_width/2, -slk_offset_pad], end=[l_slk, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[l_slk , t_slk], end=[l_slk, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[l_slk+w_slk , t_slk], end=[l_slk+w_slk, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[l_slk, (pos_count-1)*pin_pitch+slk_offset_pad],end=[l_slk, t_slk+h_slk],layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[l_slk+w_slk, (pos_count-1)*pin_pitch+slk_offset_pad],end=[l_slk+w_slk, t_slk+h_slk],layer='F.SilkS', width=gc.silk_line_width))
        if slk_offset_pad*2 < pin_pitch - gc.silk_line_width*2:
            for c in range(0,pos_count-1):
                kicad_modg.append(Line(start=[l_slk, c*pin_pitch+slk_offset_pad],end=[l_slk, (c+1)*pin_pitch-slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk+w_slk, c*pin_pitch+slk_offset_pad],end=[l_slk+w_slk, (c+1)*pin_pitch-slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
    # create courtyard
    kicad_mod.append(RectLine(start=[roundCrt(l_crt + offset.x), roundCrt(t_crt + offset.y)],
                              end=[roundCrt(l_crt + offset.x + w_crt), roundCrt(t_crt + offset.y + h_crt)],
                              layer='F.CrtYd', width=gc.courtyard_line_width))

    # create pads
    pad_type = Pad.TYPE_SMT
    pad_shape1 = Pad.SHAPE_RECT
    pad_layers = Pad.LAYERS_SMT

    if row_count == 1:
        for c in cleft:
            kicad_modg.append(Pad(number=c+1, type=pad_type, shape=pad_shape1, at=[-smd_pad_offset, c*pin_pitch], size=pad, drill=pins_drill,layers=pad_layers))
        for c in cright:
            kicad_modg.append(Pad(number=c+1, type=pad_type, shape=pad_shape1, at=[smd_pad_offset, c * pin_pitch], size=pad, drill=pins_drill,layers=pad_layers))
    elif row_count == 2:
        p = 1
        for c in range(0, pos_count):
            if isSocket:
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[pin_pitch/2+smd_pad_offset, c * pin_pitch], size=pad, drill=pins_drill,layers=pad_layers))
                p=p+1
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[-smd_pad_offset+pin_pitch/2, c * pin_pitch], size=pad, drill=pins_drill, layers=pad_layers))
                p=p+1
            else:
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[-smd_pad_offset+pin_pitch/2, c * pin_pitch], size=pad, drill=pins_drill, layers=pad_layers))
                p=p+1
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[smd_pad_offset+pin_pitch/2, c * pin_pitch], size=pad, drill=pins_drill,layers=pad_layers))
                p=p+1

    # add model
    kicad_modg.append(
        Model(
            filename=gc.model_3d_prefix
            + lib_name
            + ".3dshapes/"
            + footprint_name
            + global_config.model_3d_suffix
        )
    )

    # write file
    lib = KicadPrettyLibrary(lib_name, None)
    lib.save(kicad_mod)

