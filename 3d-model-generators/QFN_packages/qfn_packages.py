import cadquery as cq

from src.generators.no_lead.configuration import (  # type: ignore
    NoLeadConfiguration,
)


def make_qfn(
    nlc: NoLeadConfiguration,
) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane | None, cq.Workplane | None]:

    marker = nlc.marker

    # Body size parameters
    e = nlc.body_size_x.nominal
    d = nlc.body_size_y.nominal
    a1 = nlc.body_pcb_gap.maximum
    a2 = nlc.body_height.maximum
    body_fillet = nlc.body_fillet

    # Lead parameters
    lead_height = nlc.lead_height.nominal
    lead_width_h = nlc.lead_width_h.nominal
    lead_width_v = nlc.lead_width_v.nominal
    lead_len_h = nlc.lead_len_h.nominal
    lead_len_v = nlc.lead_len_v.nominal
    lead_to_edge = nlc.lead_to_edge.nominal
    lead_shape = nlc.lead_shape
    lead_shape_custom = nlc.lead_shape_custom
    npx = nlc.num_pins_x
    npy = nlc.num_pins_y
    ep_chamfer = nlc.ep_chamfer.nominal

    # Excluded pins:
    excluded_pins = nlc.deleted_pins + nlc.hidden_pins

    if a1 < 0.02:
        print("A1 can NOT be zero (or this script will fail). Setting A1 to 0.02.")
        a1 = 0.02

    a = a1 + a2

    if lead_to_edge == 0.0:
        case = cq.Workplane("XY").box(e - a1, d - a1, a2)  # margin to see fused pins
    else:
        case = cq.Workplane("XY").box(e, d, a2)  # NO margin, pins don't emerge
    if body_fillet != 0.0:
        case.edges("|X").fillet(body_fillet)
        case.edges("|Z").fillet(body_fillet)
    # translate the object
    case = case.translate((0, 0, a2 / 2 + a1)).rotate((0, 0, 0), (0, 0, 1), 0)

    # first pin indicator is created with a cylindrical pocket
    marker_diameter = max(d, e) / 10.0
    if min(d, e) < 5 * marker_diameter:
        marker_edge_clearance = marker_diameter / 4.0
    else:
        marker_edge_clearance = marker_diameter / 2.0
    marker_depth = 0.050
    marker_dx = nlc.marker_dx
    marker_dy = nlc.marker_dy
    if marker_dx is None:
        marker_dx = marker_edge_clearance
    if marker_dy is None:
        marker_dy = marker_edge_clearance

    if lead_shape in ("concave", "cshaped"):
        if npy != 0:
            marker_dx = marker_dx + lead_len_h - a1 / 2
        if npx != 0:
            marker_dy = marker_dy + lead_len_v - a1 / 2

    if marker == "bar":
        pinmark = cq.Workplane(
            "XY", (-e / 2 + marker_diameter / 2 + marker_dx, 0, a - marker_depth / 2)
        ).box(marker_diameter, d - 2 * marker_dy, marker_depth)
        case = case.cut(pinmark)
    elif marker == "circle":
        circle_center_x = -e / 2 + marker_diameter / 2 + marker_dx
        circle_center_y = d / 2 - marker_diameter / 2 - marker_dy
        pinmark = (
            cq.Workplane("XY", (circle_center_x, circle_center_y, a))
            .circle(marker_diameter / 2)
            .extrude(-marker_depth)
        )
        case = case.cut(pinmark)
    else:
        pinmark = None

    bpin_shape: dict[str, cq.Workplane] = {}
    for axis, length, width in zip(
        ["x", "y"], [lead_len_h, lead_len_v], [lead_width_h, lead_width_v]
    ):
        if lead_shape == "square":  # square pins
            bpin = (
                cq.Workplane("XY")
                .moveTo(width, 0)
                .lineTo(width, length)
                .lineTo(0, length)
                .lineTo(0, 0)
                .close()
                .extrude(lead_height)
                .translate((-width / 2, -d / 2, 0))
                .rotate((0, 0, 0), (0, 0, 1), -180)
            )
            bpin_shape[axis] = bpin
        elif lead_shape == "rounded":
            bpin = (
                cq.Workplane("XY")
                .moveTo(width, 0)
                .lineTo(width, length - width / 2)
                .threePointArc((width / 2, length), (0, length - width / 2))
                .lineTo(0, 0)
                .close()
                .extrude(lead_height)
                .translate((-width / 2, -d / 2, 0))
                .rotate((0, 0, 0), (0, 0, 1), -180)
            )
            bpin_shape[axis] = bpin
        elif lead_shape == "concave":
            pincut = (
                cq.Workplane("XY")
                .box(width, length, a2 + a1 * 2)
                .translate((0, d / 2 - length / 2, a2 / 2 + a1))
            )
            bpin = (
                cq.Workplane("XY")
                .box(width, length, a2 + a1 * 2)
                .translate((0, d / 2 - length / 2, a2 / 2 + a1))
                .edges("|X")
                .fillet(a1)
                .faces(">Z")
                .edges(">Y")
                .workplane(centerOption="CenterOfMass")
                .circle(width * 0.3)
                .cutThruAll()
            )
            bpin_shape[axis] = bpin
        elif lead_shape == "cshaped":
            bpin = (
                cq.Workplane("XY")
                .box(width, length, a2 + a1 * 2)
                .translate((0, d / 2 - length / 2, a2 / 2 + a1))
                .edges("|X")
                .fillet(a1)
            )
            bpin_shape[axis] = bpin

    pitch_x = nlc.pitch_x.nominal
    pitch_y = nlc.pitch_y.nominal
    pins: list[cq.Workplane] = []
    pincounter = 1
    if lead_shape == "custom":
        for pin_shape in lead_shape_custom:
            first_point = pin_shape[0]
            pin = cq.Workplane("XY").moveTo(first_point[0], first_point[1])
            for i in range(1, len(pin_shape)):
                point = pin_shape[i]
                pin = pin.lineTo(point[0], point[1])
            pin = pin.close().extrude(lead_height)
            pins.append(pin)
        pincounter += 1
    else:
        # create top, bottom side pins
        first_pos_x = (npx - 1) * pitch_x / 2
        for i in range(npx):
            if pincounter not in excluded_pins:
                pin = (
                    bpin_shape["x"]
                    .translate((first_pos_x - i * pitch_x, -lead_to_edge, 0))
                    .rotate((0, 0, 0), (0, 0, 1), 180)
                )
                pins.append(pin)
                if lead_shape == "concave":
                    pinsubtract = pincut.translate(
                        (first_pos_x - i * pitch_x, -lead_to_edge, 0)
                    ).rotate((0, 0, 0), (0, 0, 1), 180)
                    case = case.cut(pinsubtract)
            pincounter += 1

        first_pos_y = (npy - 1) * pitch_y / 2
        for i in range(npy):
            if pincounter not in excluded_pins:
                pin = (
                    bpin_shape["y"]
                    .translate(
                        (first_pos_y - i * pitch_y, (e - d) / 2 - lead_to_edge, 0)
                    )
                    .rotate((0, 0, 0), (0, 0, 1), 270)
                )
                pins.append(pin)
                if lead_shape == "concave":
                    pinsubtract = pincut.translate(
                        (first_pos_y - i * pitch_y, (e - d) / 2 - lead_to_edge, 0)
                    ).rotate((0, 0, 0), (0, 0, 1), 270)
                    case = case.cut(pinsubtract)
            pincounter += 1

        for i in range(npx):
            if pincounter not in excluded_pins:
                pin = bpin_shape["x"].translate(
                    (first_pos_x - i * pitch_x, -lead_to_edge, 0)
                )
                pins.append(pin)
                if lead_shape == "concave":
                    pinsubtract = pincut.translate(
                        (first_pos_x - i * pitch_x, -lead_to_edge, 0)
                    )
                    case = case.cut(pinsubtract)
            pincounter += 1

        for i in range(npy):
            if pincounter not in excluded_pins:
                pin = (
                    bpin_shape["y"]
                    .translate(
                        (first_pos_y - i * pitch_y, (e - d) / 2 - lead_to_edge, 0)
                    )
                    .rotate((0, 0, 0), (0, 0, 1), 90)
                )
                pins.append(pin)
                if lead_shape == "concave":
                    pinsubtract = pincut.translate(
                        (first_pos_y - i * pitch_y, (e - d) / 2 - lead_to_edge, 0)
                    ).rotate((0, 0, 0), (0, 0, 1), 90)
                    case = case.cut(pinsubtract)
            pincounter += 1

    # create exposed thermal pad if requested
    if nlc.has_ep:
        epads: list[cq.Workplane] = []
        ep_size_x = nlc.ep_size_x.nominal
        ep_size_y = nlc.ep_size_y.nominal
        ep_chamfer = nlc.ep_chamfer.nominal
        epad_offset_x = nlc.ep_offset_x.nominal
        epad_offset_y = nlc.ep_offset_y.nominal
        for nx in range(1, nlc.ep_num[0] + 1):
            for ny in range(1, nlc.ep_num[1] + 1):
                offset_x = (
                    -((nlc.ep_num[0] - 1) * nlc.ep_pitch[0]) / 2
                    + (nx - 1) * nlc.ep_pitch[0]
                )
                offset_y = (
                    -((nlc.ep_num[1] - 1) * nlc.ep_pitch[1]) / 2
                    + (ny - 1) * nlc.ep_pitch[1]
                )
                epad: cq.Workplane = (
                    cq.Workplane("XY")
                    .moveTo(-ep_size_x / 2 + ep_chamfer, -ep_size_y / 2)
                    .lineTo(ep_size_x / 2, -ep_size_y / 2)
                    .lineTo(ep_size_x / 2, ep_size_y / 2)
                    .lineTo(-ep_size_x / 2, ep_size_y / 2)
                    .lineTo(-ep_size_x / 2, -ep_size_y / 2 + ep_chamfer)
                    .close()
                    .extrude(a1 + a1 / 2)
                    .translate((epad_offset_x + offset_x, epad_offset_y + offset_y, 0))
                    .rotate((0, 0, 0), (0, 0, 1), nlc.ep_angle)
                )
                epads.append(epad)
        # merge all epads to a single object
        merged_epads = epads[0]
        for p in pins[1:]:
            merged_epads = merged_epads.union(p)
    else:
        merged_epads = None

    # merge all pins to a single object
    merged_pins = pins[0]
    for p in pins[1:]:
        merged_pins = merged_pins.union(p)

    # extract pins from case
    case = case.cut(merged_pins)

    return case, merged_pins, merged_epads, pinmark
