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

import os
from math import radians, tan
from typing import Any

import cadquery as cq

from _tools import cq_color_correct, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

dest_dir_prefix = "Package_BGA.3dshapes"

FUSED_AND_COMPRESSED = False


def make_plg(wp, rw, rh, cv1, cv):
    """
    Creates a rectangle with chamfered corners.
    wp: workplane object
    rw: rectangle width
    rh: rectangle height
    cv1: chamfer value for 1st corner (lower left)
    cv: chamfer value for other corners
    """
    points = [
        (-rw / 2.0, -rh / 2.0 + cv1),
        (-rw / 2.0, rh / 2.0 - cv),
        (-rw / 2.0 + cv, rh / 2.0),
        (rw / 2.0 - cv, rh / 2.0),
        (rw / 2.0, rh / 2.0 - cv),
        (rw / 2.0, -rh / 2.0 + cv),
        (rw / 2.0 - cv, -rh / 2.0),
        (-rw / 2.0 + cv1, -rh / 2.0),  # ,
    ]
    sp = points.pop()
    wp = wp.moveTo(sp[0], sp[1])
    wp = wp.polyline(points, includeCurrent=True).close().wire()

    return wp


def make_case(
    params: dict[str, Any],
) -> tuple[cq.Workplane | None, cq.Workplane, Any, cq.Workplane]:

    ef = params.get("ef", 0.0)
    cff = params.get("cff")
    cf = params.get("cf")
    D = params["D"]
    E = params["E"]
    D1 = params.get("D1")
    E1 = params.get("E1")
    A1 = params["A1"]
    A2 = params.get("A2")
    A = params["A"]
    molded = params.get("molded")
    b = params["b"]
    e = params["e"]
    ex = params.get("ex")
    sp = params.get("sp", 0.0)
    npx = params["npx"]
    npy = params["npy"]
    rot = params["rotation"]

    if ex == None:
        ex = e
    if ex == 0:
        ex = e

    if params.get("excluded_pins") is not None:
        excluded_pins = tuple(
            ep if isinstance(ep, str) else str(int(ep))
            for ep in params["excluded_pins"]
        )
    else:
        excluded_pins = ()  ##no pin excluded

    sphere_r = b / 2 * (1.05)  # added extra 0.5% diameter for fusion
    s_center = (0, 0, 0)
    sphere = cq.Workplane("XY", s_center).sphere(sphere_r)
    bpin = sphere.translate((0, 0, b / 2 - sp))

    pins = []
    # create top, bottom side pins
    pincounter = 1
    first_pos_x = (npx - 1) * e / 2
    for j in range(npy):
        for i in range(npx):
            if "internals" in excluded_pins:
                if str(int(pincounter)) not in excluded_pins:
                    if j == 0 or j == npy - 1 or i == 0 or i == npx - 1:
                        pin = bpin.translate(
                            (first_pos_x - i * e, (npy * ex / 2 - ex / 2) - j * ex, 0)
                        ).rotate((0, 0, 0), (0, 0, 1), 180)
                        pins.append(pin)
            elif str(int(pincounter)) not in excluded_pins:
                pin = bpin.translate(
                    (first_pos_x - i * e, (npy * ex / 2 - ex / 2) - j * ex, 0)
                ).rotate((0, 0, 0), (0, 0, 1), 180)
                pins.append(pin)
            pincounter += 1

    # merge all pins to a single object
    merged_pins = pins[0]
    for p in pins[1:]:
        merged_pins = merged_pins.union(p)
    pins = merged_pins

    # first pin indicator is created with a cylindrical pocket
    marker_depth = A / 4
    marker_diameter = max(D, E) / 10.0
    if min(D, E) < 5 * marker_diameter:
        marker_edge_clearance = marker_diameter / 4.0
    else:
        marker_edge_clearance = marker_diameter / 2.0
    if molded is not None:
        the = 24
        if D1 is None:
            D1 = D * (1 - 0.065)
            E1 = E * (1 - 0.065)
        D1_t = D1 - 2 * tan(radians(the)) * (A - A1 - A2)
        E1_t = E1 - 2 * tan(radians(the)) * (A - A1 - A2)
        # draw the case
        cw = D - 2 * A1
        cl = E - 2 * A1
        case_bot = cq.Workplane("XY").workplane(offset=0)
        case_bot = make_plg(case_bot, cw, cl, cff, cf)
        case_bot = case_bot.extrude(A2 - 0.01)
        case_bot = case_bot.translate((0, 0, A1))

        case = cq.Workplane("XY").workplane(offset=A1)
        case = make_plg(case, D1, E1, 3 * cf, 3 * cf)
        case = case.extrude(0.01)
        case = case.faces(">Z").workplane()
        case = make_plg(case, D1, E1, 3 * cf, 3 * cf).workplane(offset=A - A2 - A1)
        case = make_plg(case, D1_t, E1_t, 3 * cf, 3 * cf).loft(ruled=True)
        # fillet the bottom vertical edges
        if ef != 0:
            case_bot = case_bot.edges("|Z").fillet(ef)
        # fillet top and side faces of the top molded part
        if ef != 0:
            BS = cq.selectors.BoxSelector
            case = case.edges(
                BS((-D1 / 2, -E1 / 2, A2 + 0.001), (D1 / 2, E1 / 2, A + 0.001))
            ).fillet(ef)
        case = case.translate((0, 0, A2 - 0.01))
        pinmark = (
            cq.Workplane(
                "XZ",
                (
                    -D / 2 + marker_edge_clearance + marker_diameter / 2,
                    -E / 2 + marker_edge_clearance + marker_diameter / 2,
                    A,
                ),
            )
            .rect(marker_diameter / 2, -marker_depth, False)
            .revolve()
        )
        pinmark = pinmark.translate(
            (
                (D - D1_t) / 2 + marker_edge_clearance + cff,
                (E - E1_t) / 2 + marker_edge_clearance + cff,
                -sp,
            )
        )
        case = case.cut(pinmark)
        # extract pins from case
        if FUSED_AND_COMPRESSED:
            case_bot = case_bot.cut(pins)
        ##

    else:
        A2 = A - A1  # body height
        case = cq.Workplane("XY").box(D, E, A2)  # NO margin, pins don't emerge
        if ef != 0:
            case.edges("|X").fillet(ef)
            case.edges("|Z").fillet(ef)
        # translate the object
        case = case.translate((0, 0, A2 / 2 + A1 - sp)).rotate((0, 0, 0), (0, 0, 1), 0)

        pinmark = (
            cq.Workplane(
                "XZ",
                (
                    -D / 2 + marker_edge_clearance + marker_diameter / 2,
                    -E / 2 + marker_edge_clearance + marker_diameter / 2,
                    marker_depth,
                ),
            )
            .rect(marker_diameter / 2, -2 * marker_depth, False)
            .revolve()
            .translate((0, 0, A2 + A1 - sp - marker_depth + 0.002))
        )
        case = case.cut(pinmark)
        # extract pins from case
        if FUSED_AND_COMPRESSED:
            case = case.cut(pins)
        case_bot = None

    # See if rotation has been requested
    if params["rotation"] != 0:
        case = case.rotate((0, 0, 0), (0, 0, 1), rot)
        pins = pins.rotate((0, 0, 0), (0, 0, 1), rot)
        pinmark = pinmark.rotate((0, 0, 0), (0, 0, 1), rot)

    return (case_bot, case, pins, pinmark)


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("BGA_packages")

    if all_params == None:
        print("ERROR: Model parameters must be provided.")
        return

    # Handle the case where no model has been passed
    if model_to_build is None:
        print("No variant name is given! building: {0}".format(model_to_build))

        model_to_build = all_params.keys()[0]

    # Handle being able to generate all models or just one
    if model_to_build == "all":
        models = all_params
    else:
        models = {model_to_build: all_params[model_to_build]}

    if output_dir_prefix == None:
        print("ERROR: An output directory must be provided.")
        return
    else:
        # Construct the final output directory
        output_dir = os.path.join(output_dir_prefix, dest_dir_prefix)

    # Step through the selected models
    for model in models:
        # Safety check to make sure the selected model is valid
        if not model in all_params.keys():
            print("Parameters for %s doesn't exist in 'all_params', skipping." % model)
            continue

        # Load the appropriate colors
        body_bot_color = shaderColors.named_colors["dark green body"].getDiffuseFloat()
        body_color = shaderColors.named_colors["black body"].getDiffuseFloat()
        pins_color = shaderColors.named_colors["metal grey pins"].getDiffuseFloat()
        marking_color = shaderColors.named_colors["light brown label"].getDiffuseFloat()

        # Generate the current model
        case_bot, case, pins, pinmark = make_case(all_params[model])

        # Wrap the component parts in an assembly so that we can attach colors
        component = cq.Assembly(name=model)
        if case_bot != None:
            component.add(
                case_bot,
                color=cq_color_correct.Color(
                    body_bot_color[0], body_bot_color[1], body_bot_color[2]
                ),
            )
        component.add(
            case,
            color=cq_color_correct.Color(body_color[0], body_color[1], body_color[2]),
        )
        component.add(
            pins,
            color=cq_color_correct.Color(pins_color[0], pins_color[1], pins_color[2]),
        )
        component.add(
            pinmark,
            color=cq_color_correct.Color(
                marking_color[0], marking_color[1], marking_color[2]
            ),
        )

        part_output_dir = output_dir
        if (
            "library_name" in all_params[model]
            and all_params[model]["library_name"] is not None
        ):
            part_output_dir = os.path.join(
                output_dir_prefix, all_params[model]["library_name"] + ".3dshapes"
            )

        # Create the output directory if it does not exist
        if not os.path.exists(part_output_dir):
            os.makedirs(part_output_dir)

        if FUSED_AND_COMPRESSED:
            # Export the assembly to STEP
            component.export(
                os.path.join(part_output_dir, model + ".step"),
                cq.exporters.ExportTypes.STEP,
                mode=cq.exporters.assembly.ExportModes.FUSED,
                write_pcurves=False,
            )

            # Check for a proper union
            export_tools.check_step_export_union(component, part_output_dir, model)

            # Do STEP post-processing
            export_tools.postprocess_step(component, part_output_dir, model)

            # Export the assembly to VRML
            if enable_vrml:
                parts = [case, pins, pinmark]
                colors = ["black body", "metal grey pins", "light brown label"]
                if case_bot != None:
                    parts.append(case_bot)
                    colors.append("dark green body")
                export_VRML(
                    os.path.join(part_output_dir, model + ".wrl"), parts, colors
                )

            # Update the license
            from _tools import add_license

            add_license.addLicenseToStep(
                part_output_dir,
                model + ".step",
                add_license.LIST_int_license,
                add_license.STR_int_licAuthor,
                add_license.STR_int_licEmail,
                add_license.STR_int_licOrgSys,
                add_license.STR_int_licPreProc,
            )
        else:
            # Export the assembly to STEP
            component.export(
                os.path.join(part_output_dir, model + ".step"),
                cq.exporters.ExportTypes.STEP,
                mode=cq.exporters.assembly.ExportModes.DEFAULT,
                write_pcurves=False,
            )
