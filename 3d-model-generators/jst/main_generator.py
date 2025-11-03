#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is derived from a cadquery script for generating PDIP models in X3D format
#
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
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
# * cadquery script for generating JST-XH models in STEP AP214               *
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

__title__ = "main generator for molex connector 3D models exported to STEP and VRML"
__author__ = "scripts: maurice and hyOzd; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import cadquery as cq

from _tools import export_tools, parameters

from .cq_models import (
    conn_jst_eh_models,
    conn_jst_gh_models,
    conn_jst_ph_models,
    conn_jst_xh_models,
)


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("jst")

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
        for pin_num in all_params[model]["pin_range"]:
            all_params[model]["num_pins"] = pin_num
            length = all_params[model]["body_length"]
            all_params[model]["body_length"] = all_params[model][
                "body_start_length"
            ] + (all_params[model]["pin_pitch"] * (pin_num - 1))

            # Figure out which code to execute to create the models
            if all_params[model]["series"] == "EH":
                cqm = conn_jst_eh_models
            elif all_params[model]["series"] == "GH":
                cqm = conn_jst_gh_models
            elif all_params[model]["series"] == "PH":
                cqm = conn_jst_ph_models
            elif (
                all_params[model]["series"] == "XH"
                or all_params[model]["series"] == "XHVS"
            ):
                cqm = conn_jst_xh_models
            else:
                print("Model not recognized: {}".format(all_params[model]["series"]))

            # Make the parts of the model
            body = cqm.generate_body(all_params[model])
            pins = cqm.generate_pins(all_params[model])
            body = body.rotateAboutCenter((0, 0, 1), all_params[model]["rotation"])
            pins = pins.rotateAboutCenter((0, 0, 1), all_params[model]["rotation"])
            body = body.translate(all_params[model]["translation"])
            pins = pins.translate(all_params[model]["translation"])

            # Assemble the filename
            pad_pins = "0" + str(pin_num) if pin_num < 10 else str(pin_num)
            file_name = all_params[model]["file_name"].format(
                num_pins=pin_num, padded_pins=pad_pins
            )

            parts: list[cq.Workplane] = [body, pins]
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
