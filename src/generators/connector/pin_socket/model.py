#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This was originaly derived from a cadquery script for generating PDIP models in X3D format
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
## the script will generate STEP and VRML parametric models
## to be used with kicad StepUp script
#
# * These are cadquery tools to export                                       *
# * generated models in STEP & VRML format.                                  *
# *                                                                          *
# * cadquery script for generating Molex models in STEP AP214                *
# *   Copyright (c) 2016                                                     *
# * Rene Poeschl https://github.com/poeschlr                                 *
# * Copyright (c) 2021                                                       *
# *     Update 2021                                                          *
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

import cadquery as cq

from _tools import cq_color_correct, export_tools, parameters, shaderColors

from .cq_socket_strips import angled_socket_strip, smd_socket_strip, socket_strip


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Connector_PinSocket")

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

        # Safety check to make sure the selected model is valid
        if not model in all_params.keys():
            print("Parameters for %s doesn't exist in 'all_params', skipping." % model)
            continue

        # Create a model for each number of pins
        for pin_num in range(
            all_params[model]["pins_min"], all_params[model]["pins_max"] + 1
        ):
            if all_params[model]["num_pin_rows"] == 1:
                all_params[model]["num_pins"] = pin_num
            else:
                all_params[model]["num_pins"] = pin_num * 2

            # Generate the current model
            if all_params[model]["model_class"].startswith("SMD"):
                cqm = smd_socket_strip(all_params[model])
            elif all_params[model]["model_class"].endswith("Vertical"):
                cqm = socket_strip(all_params[model])
            elif all_params[model]["model_class"].endswith("Horizontal"):
                cqm = angled_socket_strip(all_params[model])
            else:
                print("No match found for model_class.")

            # Used to wrap all the parts into an assembly
            component = cq.Assembly(name=model)

            # Make the translation correct
            translation = (0.0, 0.0)
            if all_params[model]["model_class"] == "THT-1x1.00mm_Vertical":
                translation = (
                    all_params[model]["pin_pitch"]
                    * (pin_num / 2.0 / all_params[model]["num_pin_rows"] - 0.5),
                    all_params[model]["pin_width"] / 1.5
                    + all_params[model]["pin_thickness"]
                    - 0.01,
                    0.0,
                )  # 1 = num_pin_rows, second pin_pitch = pin_rows_distance
            elif all_params[model]["model_class"] == "THT-1x1.27mm_Vertical":
                translation = (
                    all_params[model]["pin_pitch"]
                    * (pin_num / 2.0 / all_params[model]["num_pin_rows"] - 0.5),
                    all_params[model]["pin_width"] / 2.0
                    - all_params[model]["pin_thickness"]
                    - 0.05,
                    0.0,
                )  # 1 = num_pin_rows, second pin_pitch = pin_rows_distance
            elif all_params[model]["model_class"] == "THT-1x2.00mm_Vertical":
                translation = (
                    all_params[model]["pin_pitch"]
                    * (pin_num / 2.0 / all_params[model]["num_pin_rows"] - 0.5),
                    all_params[model]["pin_width"] / 2.0
                    - all_params[model]["pin_thickness"]
                    - 0.1,
                    0.0,
                )  # 1 = num_pin_rows, second pin_pitch = pin_rows_distance
            elif all_params[model]["model_class"] == "THT-1x2.54mm_Vertical":
                translation = (
                    all_params[model]["pin_pitch"]
                    * (pin_num / 2.0 / all_params[model]["num_pin_rows"] - 0.5),
                    all_params[model]["pin_width"] / 2.0
                    - all_params[model]["pin_thickness"]
                    - 0.1,
                    0.0,
                )  # 1 = num_pin_rows, second pin_pitch = pin_rows_distance
            elif all_params[model]["model_class"].startswith("THT-1") and all_params[
                model
            ]["model_class"].endswith("Horizontal"):
                translation = (
                    all_params[model]["pin_pitch"] * (pin_num - 1) / 2.0,
                    all_params[model]["pin_pitch"] / 2.0
                    - all_params[model]["pin_pitch"] / 2.0,
                    0.0,
                )  # all_params[model]['pin_pitch'] / 2.0)
            elif all_params[model]["model_class"].startswith("THT-2") and all_params[
                model
            ]["model_class"].endswith("Horizontal"):
                translation = (
                    all_params[model]["pin_pitch"] * (pin_num - 1) / 2.0,
                    all_params[model]["pin_pitch"] / 2.0
                    - all_params[model]["pin_width"] / 2.0
                    + all_params[model]["pin_thickness"]
                    + 0.1,
                    0.0,
                )  # all_params[model]['pin_pitch'] / 2.0)
            elif all_params[model]["model_class"].startswith("SMD"):
                translation = (0.0, 0.0, all_params[model]["pin_width"] / 2.0)
            else:
                translation = (
                    all_params[model]["pin_pitch"] * (pin_num - 1) / 2.0,
                    all_params[model]["pin_pitch"] / 2.0,
                    0.0,
                )

            # Generate the current strip
            body = cqm._make_body()
            pins = cqm._make_pins()
            body = body.translate(
                (-translation[0], translation[1], translation[2])
            ).rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            pins = pins.translate(
                (-translation[0], translation[1], translation[2])
            ).rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])

            # Make sure the pin name is zero padded
            if pin_num < 10:
                pin_num_str = "0" + str(pin_num)
            else:
                pin_num_str = str(pin_num)

            # Create the file name based on the rows and pins
            file_name = all_params[model]["model_name"].format(
                all_params[model]["num_pin_rows"], pin_num_str
            )

            parts: list[cq.Workplane] = [body, pins]
            color_names: list[str] = [
                all_params[model]["body_color_key"],
                all_params[model]["pins_color_key"],
            ]

            export_tools.export(
                root_output_dir=output_dir_prefix,
                lib_name=all_params[model]["destination_dir"],
                model_name=file_name,
                parts=parts,
                color_names=color_names,
                export_as_vrml=enable_vrml,
            )
