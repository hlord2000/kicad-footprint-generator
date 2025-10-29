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
# * cadquery script for generating QFP/SOIC/SSOP/TSSOP models in STEP AP214  *
# * Original script:                                                         *
# * Copyright (c) 2016 Hasan Yavuz Özderya https://bitbucket.org/hyOzd       *
# *                    Maurice https://github.com/easyw                      *
# *                    Rene Poeschl https://github.com/poeschlr              *
# * Refactored to be model-independent:                                      *
# * Copyright (c) 2017 Ray Benitez https://github.com/hackscribble           *
# * Updated:                                                                 *
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

__title__ = "export of 3D models exported to STEP and VRML"
__author__ = "scripts: hackscribble; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from .DPAK_factory import (
    ATPAK,
    HSOF8,
    SOT89,
    SOT669,
    SOT1235,
    TO252,
    TO263,
    TO268,
    Infineon_PG_TO_220_7Lead_TabPin8,
    Rohm_HRP7,
)


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("TO_SOT_Packages_SMD_custom")

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
            all_params[model]["base"]["device"]["body"]["colour"]
        ].getDiffuseFloat()
        tab_color = shaderColors.named_colors[
            all_params[model]["base"]["device"]["tab"]["colour"]
        ].getDiffuseFloat()
        pin_color = shaderColors.named_colors[
            all_params[model]["base"]["device"]["pins"]["colour"]
        ].getDiffuseFloat()

        # Check the model name to see which class to load
        available_models = {
            "TO-252": TO252,
            "TO-263": TO263,
            "TO-268": TO268,
            "ATPAK": ATPAK,
            "HSOF8": HSOF8,
            "LFPAK56": SOT669,
            "LFPAK88": SOT1235,
            "SOT89": SOT89,
            "Infineon_PG_TO_220_7Lead_TabPin8": Infineon_PG_TO_220_7Lead_TabPin8,
            "Rohm_HRP7": Rohm_HRP7,
        }
        try:
            cqm = available_models[model]()
        except KeyError:
            print(
                f"Model not recognized '{model}'. Please choose from the available models: {list(sorted(available_models.keys()))}."
            )
            continue

        # Build all the variants
        for variant in all_params[model]["variants"]:
            # Make the parts of the model
            (body, tab, pins, file_name) = cqm.build_series(
                all_params[model]["base"], all_params[model]["variants"][variant]
            )
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
                tab,
                color=cq_color_correct.Color(tab_color[0], tab_color[1], tab_color[2]),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(pin_color[0], pin_color[1], pin_color[2]),
            )

            # Assemble the filename
            # file_name = all_params[model]['model_name']

            # Export the assembly to STEP
            component.name = file_name
            export_tools.export_step(component, output_dir, file_name)

            # Export the assembly to VRML
            if enable_vrml:
                export_VRML(
                    os.path.join(output_dir, file_name + ".wrl"),
                    [body, tab, pins],
                    [
                        all_params[model]["base"]["device"]["body"]["colour"],
                        all_params[model]["base"]["device"]["tab"]["colour"],
                        all_params[model]["base"]["device"]["pins"]["colour"],
                    ],
                )
