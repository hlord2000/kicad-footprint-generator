#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is derived from a cadquery script for generating PDIP models in X3D format
#
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
#
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
# * cadquery script for generating Molex models in STEP AP214                *
# * Copyright (c) 2016                                                       *
# *     Rene Poeschl https://github.com/poeschlr                             *
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

__title__ = "make molex connector 3D models exported to STEP and VRML"
__author__ = "scripts: maurice and hyOzd; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from .cq_models.conn_molex_502250 import generate_part as generate_part_502250
from .cq_models.conn_molex_kk_5273 import generate_part as generate_part_kk_5273
from .cq_models.conn_molex_kk_6410 import generate_part as generate_part_kk_6410
from .cq_models.conn_molex_kk_41791 import generate_part as generate_part_kk_41791
from .cq_models.conn_molex_kk_41792 import generate_part as generate_part_kk_41792
from .cq_models.conn_molex_picoblade_53261 import generate_part as generate_part_53261
from .cq_models.conn_molex_picoblade_53398 import generate_part as generate_part_53398
from .cq_models.conn_molex_picoflex_90325 import generate_part as generate_part_90325
from .cq_models.conn_molex_picoflex_90814 import generate_part as generate_part_90814
from .cq_models.conn_molex_SlimStack_54722 import generate_part as generate_part_54722
from .cq_models.conn_molex_SlimStack_55560 import generate_part as generate_part_55560


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("molex")

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
        body_color = shaderColors.named_colors[
            all_params[model]["body_color_key"]
        ].getDiffuseFloat()
        pin_color = shaderColors.named_colors[
            all_params[model]["pin_color_key"]
        ].getDiffuseFloat()
        latch_color = shaderColors.named_colors[
            all_params[model]["latch_color_key"]
        ].getDiffuseFloat()

        if all_params[model]["model_name"] == "502250":
            generate_part = generate_part_502250
        elif all_params[model]["model_name"] == "5273":
            generate_part = generate_part_kk_5273
        elif all_params[model]["model_name"] == "6410":
            generate_part = generate_part_kk_6410
        elif all_params[model]["model_name"] == "41791":
            generate_part = generate_part_kk_41791
        elif all_params[model]["model_name"] == "41792":
            generate_part = generate_part_kk_41792
        elif all_params[model]["model_name"] == "53261":
            generate_part = generate_part_53261
        elif all_params[model]["model_name"] == "53398":
            generate_part = generate_part_53398
        elif all_params[model]["model_name"] == "90325":
            generate_part = generate_part_90325
        elif all_params[model]["model_name"] == "90814":
            generate_part = generate_part_90814
        elif all_params[model]["model_name"] == "54722":
            generate_part = generate_part_54722
        elif all_params[model]["model_name"] == "55560":
            generate_part = generate_part_55560
        else:
            print(
                "Could not find a match for model name {}.".format(
                    all_params[model]["model_name"]
                )
            )
            continue

        # Generate a variant for each pin count
        for pin_count in all_params[model]["pin_range"]:
            # Make the parts of the model
            (pins, body, latch) = generate_part(all_params[model], pin_count)
            # body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]['rotation'])
            # pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]['rotation'])

            # Used to wrap all the parts into an assembly
            component = cq.Assembly()

            # Add the parts to the assembly
            component.add(
                body,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(pin_color[0], pin_color[1], pin_color[2]),
            )
            component.add(
                latch,
                color=cq_color_correct.Color(
                    latch_color[0], latch_color[1], latch_color[2]
                ),
            )

            # Assemble the filename
            padded_pin_count = (
                "0" + str(pin_count) if pin_count < 10 else str(pin_count)
            )
            file_name = all_params[model]["fp_name_format_string"].format(
                man=all_params[model]["manufacturer"],
                padpincount="00" + padded_pin_count,
                halfpadpincount=(
                    "0" + str(int(pin_count / 2))
                    if (pin_count / 2) < 10
                    else str(int(pin_count / 2))
                ),
                pincount=padded_pin_count,
                num_rows=all_params[model]["number_of_rows"],
                pitch=(
                    str(all_params[model]["pitch"]) + "0"
                    if all_params[model]["model_name"].startswith("KK_396")
                    else str(all_params[model]["pitch"])
                ),
                orientation=all_params[model]["orientation"],
            )

            # Export the assembly to STEP
            component.name = file_name
            export_tools.export_step(component, output_dir, file_name)

            # Export the assembly to VRML
            if enable_vrml:
                # Add parts that are always included
                parts = [body, pins]
                colors = [
                    all_params[model]["body_color_key"],
                    all_params[model]["pin_color_key"],
                ]
                # Add optional insert/latch part
                if latch != None and not isinstance(latch.val(), cq.Vector):
                    parts.append(latch)
                    colors.append(all_params[model]["latch_color_key"])
                # Export the parts to VRML
                export_VRML(os.path.join(output_dir, file_name + ".wrl"), parts, colors)
