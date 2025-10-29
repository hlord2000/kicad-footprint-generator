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
# * cadquery script for generating DIP socket models in STEP AP214           *
# * Copyright (c) 2017                                                       *
#      Terje Io https://github.com/terjeio                                  *
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
__author__ = "scripts: maurice, hyOzd, Stefan, Terje; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from .cq_model_piano_switch import dip_switch_piano, dip_switch_piano_cts
from .cq_model_pin_switch import dip_switch, dip_switch_low_profile
from .cq_model_smd_switch import (
    dip_smd_switch,
    dip_smd_switch_lowprofile,
    dip_smd_switch_lowprofile_jpin,
)
from .cq_model_smd_switch_copal import (
    dip_switch_copal_CHS_A,
    dip_switch_copal_CHS_B,
    dip_switch_copal_CVS,
)
from .cq_model_smd_switch_kingtek import (
    dip_switch_kingtek_dshp04tj,
    dip_switch_kingtek_dshp06ts,
)
from .cq_model_smd_switch_omron import dip_switch_omron_a6h, dip_switch_omron_a6s
from .cq_model_socket_turned_pin import dip_socket_turned_pin


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("DIP_parts")

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
        pins_color = shaderColors.named_colors[
            all_params[model]["pin_color_key"]
        ].getDiffuseFloat()
        button_color = shaderColors.named_colors[
            all_params[model]["button_color_key"]
        ].getDiffuseFloat()
        mark_color = shaderColors.named_colors[
            all_params[model]["mark_color_key"]
        ].getDiffuseFloat()

        # Make a model for each type of DIP part
        for i in range(0, 15):
            # Choose the right module/method
            if i == 0:
                cqm = dip_switch_piano(all_params[model])
                offsets = (
                    cqm.pin_rows_distance / 2.0,
                    -(cqm.body_length / 2.0) + 1.40 + cqm.pin_width,
                    cqm.body_board_distance,
                )
            elif i == 1:
                cqm = dip_switch_piano_cts(all_params[model])
                offsets = (
                    cqm.pin_rows_distance / 2.0,
                    -(cqm.body_length / 2.0) + 1.85 + cqm.pin_width,
                    cqm.body_board_distance,
                )
            elif i == 2:
                cqm = dip_socket_turned_pin(all_params[model])
                offsets = cqm.offsets
            elif i == 3:
                cqm = dip_switch(all_params[model])
                offsets = (
                    cqm.pin_rows_distance / 2.0,
                    -(cqm.body_length / 2.0) + 1.80 + cqm.pin_width,
                    cqm.body_board_distance,
                )
            elif i == 4:
                cqm = dip_switch_low_profile(all_params[model])
                offsets = (
                    cqm.pin_rows_distance / 2.0,
                    -(cqm.body_length / 2.0) + 1.50 + cqm.pin_width,
                    cqm.body_board_distance,
                )
            elif i == 5:
                cqm = dip_smd_switch(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)
            elif i == 6:
                cqm = dip_smd_switch_lowprofile(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)
            elif i == 7:
                cqm = dip_smd_switch_lowprofile_jpin(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)
            elif i == 8:
                cqm = dip_switch_copal_CHS_A(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)
            elif i == 9:
                cqm = dip_switch_copal_CHS_B(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)
            elif i == 10:
                cqm = dip_switch_copal_CVS(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)
            elif i == 11:
                cqm = dip_switch_omron_a6h(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)
            elif i == 12:
                cqm = dip_switch_omron_a6s(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)
            elif i == 13:
                cqm = dip_switch_kingtek_dshp04tj(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)
            elif i == 14:
                cqm = dip_switch_kingtek_dshp06ts(all_params[model])
                offsets = (0, 0, cqm.pin_thickness / 2.0)

            # Make the parts of the model
            body = cqm.make_body()
            pins = cqm.make_pins()
            if i != 2:
                buttons = cqm.make_buttons()
                mark = cqm.make_pinmark(cqm.button_width + 0.2)

            # Get custom colors
            body_color = shaderColors.named_colors[cqm.color_keys[0]].getDiffuseFloat()

            # Put the parts in the correct position relative to the pads on the board
            if i != 2:
                rotation = 90
            else:
                rotation = -90
            body = body.rotate((0, 0, 0), (0, 0, 1), rotation).translate(offsets)
            pins = pins.rotate((0, 0, 0), (0, 0, 1), rotation).translate(offsets)
            if i != 2:
                buttons = buttons.rotate((0, 0, 0), (0, 0, 1), rotation).translate(
                    offsets
                )
                mark = mark.rotate((0, 0, 0), (0, 0, 1), rotation).translate(offsets)

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
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )
            if i != 2:
                component.add(
                    buttons,
                    color=cq_color_correct.Color(
                        button_color[0], button_color[1], button_color[2]
                    ),
                )
                component.add(
                    mark,
                    color=cq_color_correct.Color(
                        mark_color[0], mark_color[1], mark_color[2]
                    ),
                )

            # Assemble the filename
            file_name = cqm.makeModelName(model)

            # Export the assembly to STEP
            component.name = file_name
            export_tools.export_step(component, output_dir, file_name)

            # Export the assembly to VRML
            if enable_vrml:
                parts = [body, pins]
                colors = [
                    all_params[model]["body_color_key"],
                    all_params[model]["pin_color_key"],
                ]
                if i != 2:
                    parts.append(buttons)
                    parts.append(mark)
                    colors.append(all_params[model]["button_color_key"])
                    colors.append(all_params[model]["mark_color_key"])
                export_VRML(os.path.join(output_dir, file_name + ".wrl"), parts, colors)
