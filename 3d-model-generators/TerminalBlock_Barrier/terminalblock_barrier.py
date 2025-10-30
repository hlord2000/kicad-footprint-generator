import math as math
import os

import cadquery as cq

from _tools import cq_color_correct, export_tools, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from kilibs.declarative_defs.packages.terminal_block_barrier_properties import (
    TerminalBlockBarrierProperties,
)


def generate_model(
    cfg: TerminalBlockBarrierProperties, output_dir: str, enable_vrml: bool
):

    # Load the appropriate colors
    col = shaderColors.named_colors[cfg.body_color_key]
    r, g, b = col.getDiffuseFloat()
    body_color = cq_color_correct.Color(r, g, b)
    col = shaderColors.named_colors[cfg.pins_color_key]
    r, g, b = col.getDiffuseFloat()
    pins_color = cq_color_correct.Color(r, g, b)
    col = shaderColors.named_colors[cfg.cover_color_key]
    r, g, b = col.getDiffuseFloat()
    cover_color = cq_color_correct.Color(r, g, b)

    # Collect the array of pin numbers so that we can handle the one config that has a custom set in a string
    for n_pins in cfg.n_pin_variants:
        # Create the file name based on the rows and pins
        file_name = cfg.getFootprintName(n_pins)
        print(f"        - {file_name}")

        body, pins, cover = generate_parts(cfg, n_pins)

        # Used to wrap all the parts into an assembly
        component = cq.Assembly()
        component.name = file_name
        component.add(body, color=body_color)
        component.add(pins, color=pins_color)
        if cover:
            component.add(cover, color=cover_color)

        # Export the assembly to STEP
        component.save(
            os.path.join(output_dir, file_name + ".step"),
            cq.exporters.ExportTypes.STEP,
            mode=cq.exporters.assembly.ExportModes.FUSED,
            write_pcurves=False,
        )

        # Check for a proper union
        export_tools.check_step_export_union(component, output_dir, file_name)

        # Do STEP post-processing
        export_tools.postprocess_step(component, output_dir, file_name)

        # Export the assembly to VRML
        if enable_vrml:
            parts = [body, pins]
            colors = [cfg.body_color_key, cfg.pins_color_key]
            if cover:
                parts.append(cover)
                colors.append(cfg.cover_color_key)
            export_VRML(os.path.join(output_dir, file_name + ".wrl"), parts, colors)

        # Update the license
        from _tools import add_license

        add_license.addLicenseToStep(
            output_dir,
            file_name + ".step",
            add_license.LIST_int_license,
            add_license.STR_int_licAuthor,
            add_license.STR_int_licEmail,
            add_license.STR_int_licOrgSys,
            add_license.STR_int_licPreProc,
        )


def generate_parts(cfg: TerminalBlockBarrierProperties, n_pins: int):
    """
    Generates the body (case) and pins for the component.
    from the number of pins
    """

    length = cfg.pitch * n_pins - cfg.separator + cfg.side_border * 2
    x_center = (n_pins - 1) * cfg.pitch / 2

    # Generate the case/body
    body = (
        cq.Workplane()
        .rect(length, cfg.width)
        .extrude(cfg.height)
        .translate((x_center, 0))
    )
    # front fillet (back fillet if no back_border)
    if cfg.fillet > 0:
        selector = "|X and >Z"
        if cfg.back_border > 0:
            selector += " and <Y"
        body = body.edges(selector).fillet(cfg.fillet)

    # compute body to remove for each pin
    # barrier cell + back/front/bottom clearance
    body_cut = (
        cq.Workplane("XY")
        .rect(cfg.cell_size.x, cfg.cell_size.y)
        .extrude(-cfg.cell_size.z)
        .translate((0, -cfg.back_border, cfg.height))
    )
    if cfg.clr_bottom > 0:
        body_cut.add(
            cq.Workplane("XY")
            .rect(cfg.cell_size.x, cfg.width + 2.0)
            .extrude(cfg.clr_bottom)
        )
    if cfg.clr_back > 0:
        body_cut.add(
            cq.Workplane("XZ")
            .rect(cfg.cell_size.x, cfg.height)
            .extrude(cfg.clr_back)
            .translate((0, cfg.width / 2, cfg.height / 2 - cfg.separator))
        )
    if cfg.clr_front > 0:
        body_cut.add(
            cq.Workplane("XZ")
            .rect(cfg.cell_size.x, cfg.height)
            .extrude(-cfg.clr_front)
            .translate((0, -cfg.width / 2, cfg.height / 2 - cfg.separator))
        )

    for i in range(1, n_pins + 1):
        body = body.cut(body_cut.translate(((i - 1) * cfg.pitch, 0, 0)))

    # create pin (from bottom to screw assembly)
    z_screw_asm = cfg.height - cfg.cell_size.z
    pin = (
        cq.Workplane("XY")
        .rect(cfg.pin_size.x, cfg.pin_size.y)
        .extrude(-cfg.pin_size.z - z_screw_asm)
        .translate((0, 0, z_screw_asm))
        .edges("|Y and <Z")
        .chamfer(cfg.pin_size.x * 0.49)
    )

    # create a screw base
    screw_base = (
        cq.Workplane("XY")
        .rect(cfg.screw_base_size.x, cfg.screw_base_size.y)
        .extrude(cfg.screw_base_size.z)
        .edges("|Z")
        .chamfer(cfg.screw_base_size.x * 0.1)
        .union(
            cq.Workplane("XY")
            .rect(cfg.screw_base_size.x * 0.5, cfg.screw_base_size.y * 1.4)
            .extrude(0.1)
        )
    )

    # Create a cross-type screw head
    r_screw = cfg.screw_diameter / 2
    h_screw = r_screw * 0.5
    screw_head = (
        cq.Workplane("XY")
        .circle(r_screw)
        .extrude(h_screw)
        .faces(">Z")
        .fillet(h_screw / 2)
        .faces("<Z")
        .fillet(h_screw / 5)
    )
    w_cross = r_screw * 0.2
    d_cross = h_screw * 0.4
    cross_slot1 = (
        cq.Workplane("XY")
        .workplane(offset=h_screw)
        .rect(w_cross, r_screw * 2)
        .extrude(-d_cross)
    )
    cross_slot2 = (
        cq.Workplane("XY")
        .workplane(offset=h_screw)
        .rect(r_screw, w_cross)
        .extrude(-d_cross)
    )
    screw_head = (
        screw_head.cut(cross_slot1).cut(cross_slot2).rotate((0, 0, 0), (0, 0, 1), 30)
    )

    # create a pin assembly (pin + base + screw) and their relative positions
    y_pad = cfg.width / 2 - cfg.pad_to_back
    pin_asm = cq.Workplane().add(pin.translate((0, y_pad, 0)))

    y_screw = -cfg.back_border / 2 - cfg.screw_offset
    screw_asm = (
        cq.Workplane()
        .add(screw_base)
        .union(screw_head.translate((0, 0, cfg.screw_base_size.z)))
    )
    pin_asm = pin_asm.union(
        screw_asm.translate((0, y_screw, cfg.height - cfg.cell_size.z))
    )

    # repeat pin assembly for connector
    pins = cq.Workplane().add(pin_asm)
    for i in range(1, n_pins + 1):
        pins = pins.union(pin_asm.translate(((i - 1) * cfg.pitch, 0, 0)))

    # add cover
    cover = None
    if cfg.cover_thickness:
        t = cfg.cover_thickness
        cover = (
            cq.Workplane("XY")
            .rect(length - cfg.cover_hinge * 2, cfg.cover_width)
            .extrude(t)
            .edges("|X and >Z")
            .fillet(t * 0.4999)
            .edges("|X and <Z and >Y")
            .chamfer(t * 0.2, t * 0.5)
            .edges("|X and <Z and <Y")
            .chamfer(t * 0.2, t * 0.5)
        )
        cover_in = (
            cq.Workplane("XY")
            .rect(length - cfg.side_border - t, cfg.cover_width - t)
            .extrude(t / 2)
        )
        cover = cover.cut(cover_in).translate(
            (x_center, (cfg.width - cfg.cover_width) / 2, cfg.height)
        )

        hinge = (
            cq.Workplane("YZ")
            .lineTo(t, 0)
            .lineTo(t, t / 2)
            .threePointArc((t / 2, t), (0.0, t / 2))
            .close()
            .extrude(cfg.cover_hinge)
            .faces(">X")
            .workplane()
            .center(t / 2, t / 2)
            .hole(t / 2)
            .translate(
                (-cfg.cell_size.x / 2 - cfg.side_border, cfg.width / 2 - t, cfg.height)
            )
        )
        hinge = hinge.union(
            hinge.translate((0.0, -cfg.width + cfg.fillet + t * 1.5, 0.0))
        )
        body = body.union(hinge).union(hinge.mirror("YZ", (x_center, 0, 0)))

    origin = (0.0, -y_pad, 0.0)
    pins = pins.translate(origin)
    body = body.translate(origin)
    if cover:
        cover = cover.translate(origin)

    return (body, pins, cover)
