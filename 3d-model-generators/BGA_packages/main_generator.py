#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is derived from a cadquery script for generating QFP models in
# X3D format.
#
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
#
# Dimensions are from Jedec MS-026D document.
#
# Thanks to Frank Severinsen (Shack) for including the orignal vrml
# materials.
#
## Requirements
## CadQuery 2.1 commit e00ac83f98354b9d55e6c57b9bb471cdf73d0e96 or newer
## https://github.com/CadQuery/cadquery
#
## To run the script just do: ./generator.py --output_dir [output_directory]
## e.g. ./generator.py --output_dir /tmp
#
## These are CadQuery scripts that will generate STEP and VRML parametric
## models.
#
# *                                                                          *
# * cadquery script for generating QFP/SOIC/SSOP/TSSOP models in STEP AP214  *
# *   Copyright (c) 2015                                                     *
# * Maurice https://launchpad.net/~easyw                                     *
# * Copyright (c) 2021                                                       *
# *     Update 2021                                                          *
# *     jmwright (https://github.com/jmwright)                               *
# *     Work sponsored by KiCAD Services Corporation                         *
# *          (https://www.kipro-pcb.com/)                                    *
# *                                                                          *
# * All trademarks within this guide belong to their legitimate owners.      *
# *                                                                          *
# *   This program is free software; you can redistribute it and/or modify   *
# *   it under the terms of the GNU Lesser General Public License (LGPL)     *
# *   as published by the Free Software Foundation; either version 2 of      *
# *   the License, or (at your option) any later version.                    *
# *   for detail see the LICENCE text file.                                  *
# *                                                                          *
# *   This program is distributed in the hope that it will be useful,        *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of         *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          *
# *   GNU Library General Public License for more details.                   *
# *                                                                          *
# *   You should have received a copy of the GNU Library General Public      *
# *   License along with this program; if not, write to the Free Software    *
# *   Foundation, Inc.,                                                      *
# *   51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA           *
# *                                                                          *
# ****************************************************************************

__title__ = "make BGA ICs 3D models"
__author__ = "maurice, hyOzd, jmwright"
__Comment__ = "make BGA ICs 3D models exported to STEP and VRML"

___ver___ = "2.0.0"

import glob
import os
from math import radians, tan
from pathlib import Path
from typing import Any

import cadquery as cq
import yaml

from _tools import (  # type:ignore
    cq_color_correct,
    export_tools,
    shaderColors,
)
from exportVRML.export_part_to_VRML import export_VRML  # type: ignore

from kilibs.util import dict_tools  # type: ignore
from src.generators.BGA.bga_configuration import (  # type: ignore
    BGAConfiguration,
    load_config,
)

dest_dir_prefix = "Package_BGA.3dshapes"

FUSED_AND_COMPRESSED = False


def make_plg(
    wp: cq.Workplane, rw: float, rh: float, cv1: float, cv: float
) -> cq.Workplane:
    """
    Creates a rectangle with chamfered corners.
    wp: workplane object
    rw: rectangle width (x)
    rh: rectangle height (y)
    cv1: chamfer value for 1st corner (top left)
    cv: chamfer value for other corners
    """
    x = rw / 2.0
    y = rh / 2.0
    points = [
        (-x, y - cv1),
        (-x + cv1, y),
        (x - cv, y),
        (x, y - cv),
        (x, -y + cv),
        (x - cv, -y),
        (-x + cv, -y),
        (-x, -y + cv),
        (-x, y - cv1),
    ]
    return wp.polyline(points, includeCurrent=False).wire()


def make_case(
    bga_config: BGAConfiguration,
) -> tuple[cq.Workplane | None, cq.Workplane, Any, cq.Workplane]:

    ef = bga_config.body_fillet
    cff = bga_config.first_corner_chamfer
    cf = bga_config.corner_chamfer
    d = bga_config.body_size_y
    e = bga_config.body_size_x
    d1 = bga_config.mold_size_y
    e1 = bga_config.mold_size_x
    a1 = bga_config.body_pcb_gap
    a2 = bga_config.mold_size_z_bottom
    a = bga_config.overall_height
    sp = bga_config.seating_plane
    b = bga_config.ball_diameter
    if b is None:
        raise KeyError("Cannot generate 3D model without a `ball_diameter` parameter.")

    sphere_r = b / 2 * (1.05)  # added extra 0.5% diameter for fusion
    s_center = (0, 0, 0)
    sphere = cq.Workplane("XY", s_center).sphere(sphere_r)
    bpin = sphere.translate((0, 0, b / 2 - sp))

    pin_positions: list[cq.Location] = []
    for layout_data in bga_config.layout_data_list:
        for pad_data in layout_data.pad_data_list:
            pos = pad_data.position
            pin_positions.append(cq.Location(cq.Vector(pos.x, pos.y)))

    # Create all pins in a single, efficient operation
    merged_pins = (
        cq.Workplane("XY")
        .pushPoints(pin_positions)
        .each(lambda loc: bpin.val().located(loc), combine="a")  # type: ignore
    )

    # first pin indicator is created with a cylindrical pocket
    marker_depth = 0.05  # fixed 50 um for all markers
    marker_diameter = max(d, e) / 10.0
    if min(d, e) < 5 * marker_diameter:
        marker_edge_clearance = marker_diameter / 4.0
    else:
        marker_edge_clearance = marker_diameter / 2.0
    if bga_config.molded:
        the = 24
        d1_t = d1 - 2 * tan(radians(the)) * (a - a1 - a2)
        e1_t = e1 - 2 * tan(radians(the)) * (a - a1 - a2)
        # draw the case
        cw = e - 2 * a1
        ch = d - 2 * a1
        case_bot = cq.Workplane("XY").workplane(offset=0)
        case_bot = make_plg(case_bot, cw, ch, cff, cf)
        case_bot = case_bot.extrude(a2 - 0.01)
        case_bot = case_bot.translate((0, 0, a1))

        case = cq.Workplane("XY").workplane(offset=a1)
        case = make_plg(case, e1, d1, 3 * cf, 3 * cf)
        case = case.extrude(0.01)
        case = case.faces(">Z").workplane()
        case = make_plg(case, e1, d1, 3 * cf, 3 * cf).workplane(offset=a - a2 - a1)
        case = make_plg(case, e1_t, d1_t, 3 * cf, 3 * cf).loft(ruled=True)
        # fillet the bottom vertical edges
        if ef != 0:
            case_bot = case_bot.edges("|Z").fillet(ef)
        # fillet top and side faces of the top molded part
        if ef != 0:
            BS = cq.selectors.BoxSelector
            case = case.edges(
                BS((-e1 / 2, -d1 / 2, a2 + 0.001), (e1 / 2, d1 / 2, a + 0.001))
            ).fillet(ef)
        case = case.translate((0, 0, a2 - 0.01))
        pinmark = (
            cq.Workplane(
                "XZ",
                (
                    -e / 2 + marker_edge_clearance + marker_diameter / 2,
                    d / 2 - marker_edge_clearance - marker_diameter / 2,
                    a,
                ),
            )
            .rect(marker_diameter / 2, -marker_depth, False)
            .revolve()
        )
        pinmark = pinmark.translate(
            (
                (e - e1_t) / 2 + marker_edge_clearance + cff,
                (d - d1_t) / 2 - marker_edge_clearance - cff,
                -sp,
            )
        )

    else:
        a2 = a - a1  # body height
        case = cq.Workplane("XY").box(e, d, a2)  # NO margin, pins don't emerge
        if ef != 0:
            case.edges("|X").fillet(ef)
            case.edges("|Z").fillet(ef)
        # translate the object
        case = case.translate((0, 0, a2 / 2 + a1 - sp)).rotate((0, 0, 0), (0, 0, 1), 0)
        pinmark = (
            cq.Workplane(
                "XZ",
                (
                    -e / 2 + marker_edge_clearance + marker_diameter / 2,
                    d / 2 - marker_edge_clearance - marker_diameter / 2,
                    marker_depth,
                ),
            )
            .rect(marker_diameter / 2, -2 * marker_depth, False)
            .revolve()
            .translate((0, 0, a2 + a1 - sp - marker_depth + 0.002))
        )
        case_bot = None

    if bga_config.marker is not None:
        pad_position_found = False
        for layout_data in bga_config.layout_data_list:
            for pad_data in layout_data.pad_data_list:
                if pad_data.name == bga_config.marker:
                    pad_position_found = True
                    pos = pad_data.position
                    pinmark = (
                        cq.Workplane("XY", (pos.x, -pos.y, a))
                        .circle(marker_diameter / 2, False)
                        .extrude(-marker_depth)
                    )
                    break
            if pad_position_found:
                break
        if not pad_position_found:
            raise ValueError(
                f"Mark is '{bga_config.marker}', however no such pin was found."
            )
    case = case.cut(pinmark)

    return (case_bot, case, merged_pins, pinmark)


def make_models(
    model_to_build: str | None = None,
    output_dir_prefix: str | None = None,
    enable_vrml: bool = True,
) -> None:
    """
    Main entry point into this generator.
    """

    gullwing_path = os.path.dirname(os.path.realpath(__file__))
    all_yaml_files = glob.glob(f"{gullwing_path}/../../data/BGA/*.yaml")

    if not all_yaml_files:
        print("No YAML files found to process.")
        return

    config = load_config("../scripts/Packages/package_config_KLCv3.yaml")

    bga_configs: list[BGAConfiguration] = []
    for yaml_file in all_yaml_files:
        file_path = Path(yaml_file)
        with open(file_path, "r") as stream:
            yaml_dict = yaml.safe_load(stream)
            dict_tools.dictInherit(yaml_dict)
            header = yaml_dict.get("FileHeader")
            for key, value in yaml_dict.items():
                if key != "FileHeader":
                    if (
                        model_to_build == key
                        or model_to_build == "all"
                        or model_to_build == None
                    ):
                        bgac = BGAConfiguration(key, value, header, config)
                        if bgac.has_3d_data:
                            bga_configs.append(bgac)

    if output_dir_prefix == None:
        print("ERROR: An output directory must be provided.")
        return
    else:
        # Construct the final output directory
        output_dir = os.path.join(output_dir_prefix, dest_dir_prefix)

    # Load the colors
    rgb_body_b = shaderColors.named_colors["dark green body"].getDiffuseFloat()
    rgb_body = shaderColors.named_colors["black body"].getDiffuseFloat()
    rbg_pin = shaderColors.named_colors["metal grey pins"].getDiffuseFloat()
    rgb_mark = shaderColors.named_colors["light brown label"].getDiffuseFloat()

    rgb_body_b = cq_color_correct.Color(rgb_body_b[0], rgb_body_b[1], rgb_body_b[2])
    body_color = cq_color_correct.Color(rgb_body[0], rgb_body[1], rgb_body[2])
    pin_color = cq_color_correct.Color(rbg_pin[0], rbg_pin[1], rbg_pin[2])
    mark_color = cq_color_correct.Color(rgb_mark[0], rgb_mark[1], rgb_mark[2])

    # Step through the selected models
    for bga_config in bga_configs:
        # Generate the current model
        case_bot, case, pins, pinmark = make_case(bga_config)

        # Wrap the component parts in an assembly so that we can attach colors
        component = cq.Assembly(name=bga_config.name)
        if case_bot != None:
            component.add(case_bot, color=rgb_body_b)  # type: ignore
        component.add(case, color=body_color)  # type: ignore
        component.add(pins, color=pin_color)  # type: ignore
        component.add(pinmark, color=mark_color)  # type: ignore

        part_output_dir = output_dir
        part_output_dir = os.path.join(
            output_dir_prefix, bga_config.lib_name + ".3dshapes"
        )

        # Create the output directory if it does not exist
        if not os.path.exists(part_output_dir):
            os.makedirs(part_output_dir)

        if FUSED_AND_COMPRESSED:
            # Export the assembly to STEP
            component.export(  # type: ignore
                os.path.join(part_output_dir, bga_config.name + ".step"),
                cq.exporters.ExportTypes.STEP,
                mode=cq.exporters.assembly.ExportModes.FUSED,  # type: ignore
                write_pcurves=False,
            )

            # Check for a proper union
            export_tools.check_step_export_union(
                component, part_output_dir, bga_config.name
            )

            # Do STEP post-processing
            export_tools.postprocess_step(component, part_output_dir, bga_config.name)

            # Export the assembly to VRML
            if enable_vrml:
                parts = [case, pins, pinmark]
                colors = ["black body", "metal grey pins", "light brown label"]
                if case_bot != None:
                    parts.append(case_bot)
                    colors.append("dark green body")
                export_VRML(
                    os.path.join(part_output_dir, bga_config.name + ".wrl"),
                    parts,
                    colors,
                )

            # Update the license
            from _tools import add_license  # type: ignore

            add_license.addLicenseToStep(  # type: ignore
                part_output_dir,
                bga_config.name + ".step",
                add_license.LIST_int_license,
                add_license.STR_int_licAuthor,
                add_license.STR_int_licEmail,
                add_license.STR_int_licOrgSys,
                add_license.STR_int_licPreProc,
            )
        else:
            # Export the assembly to STEP
            component.export(  # type: ignore
                os.path.join(part_output_dir, bga_config.name + ".step"),
                cq.exporters.ExportTypes.STEP,
                mode=cq.exporters.assembly.ExportModes.DEFAULT,  # type: ignore
                write_pcurves=False,
            )
