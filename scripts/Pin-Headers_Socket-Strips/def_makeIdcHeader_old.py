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


def makeIdcHeader(
    global_config: GC.GlobalConfig,
    pos_count: int,
    row_count: int,
    pin_pitch: float,
    row_pitch: float,
    body_width: float,
    body_overlength: float,
    body_offset: float,
    pins_drill: float,
    pad: Vec2DCompatible,
    mating_overlen: float,
    wall_thickness: float,
    notch_width: float,
    orientation: str,
    latching: float,
    latch_length: float,
    latch_width: float,
    mhole_drill: float,
    mhole_pad: Vec2DCompatible,
    mhole_overlength: float,
    mhole_offset: float,
    mhole_nr: str,
    tags_additional: list[str],
    extra_description: str,
    lib_name: str,
    classname: str,
    class_description: str,
):
    # If pins_drill is zero, then create a SMD footprint:
    gc = global_config
    overlen_top = pin_pitch/2 + body_overlength
    overlen_bot = pin_pitch/2 + body_overlength
    pad = Vector2D(pad)

    mhole_pad = Vector2D(mhole_pad)
    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    pin_size = 0.64  # square pin side length; this appears to be the same for all connectors so use a fixed internal value

    mh_present = True if mhole_drill > 0 and mhole_pad.x > 0 and mhole_pad.y > 0 and mhole_overlength > 0 else False
    mh_y = Vector2D(-mhole_overlength, (pos_count - 1) * pin_pitch + mhole_overlength)

    h_fab = (pos_count - 1) * pin_pitch + overlen_top + overlen_bot
    w_fab = body_width
    if pins_drill == 0:
        # Body should be centered for SMT footprints
        l_fab = -w_fab / 2 if body_offset == 0 else body_offset
        t_fab = -overlen_top - (pos_count - 1) * pin_pitch / 2
    else:
        l_fab = (row_pitch * (row_count - 1) - w_fab) / 2 if body_offset == 0 else body_offset
        t_fab = -overlen_top

    # these calculations are so tight that new body styles will probably break them
    h_crt = max(max(h_fab, (pos_count - 1) * pin_pitch + pad.y) + 2 * latch_length, (pos_count - 1) * pin_pitch + 2 * mhole_overlength + mhole_pad.y) + 2 * crtyd_offset
    w_crt = max(body_width, row_pitch * (row_count - 1) + pad.x) + 2 * crtyd_offset if body_offset <= 0 else pad.x / 2 + body_offset + body_width + 2 * crtyd_offset
    if pins_drill == 0:
        # Courtyard should be centered for SMT footprints
        l_crt =  -pad.x / 2 - row_pitch/2- crtyd_offset
        t_crt = min(t_fab - latch_length, -mhole_overlength - mhole_pad.y / 2) - crtyd_offset
    else:
        l_crt = l_fab - crtyd_offset if body_offset <= 0 else -pad.x / 2 - crtyd_offset
        t_crt = min(t_fab - latch_length, -mhole_overlength - mhole_pad.y / 2) - crtyd_offset
    # if orientation == 'Horizontal' and latching and mhole_drill > 0:
    if mh_present and (mhole_offset - mhole_pad.x / 2 < l_fab):
        # horizontal latching with mounting holes is a special case
        l_crt = mhole_offset - mhole_pad.x / 2 - crtyd_offset
        w_crt = -l_crt + body_width + body_offset + crtyd_offset

    if pins_drill == 0:
        # center is [0, 0] for SMD footprints
        center_fab = Vector2D(0, 0)
        center_fp = Vector2D(0, 0)
    else:
        # center of the body (horizontal: middle pin or the center of the middle pins for vertical)
        center_fab = Vector2D(row_pitch * (row_count - 1) / 2 if orientation == 'Vertical' else body_offset + body_width / 2, t_fab + h_fab / 2)
        center_fp = Vector2D(l_crt + w_crt / 2, center_fab.y)

    fab_text_props = gc.get_text_properties_for_layer("F.Fab")
    text_size, text_thickness = fab_text_props.clamp_size(w_fab * 0.6)

    footprint_name = "{3}_{0}x{1:02}{7}_P{2:03.2f}mm{4}{5}_{6}{8}".format(row_count, pos_count, pin_pitch, classname, "_Latch" if latching else "", "{0:03.1f}mm".format(latch_length) if latch_length > 0 else "", orientation, "-1MP" if mh_present else "", "_SMD"if pins_drill==0 else "")
    # footprint_name = footprint_name_base + "_MountHole" if mh_present else footprint_name_base

    if row_count == 1:
        description_rows = "single row"
        tags_rows = "single row"
    elif row_count == 2:
        description_rows = "double rows"
        tags_rows = "double row"
    elif row_count == 3:
        description_rows = "triple rows"
        tags_rows = "triple row"
    elif row_count == 4:
        description_rows = "quadruple rows"
        tags_rows = "quadruple row"
    else:
        raise ValueError("Unsupported number of rows: {0}".format(row_count))

    if pins_drill == 0:
        description = "SMD"
        tags = "SMD"
        mounting_type = ""
    else:
        description = "Through hole"
        tags = "Through hole"
        mounting_type = "THT"

    description = description + " {3}, {0}x{1:02}, {2:03.2f}mm pitch, DIN 41651 / IEC 60603-13, {4}{5}{6}{7}".format(row_count, pos_count, pin_pitch, class_description, description_rows, ", {0:03.1f}mm".format(latch_length) if latch_length > 0 else "", " latches" if latching else "", ", mounting holes" if mh_present else "", orientation.lower())
    tags = tags + " {5} {3} {6} {0}x{1:02} {2:03.2f}mm {4}".format(row_count, pos_count, pin_pitch, class_description, tags_rows, orientation.lower(), mounting_type)

    if len(tags_additional) > 0:
        for t in tags_additional:
            footprint_name = footprint_name + "_" + t
            description = description + ", " + t
            tags = tags + " " + t

    if extra_description:
        description = description + ", " + extra_description

    print(footprint_name)

    footprint_type = FootprintType.SMD if pins_drill == 0 else FootprintType.THT

    # init kicad footprint
    kicad_mod = Footprint(footprint_name, footprint_type)
    kicad_mod.description = description
    kicad_mod.tags = tags

    # instantiate footprint (SMD origin at center, THT at pin 1)
    offset = Vector2D(0, 0)
    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    # set general values
    kicad_modg.append(Property(name=Property.REFERENCE, text='REF**', at=[center_fp.x, t_crt - text_size.y / 2], layer='F.SilkS'))
    kicad_modg.append(Text(text='${REFERENCE}', at=[center_fab.x, center_fab.y], rotation=90, layer='F.Fab', size=text_size, thickness=text_thickness))
    kicad_modg.append(Property(name=Property.VALUE, text=footprint_name, at=[center_fp.x, t_crt + h_crt + text_size.y / 2], layer='F.Fab'))

    # for shrouded headers, fab and silk layers have very similar geometry
    # can use the same code to build lines on both layers with slight changes in values between layers
    # zip together lists with fab and then silk layer settings as the list elements so the same code can draw both layers
    for layer, line_width, lyr_offset, chamfer in zip(['F.Fab', 'F.SilkS'], [gc.fab_line_width, gc.silk_line_width], [0, gc.silk_fab_offset], [min(1, w_fab / 4), 0]):
        # body outline
        if orientation == "Horizontal" and latching:
            # body outline taken from existing KiCad footprint
            body_polygon = [
                (body_offset - lyr_offset, t_fab - lyr_offset), (l_fab + 6.98 + lyr_offset, t_fab - lyr_offset),
                (l_fab + w_fab + lyr_offset, t_fab + 3.17 - lyr_offset), (l_fab + w_fab + lyr_offset, t_fab + 6.99 + lyr_offset),
                (l_fab + 12.7 + lyr_offset, t_fab + 9.14 + lyr_offset), (l_fab + 12.7 + lyr_offset, t_fab + h_fab - 9.14 - lyr_offset),
                (l_fab + w_fab + lyr_offset, t_fab + h_fab - 6.99 - lyr_offset), (l_fab + w_fab + lyr_offset, t_fab + h_fab - 3.17 + lyr_offset),
                (l_fab + 6.98 + lyr_offset, t_fab + h_fab + lyr_offset), (body_offset - lyr_offset, t_fab + h_fab + lyr_offset)
            ]
            # body outline taken from simplified 3M 3000 model (also modify arguments: body_offset=-1.24 and body_width=1.24+15.53)
            # https://www.3m.com/3M/en_US/company-us/all-3m-products/~/3M-Four-Wall-Header-3000-Series/?N=5002385+3290316872&preselect=8709318+8710652+8733900+8734573&rt=rud
            body_polygon = [
                (body_offset - lyr_offset, t_fab - lyr_offset), (l_fab + 7.11 + lyr_offset, t_fab - lyr_offset),
                (l_fab + 16.77 + lyr_offset, t_fab + 3.47 - lyr_offset), (l_fab + 16.77 + lyr_offset, t_fab + 7.44 + lyr_offset),
                (l_fab + 13.21 + lyr_offset, t_fab + 8.07 + lyr_offset), (l_fab + 13.21 + lyr_offset, t_fab + h_fab - 8.07 - lyr_offset),
                (l_fab + 16.77 + lyr_offset, t_fab + h_fab - 7.44 - lyr_offset), (l_fab + 16.77 + lyr_offset, t_fab + h_fab - 3.47 + lyr_offset),
                (l_fab + 7.11 + lyr_offset, t_fab + h_fab + lyr_offset), (body_offset - lyr_offset, t_fab + h_fab + lyr_offset)
            ]
            kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
            # now draw the left side vertical line, which may be broken on the silk layer around mounting holes
            if layer == 'F.SilkS' and mh_present and mhole_pad.x/2 - mhole_offset > -body_offset + gc.silk_fab_offset * 1.5:
                body_polygon = [(body_offset - lyr_offset, t_fab - lyr_offset), (body_offset - lyr_offset, mh_y.x - mhole_pad.x/2)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                body_polygon = [(body_offset - lyr_offset, mh_y.x + mhole_pad.x/2), (body_offset - lyr_offset, mh_y.y - mhole_pad.x/2)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                body_polygon = [(body_offset - lyr_offset, mh_y.y + mhole_pad.x/2), (body_offset - lyr_offset, t_fab + h_fab + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
            else:
                body_polygon = [(body_offset - lyr_offset, t_fab + h_fab + lyr_offset), (body_offset - lyr_offset, t_fab - lyr_offset)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
        else:
            # body outline silk lines need to clear the mounting hole on vertical headers
            if mh_present and layer == 'F.SilkS':
                body_polygon = [(mhole_offset + mhole_pad.x/2 - lyr_offset, t_fab - lyr_offset), (l_fab + w_fab + lyr_offset, t_fab - lyr_offset),
                    (l_fab + w_fab + lyr_offset, t_fab + h_fab + lyr_offset), (mhole_offset + mhole_pad.x/2 - lyr_offset, t_fab + h_fab + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                body_polygon = [(mhole_offset - mhole_pad.x/2 + lyr_offset, t_fab - lyr_offset), (l_fab - lyr_offset, t_fab - lyr_offset),
                    (l_fab - lyr_offset, t_fab + h_fab + lyr_offset), (mhole_offset - mhole_pad.x/2 + lyr_offset, t_fab + h_fab + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
            else:
                if layer == "F.SilkS" and pins_drill == 0:
                    # Break silkscreen for SMD pads
                    body_polygon = [(l_fab - lyr_offset, -((pos_count-1)*pin_pitch/2)-pad.y/2-0.5), (l_fab - lyr_offset, t_fab - lyr_offset),
                        (l_fab + w_fab + lyr_offset, t_fab - lyr_offset), (l_fab +w_fab + lyr_offset, -((pos_count-1)*pin_pitch/2)-pad.y/2-0.5)]
                    kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                    body_polygon = [(l_fab - lyr_offset, ((pos_count-1)*pin_pitch/2)+pad.y/2+0.5), (l_fab - lyr_offset, t_fab + h_fab + lyr_offset),
                        (l_fab + w_fab + lyr_offset, t_fab +h_fab + lyr_offset), (l_fab +w_fab + lyr_offset, ((pos_count-1)*pin_pitch/2)+pad.y/2+0.5)]
                    kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                else:
                    body_polygon = [(l_fab + chamfer - lyr_offset, t_fab - lyr_offset), (l_fab + w_fab + lyr_offset, t_fab - lyr_offset),
                        (l_fab + w_fab + lyr_offset, t_fab + h_fab + lyr_offset), (l_fab - lyr_offset, t_fab + h_fab + lyr_offset),
                        (l_fab - lyr_offset, t_fab + chamfer - lyr_offset)]
                    kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
        if chamfer > 0 and not (orientation == 'Horizontal' and latching):
            kicad_modg.append(Line(start=[l_fab, t_fab + chamfer], end=[l_fab + chamfer, t_fab], layer=layer, width=line_width))

        # vertical mating connector outline (this is the same for both layers)
        if orientation == "Vertical":
            if pins_drill == 0:
                mating_conn_polygon = [(l_fab - lyr_offset, center_fab.y - notch_width/2), (l_fab + wall_thickness, center_fab.y - notch_width/2),
                    (l_fab + wall_thickness, t_fab+wall_thickness), (l_fab + w_fab - wall_thickness, t_fab+wall_thickness),
                    (l_fab + w_fab - wall_thickness, t_fab+h_fab-wall_thickness), (l_fab + wall_thickness, t_fab+h_fab-wall_thickness),
                    (l_fab + wall_thickness, center_fab.y + notch_width/2), (l_fab + wall_thickness, center_fab.y + notch_width/2),
                    (l_fab - lyr_offset, center_fab.y + notch_width/2)]
                if layer == "F.Fab":
                    # Only append mating connector outline in F.Fab for SMD footprints (silkscreen would be on top of pads)
                    kicad_mod.append(PolygonLine(shape=mating_conn_polygon, layer=layer, width=line_width))
            else:
                mating_conn_polygon = [(l_fab - lyr_offset, center_fab.y - notch_width/2), (l_fab + wall_thickness, center_fab.y - notch_width/2),
                    (l_fab + wall_thickness, -mating_overlen), (l_fab + w_fab - wall_thickness, -mating_overlen),
                    (l_fab + w_fab - wall_thickness, (pos_count - 1) * pin_pitch + mating_overlen), (l_fab + wall_thickness, (pos_count - 1) * pin_pitch + mating_overlen),
                    (l_fab + wall_thickness, center_fab.y + notch_width/2), (l_fab + wall_thickness, center_fab.y + notch_width/2),
                    (l_fab - lyr_offset, center_fab.y + notch_width/2)]
                kicad_mod.append(PolygonLine(shape=mating_conn_polygon, layer=layer, width=line_width))

        # horizontal mating connector 'notch' lines
        if orientation == 'Horizontal' and not latching:
            kicad_modg.append(Line(start=[body_offset - lyr_offset, center_fab.y - notch_width / 2], end=[l_fab + w_fab + lyr_offset, center_fab.y - notch_width / 2], layer=layer, width=line_width))
            kicad_modg.append(Line(start=[body_offset - lyr_offset, center_fab.y + notch_width / 2], end=[l_fab + w_fab + lyr_offset, center_fab.y + notch_width / 2], layer=layer, width=line_width))

        # vertical latches (horizontal latches are off the PCB and not shown)
        if orientation == "Vertical" and latching and latch_length > 0:
            # body outline silk lines need to clear the mounting hole on vertical headers
            if mh_present and layer == "F.SilkS":
                # top latch
                latch_top_polygon = [(center_fab.x - latch_width/2 - lyr_offset, mh_y.x - mhole_pad.y/2 + lyr_offset), (center_fab.x - latch_width/2 - lyr_offset, t_fab - latch_length - lyr_offset),
                    (center_fab.x + latch_width/2 + lyr_offset, t_fab - latch_length - lyr_offset), (center_fab.x + latch_width/2 + lyr_offset, mh_y.x - mhole_pad.y/2 + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=latch_top_polygon, layer=layer, width=line_width))
                # bottom latch
                latch_bottom_polygon = [(center_fab.x - latch_width/2 - lyr_offset, mh_y.y + mhole_pad.y/2 - lyr_offset), (center_fab.x - latch_width/2 - lyr_offset, t_fab + h_fab + latch_length + lyr_offset),
                    (center_fab.x + latch_width/2 + lyr_offset, t_fab + h_fab + latch_length + lyr_offset), (center_fab.x + latch_width/2 + lyr_offset, mh_y.y + mhole_pad.y/2 - lyr_offset)]
                kicad_mod.append(PolygonLine(shape=latch_bottom_polygon, layer=layer, width=line_width))
            else:
                # top latch
                latch_top_polygon = [(center_fab.x - latch_width/2 - lyr_offset, t_fab - lyr_offset), (center_fab.x - latch_width/2 - lyr_offset, t_fab - latch_length - lyr_offset),
                    (center_fab.x + latch_width/2 + lyr_offset, t_fab - latch_length - lyr_offset), (center_fab.x + latch_width/2 + lyr_offset, t_fab - lyr_offset)]
                kicad_mod.append(PolygonLine(shape=latch_top_polygon, layer=layer, width=line_width))
                # bottom latch
                latch_bottom_polygon = [(center_fab.x - latch_width/2 - lyr_offset, t_fab + h_fab + lyr_offset), (center_fab.x - latch_width/2 - lyr_offset, t_fab + h_fab + latch_length + lyr_offset),
                    (center_fab.x + latch_width/2 + lyr_offset, t_fab + h_fab + latch_length + lyr_offset), (center_fab.x + latch_width/2 + lyr_offset, t_fab + h_fab + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=latch_bottom_polygon, layer=layer, width=line_width))

    # horizontal pin outlines (only applies if the body is right of the leftmost pin row)
    # if orientation == 'Horizontal' and not latching:
    if body_offset > 0:
        for row in range(pos_count):
            horiz_pin_polygon = [(body_offset, pin_pitch * row - pin_size / 2), (-pin_size / 2, pin_pitch * row - pin_size / 2),
                (-pin_size / 2, pin_pitch * row + pin_size / 2), (body_offset, pin_pitch * row + pin_size / 2)]
            kicad_modg.append(PolygonLine(shape=horiz_pin_polygon, layer='F.Fab', width=gc.fab_line_width))

    # silk pin 1 mark (triangle to the left of pin 1)
    slk_mark_height = 1
    slk_mark_width = 1
    if pins_drill == 0:
        slk_polygon = [(l_fab - gc.silk_fab_offset, -((pos_count-1)*pin_pitch/2)-pad.y/2-0.5), (l_fab - gc.silk_fab_offset-1.5, -((pos_count-1)*pin_pitch/2)-pad.y/2-0.5)]
    else:
        slk_mark_tip = min(l_fab, -pad.x / 2) - 0.5 # offset 0.5mm from pin 1 or the body
        slk_polygon = [(slk_mark_tip, 0), (slk_mark_tip - slk_mark_width, -slk_mark_height / 2),
            (slk_mark_tip - slk_mark_width, slk_mark_height / 2), (slk_mark_tip, 0)]
    kicad_mod.append(PolygonLine(shape=slk_polygon, layer='F.SilkS', width=gc.silk_line_width))

    # create courtyard
    if pins_drill == 0 and orientation == "Vertical" and not latching:
        #         l_crt =  -pad.x / 2 - row_pitch/2- crt_offset
        crt_polygon = [
            (roundCrt(l_fab - crtyd_offset), roundCrt(t_crt)),
            (roundCrt(l_fab - crtyd_offset), roundCrt(-((pos_count-1)*pin_pitch/2)-pad.y/2 - crtyd_offset)),
            (roundCrt(l_crt), roundCrt(-((pos_count-1)*pin_pitch/2)-pad.y/2 - crtyd_offset)),
            (roundCrt(l_crt), roundCrt(((pos_count-1)*pin_pitch/2)+pad.y/2 + crtyd_offset)),
            (roundCrt(l_fab - crtyd_offset), roundCrt(((pos_count-1)*pin_pitch/2)+pad.y/2 + crtyd_offset)),
            (roundCrt(l_fab - crtyd_offset), roundCrt(-t_crt)),
            (roundCrt(-l_fab + crtyd_offset), roundCrt(-t_crt)),
            (roundCrt(-l_fab + crtyd_offset), roundCrt(((pos_count-1)*pin_pitch/2)+pad.y/2 + crtyd_offset)),
            (roundCrt(-l_crt), roundCrt(((pos_count-1)*pin_pitch/2)+pad.y/2 + crtyd_offset)),
            (roundCrt(-l_crt), roundCrt(-((pos_count-1)*pin_pitch/2)-pad.y/2 - crtyd_offset)),
            (roundCrt(-l_fab + crtyd_offset), roundCrt(-((pos_count-1)*pin_pitch/2)-pad.y/2 - crtyd_offset)),
            (roundCrt(-l_fab + crtyd_offset), roundCrt(t_crt)),
            (roundCrt(l_fab - crtyd_offset), roundCrt(t_crt))
        ]
        kicad_mod.append(PolygonLine(shape=crt_polygon, layer='F.CrtYd', width=gc.courtyard_line_width))
    else:
        kicad_mod.append(RectLine(start=[roundCrt(l_crt), roundCrt(t_crt)], end=[roundCrt(l_crt + w_crt),
                    roundCrt(t_crt + h_crt)], layer='F.CrtYd', width=gc.courtyard_line_width))

    # create pads (first the left row then the right row)
    if pins_drill == 0:
        pad_type = Pad.TYPE_SMT
        pad_shape = Pad.SHAPE_ROUNDRECT
        pad_layers = Pad.LAYERS_SMT
    else:
        pad_type = Pad.TYPE_THT
        pad_shape = Pad.SHAPE_OVAL
        pad_layers = Pad.LAYERS_THT

    if pins_drill == 0:
        # For SMD footprints, pad 1 location is not (0,0)
        for start_pos, initial in zip([-row_pitch/2, row_pitch/2], range(1, row_count + 1)):
            kicad_modg.append(PadArray(pincount=pos_count, spacing=[0,pin_pitch], start=[start_pos,-(pos_count-1)*pin_pitch/2], initial=initial, increment=row_count,
                type=pad_type, shape=pad_shape, size=pad, drill=pins_drill, layers=pad_layers,
                round_radius_handler=global_config.roundrect_radius_handler))
    else:
        for start_pos, initial in zip([0, row_pitch], range(1, row_count + 1)):
            kicad_modg.append(PadArray(pincount=pos_count, spacing=[0,pin_pitch], start=[start_pos,0], initial=initial, increment=row_count,
                type=pad_type, shape=pad_shape, size=pad, drill=pins_drill, layers=pad_layers,
                round_radius_handler=global_config.roundrect_radius_handler))

    # create mounting hole pads
    if mh_present:
        for mh_y_offset in mh_y:
            kicad_modg.append(Pad(number=mhole_nr, type=Pad.TYPE_THT, shape=Pad.SHAPE_OVAL, at=[mhole_offset, mh_y_offset], size=mhole_pad,
                drill=mhole_drill, layers=Pad.LAYERS_THT))

    # add model (even if there are mounting holes on the footprint do not include that in the 3D model)
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

