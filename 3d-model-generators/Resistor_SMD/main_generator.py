# -*- coding: utf8 -*-
#!/usr/bin/python
#
# The original, CadQuery 1.x based script was derived from a CadQuery
# script for generating PDIP models in X3D format.
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
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
# * Copyright (c) 2015                                                       *
# *     Maurice https://launchpad.net/~easyw                                 *
# * Copyright (c) 2021                                                       *
# *     Update 2021                                                          *
# *     jmwright (https://github.com/jmwright)                               *
# *     Work sponsored by KiCAD Services Corporation                         *
#           (https://www.kipro-pcb.com/)                                    *
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

__title__ = "Make chip Resistors 3D models"
__author__ = "maurice, jmwright"
__Comment__ = "Make chip Resistors 3D models exported to STEP and VRML"

___ver___ = "2.0.0"

import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

body_color_key = "white body"
body_color = shaderColors.named_colors[body_color_key].getDiffuseFloat()
pins_color_key = "metal grey pins"
pins_color = shaderColors.named_colors[pins_color_key].getDiffuseFloat()
top_color_key = "resistor black body"
top_color = shaderColors.named_colors[top_color_key].getDiffuseFloat()

dest_dir_prefix = "Resistor_SMD.3dshapes"

"""
Generates the CadQuery model that will be exported.
"""


def make_chip(model, all_params):
    # dimensions for chip capacitors
    length = all_params[model]["length"]  # package length
    width = all_params[model]["width"]  # package width
    height = all_params[model]["height"]  # package height

    pin_band = all_params[model]["pin_band"]  # pin band
    pin_thickness = all_params[model]["pin_thickness"]  # pin thickness
    if pin_thickness == "auto":
        pin_thickness = height / 10.0

    edge_fillet = all_params[model]["edge_fillet"]  # fillet of edges
    if edge_fillet == "auto":
        edge_fillet = pin_thickness

    # Create a 3D box based on the dimension variables above and fillet it
    case = (
        cq.Workplane("XY")
        .workplane(offset=pin_thickness)
        .box(
            length - 2 * pin_thickness,
            width,
            height - 2 * pin_thickness,
            centered=(True, True, False),
        )
    )
    top = (
        cq.Workplane("XY")
        .workplane(offset=height - pin_thickness)
        .box(length - 2 * pin_band, width, pin_thickness, centered=(True, True, False))
    )

    # Create a 3D box based on the dimension variables above and fillet it
    pin1 = cq.Workplane("XY").box(pin_band, width, height)
    pin1 = pin1.edges("|Y").fillet(edge_fillet)
    pin1 = pin1.translate((-length / 2 + pin_band / 2, 0, height / 2)).rotate(
        (0, 0, 0), (0, 0, 1), 0
    )
    pin2 = cq.Workplane("XY").box(pin_band, width, height)
    pin2 = pin2.edges("|Y").fillet(edge_fillet)
    pin2 = pin2.translate((length / 2 - pin_band / 2, 0, height / 2)).rotate(
        (0, 0, 0), (0, 0, 1), 0
    )
    pins = pin1.union(pin2)
    # body_copy.ShapeColor=result.ShapeColor

    # extract case from pins
    # case = case.cut(pins)
    pins = pins.cut(case)

    return (case, top, pins)


def make_models(model_to_build=None, output_dir=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Resistor_SMD")

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

    if output_dir == None:
        print("ERROR: An output directory must be provided.")
        return
    else:
        # Construct the final output directory
        output_dir = os.path.join(output_dir, dest_dir_prefix)

    # Step through the selected models
    for model in models:

        # Safety check to make sure the selected model is valid
        if not model in all_params.keys():
            print("Parameters for %s doesn't exist in 'all_params', skipping." % model)
            continue

        body, top, pins = make_chip(model, all_params)

        # Wrap the component parts in an assembly so that we can attach colors
        component = cq.Assembly()
        component.add(
            body,
            color=cq_color_correct.Color(body_color[0], body_color[1], body_color[2]),
        )
        component.add(
            pins,
            color=cq_color_correct.Color(pins_color[0], pins_color[1], pins_color[2]),
        )
        component.add(
            top, color=cq_color_correct.Color(top_color[0], top_color[1], top_color[2])
        )

        # Export the assembly to STEP
        component.name = model
        export_tools.export_step(component, output_dir, model)

        # Export the assembly to VRML
        if enable_vrml:
            export_VRML(
                os.path.join(output_dir, model + ".wrl"),
                [body, pins, top],
                ["white body", "metal grey pins", "resistor black body"],
            )
