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


# THT Angled (Horizontal) PinSocket:
#####################################
# <--------------------------------------> body_width
#                                             <- ------> row_pitch
#                                          <-> body_offset
# +---------------------------------------+            ---+
# |                                       |  OOO      OOO |    ^
# |                                       |  OOO ==== OOO | ^  pin_width
# |                                       |  OOO      OOO   |  v
# +---------------------------------------+                 pin_pitch
# |                                       |  OOO      OOO   |
# |                                       |  OOO ==== OOO   v
# |                                       |  OOO      OOO
# +---------------------------------------+
#
def makeSocketStripAngled(
    global_config: GC.GlobalConfig,
    pos_count: int,
    row_count: int,
    pin_pitch: float,
    row_pitch: float,
    body_width: float,
    body_offset: float,
    pin_width: float,
    pins_drill: float,
    pad: Vec2DCompatible,
    tags_additional: list[str] = [],
    lib_name: str = "Socket_Strips",
    class_name: str = "Socket_Strip",
    class_description: str = "socket strip",
    name_format: str | None = None,
):
    gc = global_config
    pad = Vector2D(pad)
    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    h_fabb = (pos_count - 1) * pin_pitch + pin_pitch / 2 + pin_pitch / 2
    w_fabb = -body_width
    l_fabb = -1 * (row_pitch * (row_count - 1) + body_offset)
    t_fabb = -pin_pitch / 2
    t_fabp = -pin_width / 2

    w_slkb = w_fabb - 2 * gc.silk_fab_offset
    l_slkb = l_fabb + gc.silk_fab_offset
    t_slkb = t_fabb - gc.silk_fab_offset
    l_slkp = l_slkb + w_slkb
    t_slkp = t_fabp - gc.silk_fab_offset

    w_crt = -1*(pin_pitch / 2 + (row_count - 1) * row_pitch + body_offset + body_width  + 2 * crtyd_offset)
    h_crt = h_fabb + 2 * crtyd_offset
    l_crt = pin_pitch / 2 + crtyd_offset
    t_crt = -pin_pitch / 2 - crtyd_offset

    if name_format is None:
        name_format = "{class_name}_{row_count}x{pos_count:02}_P{pitch:03.2f}mm_Horizontal"
    footprint_name = name_format.format(class_name=class_name, row_count=row_count, pos_count=pos_count, pitch=pin_pitch)

    description = "Through hole angled {4}, {0}x{1:02}, {2:03.2f}mm pitch, {3}mm socket length".format(row_count, pos_count,
                                                                                                    pin_pitch,
                                                                                                    body_width,
                                                                                                    class_description)
    tags = "Through hole angled {3} THT {0}x{1:02} {2:03.2f}mm".format(row_count, pos_count, pin_pitch, class_description)
    if (row_count == 1):
        description = description + ", single row"
        tags = tags + " single row"
    elif row_count == 2:
        description = description + ", double rows"
        tags = tags + " double row"
    elif row_count == 3:
        description = description + ", triple rows"
        tags = tags + " triple row"

    if len(tags_additional) > 0:
        for t in tags_additional:
            footprint_name = footprint_name + "_" + t
            description = description + ", " + t
            tags = tags + " " + t

    print(footprint_name)

    # init kicad footprint
    kicad_mod = Footprint(footprint_name, FootprintType.THT)
    kicad_mod.description = description
    kicad_mod.tags = tags

    # anchor for SMD-symbols is in the center, for THT-sybols at pin1
    offset = Vector2D(0, 0)
    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    # set general values
    kicad_modg.append(
        Property(name=Property.REFERENCE, text='REF**', at=[l_crt + w_crt / 2, t_crt + crtyd_offset - txt_offset], layer='F.SilkS'))
    kicad_modg.append(
        Text(text='${REFERENCE}', at=[l_crt + w_crt / 2, t_crt + crtyd_offset - txt_offset], layer='F.Fab'))
    kicad_modg.append(
        Property(name=Property.VALUE, text=footprint_name, at=[l_crt + w_crt / 2, t_crt + h_crt - crtyd_offset + txt_offset],
             layer='F.Fab'))

    # create FAB-layer
    y1 = t_fabb
    yp = t_fabp
    for r in range(1, pos_count + 1):
        kicad_modg.append(RectLine(start=[l_fabb, y1], end=[l_fabb + w_fabb, y1 + pin_pitch], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(
            RectLine(start=[0, yp], end=[l_fabb , yp + pin_width], layer='F.Fab', width=gc.fab_line_width))
        y1 = y1 + pin_pitch
        yp = yp + pin_pitch

    # create SILKSCREEN-layer + pin1 marker
    y1 = t_slkb
    yp = t_slkp
    for r in range(1, pos_count + 1):
        if pos_count == 1 and r == 1:
            kicad_modg.append(
                RectLine(start=[l_slkb, y1], end=[l_slkp, y1 + pin_pitch + 2 * gc.silk_fab_offset], layer='F.SilkS',
                         width=gc.silk_line_width))
        if (r == 1 or r == pos_count):
            kicad_modg.append(RectLine(start=[l_slkb, y1], end=[l_slkp, y1 + pin_pitch + gc.silk_fab_offset], layer='F.SilkS',
                                       width=gc.silk_line_width))
            y1 = y1 + gc.silk_fab_offset
        else:
            kicad_modg.append(RectLine(start=[l_slkb, y1], end=[l_slkp, y1 + pin_pitch], layer='F.SilkS', width=gc.silk_line_width))

        kicad_modg.append(Line(start=[-1*((row_count - 1) * row_pitch + pad.x / 2 + gc.silk_fab_offset+gc.silk_line_width), yp], end=[l_slkb, yp], layer='F.SilkS',width=gc.silk_line_width))
        kicad_modg.append(Line(start=[-1*((row_count - 1) * row_pitch + pad.x / 2 + gc.silk_fab_offset+gc.silk_line_width), yp + pin_width + 2 * gc.silk_fab_offset],end=[l_slkb, yp + pin_width + 2 * gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
        if row_count > 1:
            for c in range(2, row_count + 1):
                kicad_modg.append(Line(start=[-1*((c - 2) * row_pitch + pad.x / 2 + gc.silk_fab_offset+gc.silk_line_width), yp],
                                       end=[-1*((c - 1) * row_pitch - pad.x / 2 - gc.silk_fab_offset-gc.silk_line_width), yp], layer='F.SilkS',
                                       width=gc.silk_line_width))
                kicad_modg.append(
                    Line(start=[-1*((c - 2) * row_pitch + pad.x / 2 + gc.silk_fab_offset+gc.silk_line_width), yp + pin_width + 2 * gc.silk_fab_offset],
                         end=[-1*((c - 1) * row_pitch - pad.x / 2 - gc.silk_fab_offset-gc.silk_line_width), yp + pin_width + 2 * gc.silk_fab_offset],
                         layer='F.SilkS', width=gc.silk_line_width))
        if r == 1:
            y = y1 + gc.silk_line_width
            while y < y1 + pin_pitch + 2 * gc.silk_fab_offset:
                kicad_modg.append(Line(start=[l_slkb, y], end=[l_slkp, y], layer='F.SilkS', width=gc.silk_line_width))
                y = y + gc.silk_line_width
        y1 = y1 + pin_pitch
        yp = yp + pin_pitch

    kicad_modg.append(PolygonLine(shape=[[0, -pin_pitch / 2], [pin_pitch / 2, -pin_pitch / 2], [pin_pitch / 2, 0]], layer='F.SilkS', width=gc.silk_line_width))

    # create courtyard
    kicad_mod.append(RectLine(start=[roundCrt(l_crt + offset.x), roundCrt(t_crt + offset.y)],
                              end=[roundCrt(l_crt + offset.x + w_crt), roundCrt(t_crt + offset.y + h_crt)],
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
            x1 = x1 - row_pitch

        y1 = y1 + pin_pitch

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

