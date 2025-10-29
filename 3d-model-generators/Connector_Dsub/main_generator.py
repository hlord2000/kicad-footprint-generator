#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is derived from a cadquery script for generating PDIP models in X3D format
#
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
# This is a
# Dimensions are from Microchips Packaging Specification document:
# DS00000049BY. Body drawing is the same as QFP generator#
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
# *   Maurice https://launchpad.net/~easyw                                   *
# * Copyright (c) 2022                                                       *
# *     Update 2022                                                          *
# *     jmwright (https://github.com/jmwright)                               *
# *     Work sponsored by KiCAD Services Corporation                         *
# *          (https://www.kipro-pcb.com/)                                    *
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

__title__ = "main generator for capacitor tht model generators"
__author__ = "scripts: maurice and hyOzd; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import os
from math import radians, tan

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from .cq_dsub import *


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Connector_Dsub")

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
            print("Parameters for %s doesn't exist in 'all_params', skipping." % model)
            continue

        # Load the appropriate colors
        body_top_color = shaderColors.named_colors[
            all_params[model]["body_top_color_key"]
        ].getDiffuseFloat()
        body_color = shaderColors.named_colors[
            all_params[model]["body_color_key"]
        ].getDiffuseFloat()
        pins_color = shaderColors.named_colors[
            all_params[model]["pin_color_key"]
        ].getDiffuseFloat()
        npth_pin_color = shaderColors.named_colors[
            all_params[model]["npth_pin_color_key"]
        ].getDiffuseFloat()

        # Generate the requested genders of the connector
        for gender in all_params[model]["genders"]:
            # Add the current gender to the parameters
            all_params[model]["gender"] = gender

            # Generate the correct model
            cqm = cq_dsub()
            cqm.set_rotation(all_params[model])
            cqm.set_translate(all_params[model])
            body_top = cqm.make_top_DSUB(all_params[model])
            body = cqm.make_case_DSUB(all_params[model])
            pins = cqm.make_pin(all_params[model])
            npth_pins = cqm.make_npth_pins(all_params[model])

            # Used to wrap all the parts into an assembly
            component = cq.Assembly()

            # Add the parts to the assembly
            component.add(
                body_top,
                color=cq_color_correct.Color(
                    body_top_color[0], body_top_color[1], body_top_color[2]
                ),
            )
            component.add(
                body,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )
            component.add(
                npth_pins,
                color=cq_color_correct.Color(
                    npth_pin_color[0], npth_pin_color[1], npth_pin_color[2]
                ),
            )

            # Create the file name based on the rows and pins
            file_name = all_params[model]["model_name"].format(gender.capitalize())

            # Export the assembly to STEP
            component.name = file_name
            export_tools.export_step(component, output_dir, file_name)

            # Export the assembly to VRML
            if enable_vrml:
                # Dynamically assemble the list of parts and their corresponding colors
                parts = [body_top, body, pins]
                colors = [
                    all_params[model]["body_top_color_key"],
                    all_params[model]["body_color_key"],
                    all_params[model]["pin_color_key"],
                ]
                if npth_pins != None:
                    parts.append(npth_pins)
                    colors.append(all_params[model]["npth_pin_color_key"])
                export_VRML(os.path.join(output_dir, file_name + ".wrl"), parts, colors)
