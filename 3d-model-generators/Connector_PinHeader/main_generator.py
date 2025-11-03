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
# *   Copyright (c) 2015                                                     *
# *     Maurice https://launchpad.net/~easyw                                 *
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
__author__ = "scripts: maurice and Shack; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"


import cadquery as cq

from _tools import export_tools, parameters

from .pinheader import (
    make_Horizontal_THT_base,
    make_Horizontal_THT_pins,
    make_Vertical_SMD_base,
    make_Vertical_SMD_pins,
    make_Vertical_THT_base,
    make_Vertical_THT_pins,
)


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Connector_PinHeader")

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

        header_type = all_params[model]["type"]
        pitch = all_params[model]["pitch"]
        rows = all_params[model]["rows"]
        base_width = all_params[model]["base_width"]
        base_height = all_params[model]["base_height"]
        base_chamfer = all_params[model]["base_chamfer"]
        base_extra_length = (
            all_params[model]["base_extra_length"]
            if "base_extra_length" in all_params[model]
            else 0
        )
        base_wall_height = (
            all_params[model]["base_wall_height"]
            if "base_wall_height" in all_params[model]
            else 0
        )
        base_wall_internal_width = (
            all_params[model]["base_wall_internal_width"]
            if "base_wall_internal_width" in all_params[model]
            else 0
        )
        base_wall_internal_extra_length = (
            all_params[model]["base_wall_internal_extra_length"]
            if "base_wall_internal_extra_length" in all_params[model]
            else 0
        )
        notch_x_size = (
            all_params[model]["notch_x_size"]
            if "notch_x_size" in all_params[model]
            else 0
        )
        notch_y_size = (
            all_params[model]["notch_y_size"]
            if "notch_y_size" in all_params[model]
            else 0
        )
        notch_height = (
            all_params[model]["notch_height"]
            if "notch_height" in all_params[model]
            else 0
        )
        notch_position = (
            all_params[model]["notch_position"]
            if "notch_position" in all_params[model]
            else ""
        )
        pin_width = all_params[model]["pin_width"]
        pin_length_above_base = all_params[model]["pin_length_above_base"]

        pin_end_chamfer = all_params[model]["pin_end_chamfer"]
        rotation = all_params[model]["rotation"]

        # Collect the array of pin numbers so that we can handle the one config that has a custom set in a string
        if isinstance(all_params[model]["pins"], str):
            pin_set = [int(x) for x in all_params[model]["pins"].split(",")]
        else:
            pin_num_start = all_params[model]["pins"]["from"]
            pin_num_end = all_params[model]["pins"]["to"]
            pin_set = range(pin_num_start, pin_num_end + 1)

        if base_chamfer == "auto":
            base_chamfer = pitch / 10.0

        if pin_end_chamfer == "auto":
            pin_end_chamfer = pin_width / 4.0

        for num_pins in pin_set:
            if header_type == "Vertical_THT":
                pin_length_below_board = all_params[model]["pin_length_below_board"]
                base = make_Vertical_THT_base(
                    num_pins, pitch, rows, base_width, base_height, base_chamfer
                )
                pins = make_Vertical_THT_pins(
                    num_pins,
                    pitch,
                    rows,
                    pin_length_above_base,
                    pin_length_below_board,
                    base_height,
                    pin_width,
                    pin_end_chamfer,
                )
            elif header_type == "Horizontal_THT":
                pin_length_below_board = all_params[model]["pin_length_below_board"]
                base_x_offset = all_params[model]["base_x_offset"]
                base = make_Horizontal_THT_base(
                    num_pins,
                    pitch,
                    rows,
                    base_width,
                    base_height,
                    base_x_offset,
                    base_chamfer,
                )
                pins = make_Horizontal_THT_pins(
                    num_pins,
                    pitch,
                    rows,
                    pin_length_above_base,
                    pin_length_below_board,
                    base_height,
                    base_width,
                    pin_width,
                    pin_end_chamfer,
                    base_x_offset,
                )
            elif header_type == "Vertical_SMD":
                pin_length_horizontal = all_params[model]["pin_length_horizontal"]
                base_z_offset = all_params[model]["base_z_offset"]
                if rows == 1:
                    pin_1_start = all_params[model]["pin_1_start"]
                else:
                    pin_1_start = None
                pins = make_Vertical_SMD_pins(
                    num_pins,
                    pitch,
                    rows,
                    pin_length_above_base,
                    pin_length_horizontal,
                    base_height,
                    base_width,
                    pin_width,
                    pin_end_chamfer,
                    base_z_offset,
                    pin_1_start,
                )
                base = make_Vertical_SMD_base(
                    num_pins,
                    pitch,
                    base_width,
                    base_height,
                    base_chamfer,
                    base_z_offset,
                    base_extra_length,
                    base_wall_height,
                    base_wall_internal_width,
                    base_wall_internal_extra_length,
                    notch_position,
                    notch_x_size,
                    notch_y_size,
                    notch_height,
                )

            else:
                print("Model {} is not recognized.".format(model))
                continue

            # Create the file name based on the rows and pins
            if num_pins < 10:
                num_pins_str = "0" + str(num_pins)
            else:
                num_pins_str = str(num_pins)
            file_name = model.replace("yy", num_pins_str)

            parts: list[cq.Workplane] = [base, pins]
            color_names: list[str] = [
                all_params[model]["body_color_key"],
                all_params[model]["pin_color_key"],
            ]

            export_tools.export(
                root_output_dir=output_dir_prefix,
                lib_name=all_params[model]["destination_dir"],
                model_name=file_name,
                parts=parts,
                color_names=color_names,
                export_as_vrml=enable_vrml,
            )
