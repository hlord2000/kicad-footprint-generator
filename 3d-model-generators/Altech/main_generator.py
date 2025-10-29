#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is derived from a cadquery script for generating Converter_DCDC 3D
# format
#
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
# This is a
# Dimensions are from Microchips Packaging Specification document:
# DS00000049BY. Body drawing is the same as QFP generator#
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
# * CadQuery script for generating QFP/SOIC/SSOP/TSSOP models in STEP AP214  *
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

__title__ = "make Altech connector 3D models"
__author__ = "Stefan, based on Converter_DCDC script"
__Comment__ = (
    "make Altech connectors 3D models exported to STEP and VRML for Kicad StepUP script"
)

___ver___ = "1.3.4 18/06/2020"

import math
import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

body_color_key = "black body"  # Body color
body_color = shaderColors.named_colors[body_color_key].getDiffuseFloat()
pins_color_key = "metal grey pins"  # Pin color
pins_color = shaderColors.named_colors[pins_color_key].getDiffuseFloat()

dest_dir_prefix = "TerminalBlock_Altech.3dshapes"


def make_case_AK300(model, params, pinnumber):
    W = params[model]["W"]  # package width
    H = params[model]["H"]  # package height
    WD = params[model]["WD"]  # > Y distance form pin center to package edge
    A1 = params[model]["A1"]  # Body seperation height
    PE = params[model]["PE"]  # Distance from edge to pin
    PS = params[model]["PS"]  # Pin distance
    PD = params[model]["PD"]  # Pin diameter
    PL = params[model]["PL"]  # Pin diameter
    PF = params[model]["PF"]  # Pin form
    SW = params[model]["SW"]  # Blender width
    rotation = params[model]["rotation"]  # rotation if required

    lw = (2.0 * PE) + ((pinnumber - 1) * PS)

    #
    # Create a plygon of the shape and extrude it along the Y axis
    #
    pts = []
    pts.append((0.0, A1))
    #
    pts.append((0.0 - WD, A1))
    #
    pts.append((0.0 - WD, (A1 + H) - WD))
    #
    pts.append((0.0, A1 + H))
    #
    pts.append(((W - WD) - 0.5, A1 + H))
    #
    pts.append((W - WD, A1 + (H - 0.5)))
    #
    pts.append((W - WD, A1))
    #
    case = cq.Workplane("YZ").workplane(offset=0 - PE).polyline(pts).close().extrude(lw)
    #
    #
    A1A = A1 + 0.2
    bb = WD - 0.4
    SL = SW / 1.1  # Screw diameter

    px = 0.0
    pins = None

    for i in range(0, pinnumber):
        pp = (
            cq.Workplane("XY")
            .workplane(offset=A1A)
            .moveTo(px, 0.0 - (WD / 2.0))
            .rect(SW + 0.4, bb)
            .extrude(1.1 * H)
        )
        case = case.cut(pp)
        # Cut out screw header
        po = (
            cq.Workplane("XY")
            .workplane(offset=A1)
            .moveTo(0, 0)
            .circle(SL / 2.0, False)
            .extrude(W)
        )
        po = po.rotate((0, 0, 0), (1, 0, 0), 0 - 45.0)
        po = po.translate((px, 0.0, H / 2.0))
        case = case.cut(po)

        px = px + PS

    #    case = case.faces("<Y").edges(">X").fillet(0.1)
    case = case.faces("<X").fillet(0.2)
    case = case.faces(">X").fillet(0.2)
    case = case.faces(">Z").fillet(0.2)
    case = case.faces("<Y").edges(">Z").fillet(0.2)

    if rotation > 0.01:
        case = case.rotate((0, 0, 0), (0, 0, 1), rotation)

    return case


def make_pins_AK300(model, params, pinnumber):
    W = params[model]["W"]  # package width
    H = params[model]["H"]  # package height
    WD = params[model]["WD"]  # > Y distance form pin center to package edge
    A1 = params[model]["A1"]  # Body separation height
    PE = params[model]["PE"]  # Distance from edge to pin
    PS = params[model]["PS"]  # Pin distance
    PD = params[model]["PD"]  # Pin diameter
    PL = params[model]["PL"]  # Pin diameter
    PF = params[model]["PF"]  # Pin form
    SW = params[model]["SW"]  # Blender width
    rotation = params[model]["rotation"]  # rotation if required

    px = 0.0
    pins = None

    for i in range(0, pinnumber):
        if PF == "round":
            pint = (
                cq.Workplane("XY")
                .workplane(offset=A1)
                .moveTo(px, 0.0)
                .circle(PD[0] / 2.0, False)
                .extrude(0 - (A1 + PL))
            )
            pint = pins.faces("<Z").fillet(PD[0] / 2.2)
        else:
            pint = (
                cq.Workplane("XY")
                .workplane(offset=A1)
                .moveTo(px, 0.0)
                .rect(PD[0], PD[1])
                .extrude(0 - (A1 + PL))
            )
            if PD[0] < PD[1]:
                pint = pint.faces("<Z").fillet(PD[0] / 2.2)
            else:
                pint = pint.faces("<Z").fillet(PD[1] / 2.2)

        if i == 0:
            pins = pint
        else:
            pins = pins.union(pint, glue=True)

        A1A = A1 + 0.2
        bb0 = WD - 0.5
        bb0 = bb0 / math.cos(math.radians(45.0))
        SL = SW / 1.1  # Screw diameter

        bb = bb0
        pl = (
            cq.Workplane("XY")
            .workplane(offset=0.0)
            .moveTo(0.0, 0.0)
            .rect(SW, bb)
            .extrude(0.0 - (WD))
        )
        # Make hole
        bb1 = SW - (SW * 0.2)

        plu = (
            cq.Workplane("XY")
            .workplane(offset=0.0 + 0.1)
            .moveTo(0.0, 0.0 - ((bb / 2.0) - (bb1 / 2) - (SW * 0.2)))
            .rect(bb1, bb1)
            .extrude(0.0 - (1.1 * H + 0.2))
        )
        pl = pl.cut(plu)

        plu = (
            cq.Workplane("ZX")
            .workplane(offset=0.0 - (WD - SL))
            .moveTo(0.0 - (bb / 2.0), 0.0)
            .circle(SW / 2.5, False)
            .extrude(SL)
        )
        pl = pl.union(plu, clean=False, glue=True)

        # Add the screw head
        bba = (W - WD) / math.cos(math.radians(45.0))
        bba = bba * 0.85
        pl = (
            pl.faces(">Y")
            .workplane(centerOption="CenterOfBoundBox")
            .center(0, A1 - SL / 2.0)
            .circle(SL / 2.0)
            .extrude(SL + (SL / 4.0))
        )
        pl = (
            pl.faces(">Y")
            .workplane(centerOption="CenterOfBoundBox", invert=True)
            .rect(SL / 4.0, 10.0)
            .cutBlind(SL / 8.0)
        )
        pl = pl.faces(">Y").edges("%CIRCLE").fillet(SL / 8.0)

        # Rotate and move the pin into the correct position
        pl = pl.rotate((0, 0, 0), (1, 0, 0), 45.0)
        pl = pl.translate(
            (px, 0.0 - (WD / 2.0) + 0.1, A1 + ((H - WD) / 2.0) + WD - 0.3)
        )

        pins = pins.union(pl, glue=True)

        px = px + PS

    # Add any rotation requested via the settings
    if rotation > 0.01:
        pins = pins.rotate((0, 0, 0), (0, 0, 1), rotation)

    return pins


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Altech")

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

        body = make_case_AK300(model, all_params, all_params[model]["pin_number"])
        pins = make_pins_AK300(model, all_params, all_params[model]["pin_number"])

        # Wrap the component parts in an assembly so that we can attach colors
        component = cq.Assembly(name=model)
        component.add(
            body,
            color=cq_color_correct.Color(body_color[0], body_color[1], body_color[2]),
        )
        component.add(
            pins,
            color=cq_color_correct.Color(pins_color[0], pins_color[1], pins_color[2]),
        )

        # Export the assembly to STEP
        export_tools.export_step(component, output_dir, model)

        # Export the assembly to VRML
        if enable_vrml:
            export_VRML(
                os.path.join(output_dir, model + ".wrl"),
                [body, pins],
                ["black body", "metal grey pins"],
            )
