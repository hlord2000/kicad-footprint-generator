#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This was originally derived from a cadquery script for generating PDIP models in X3D format
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
#
# Adapted by easyw for step and vrlm export
# See https://github.com/easyw/kicad-3d-models-in-freecad
#
## Requirements
## CadQuery 2.1 commit e00ac83f98354b9d55e6c57b9bb471cdf73d0e96 or newer
## https://github.com/CadQuery/cadquery
#
## To run the script just do: ./generator.py --output_dir [output_directory]
## e.g. ./generator.py --output_dir /tmp
#
# * These are cadquery tools to export                                       *
# * generated models in STEP & VRML format.                                  *
# *                                                                          *
# * cadquery script for generating QFP/SOIC/SSOP/TSSOP models in STEP AP214  *
# * Copyright (c) 2015                                                       *
# *     Maurice https://launchpad.net/~easyw                                 *
# * Copyright (c) 2022                                                       *
# *     Update 2022                                                          *
# *     jmwright (https://github.com/jmwright)                               *
# *     Work sponsored by KiCAD Services Corporation                         *
# *          (https://www.kipro-pcb.com/)                                    *
# * Copyright (c) 2024                                                       *
# *     Martin Sotirov <martin@libtec.org>                                   *
# *                                                                          *
# * All trademarks within this guide belong to their legitimate owners.      *
# *                                                                          *
# *   This program is free software; you can redistribute it and/or modify   *
# *   it under the terms of the GNU General Public License (GPL)             *
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


import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from .cq_model_relay_smd import make_case, make_marker, make_pins

__title__ = "main generator for Relay_SMD model generators"
__author__ = (
    "scripts: hyOzd, Maurice, jmwright, Martin Sotirov; models: see cq_model files;"
)
__Comment__ = """Generates Relay SMD models for KiCad libraries"""

___ver___ = "2.0.0"


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Relay_SMD")

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

    # Step through the selected models
    for model in models:
        if output_dir_prefix == None:
            print("ERROR: An output directory must be provided.")
            return
        else:
            # Construct the final output directory
            output_dir = os.path.join(
                output_dir_prefix, all_params[model]["destination_dir"]
            )

        # Safety check to make sure the selected model is valid
        if not model in all_params.keys():
            print("Parameters for %s don't exist in 'all_params', skipping." % model)
            continue

        # Used to wrap all the parts into an assembly
        component = cq.Assembly()

        has_marker = (
            "marker_pos" in all_params[model]
            and "marker_dim" in all_params[model]
            and "marker_color_key" in all_params[model]
        )

        body = make_case(all_params[model], has_marker)
        body = body.translate(all_params[model]["translation"])
        body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        body_color = shaderColors.named_colors[
            all_params[model]["body_color_key"]
        ].getDiffuseFloat()
        component.add(
            body,
            color=cq_color_correct.Color(body_color[0], body_color[1], body_color[2]),
        )

        if has_marker:
            marker = make_marker(all_params[model])
            marker = marker.translate(all_params[model]["translation"])
            marker = marker.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            marker_color = shaderColors.named_colors[
                all_params[model]["marker_color_key"]
            ].getDiffuseFloat()
            component.add(
                marker,
                color=cq_color_correct.Color(
                    marker_color[0], marker_color[1], marker_color[2]
                ),
            )

        pins = make_pins(all_params[model])
        pins = pins.translate(all_params[model]["translation"])
        pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        pin_color = shaderColors.named_colors[
            all_params[model]["pin_color_key"]
        ].getDiffuseFloat()
        component.add(
            pins, color=cq_color_correct.Color(pin_color[0], pin_color[1], pin_color[2])
        )

        model_name = all_params[model]["model_name"]

        # Export the assembly to STEP
        component.name = model_name
        export_tools.export_step(component, output_dir, model_name)

        # Export the assembly to VRML
        if enable_vrml:
            parts = [body, pins]
            colors = [
                all_params[model]["body_color_key"],
                all_params[model]["pin_color_key"],
            ]

            if has_marker:
                parts.append(marker)
                colors.append(all_params[model]["marker_color_key"])

            export_VRML(os.path.join(output_dir, model_name + ".wrl"), parts, colors)
