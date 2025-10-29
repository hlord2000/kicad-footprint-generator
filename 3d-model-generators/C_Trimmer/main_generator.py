# -*- coding: utf-8 -*-
#!/usr/bin/python
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
## the script will generate STEP and VRML parametric models
## to be used with kicad StepUp script
#
# *                                                                          *
# * cadquery script for generating QFP/SOIC/SSOP/TSSOP models in STEP AP214  *
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
# *   it under the terms of the GNU General Public License (GPL)             *
# *   as published by the Free Software Foundation; either version 2 of      *
# *   the License, or (at your option) any later version.                    *
# *   for detail see the LICENCE text file.                                  *
# *                                                                          *
# *   This program is distribuited in the hope that it will be useful,        *
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

__title__ = "make Valve 3D models"
__author__ = "scripts: Stefan, based on Valve script; models: see cq_model files; update: jmwright"
__Comment__ = """Makes varistor 3D models exported to STEP and VRML."""

___ver___ = "2.0.0"

import os
from math import radians, tan

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from . import cq_murata, cq_sprague_goodman, cq_voltronics


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("C_Trimmer")

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
            all_params[model]["pins_color_key"]
        ].getDiffuseFloat()

        # Generate the current model
        if all_params[model]["model_class"] == "murata":
            cqm = cq_murata.cq_murata()
        elif all_params[model]["model_class"] == "sprague_goodman":
            cqm = cq_sprague_goodman.cq_sprague_goodman()
        elif all_params[model]["model_class"] == "voltronics":
            cqm = cq_voltronics.cq_voltronics()
        else:
            print("ERROR: No match found for the model_class")
            continue

        # Used to wrap all the parts into an assembly
        component = cq.Assembly(name=model)

        # The CP Axial capacitors are a special case
        if all_params[model]["model_class"] == "murata":
            if all_params[model]["modelName"].endswith("Murata_TZB4-A"):
                body_top = cqm.make_top_Murata_TZB4_A(all_params[model])
                body = cqm.make_case_Murata_TZB4_A(all_params[model])
                pins = cqm.make_pin_Murata_TZB4_A(all_params[model])
            elif all_params[model]["modelName"].endswith("Murata_TZB4-B"):
                body_top = cqm.make_top_Murata_TZB4_B(all_params[model])
                body = cqm.make_case_Murata_TZB4_B(all_params[model])
                pins = cqm.make_pin_Murata_TZB4_B(all_params[model])
            elif all_params[model]["modelName"].endswith("Murata_TZC3"):
                body_top = cqm.make_top_Murata_TZC3(all_params[model])
                body = cqm.make_case_Murata_TZC3(all_params[model])
                pins = cqm.make_pin_Murata_TZC3(all_params[model])
            elif all_params[model]["modelName"].endswith("Murata_TZR1"):
                body_top = cqm.make_top_Murata_TZR1(all_params[model])
                body = cqm.make_case_Murata_TZR1(all_params[model])
                pins = cqm.make_pin_Murata_TZR1(all_params[model])
            elif all_params[model]["modelName"].endswith("Murata_TZW4"):
                body_top = cqm.make_top_Murata_TZW4(all_params[model])
                body = cqm.make_case_Murata_TZW4(all_params[model])
                pins = cqm.make_pin_Murata_TZW4(all_params[model])
            elif all_params[model]["modelName"].endswith("Murata_TZY2"):
                body_top = cqm.make_top_Murata_TZY2(all_params[model])
                body = cqm.make_case_Murata_TZY2(all_params[model])
                pins = cqm.make_pin_Murata_TZY2(all_params[model])
            else:
                print("ERROR: No match found for the modelName")
                continue
        elif all_params[model]["model_class"] == "sprague_goodman":
            body_top = cqm.make_top_Sprague_Goodman_SGC3(all_params[model])
            body = cqm.make_case_Sprague_Goodman_SGC3(all_params[model])
            pins = cqm.make_pin_Sprague_Goodman_SGC3(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        elif all_params[model]["model_class"] == "voltronics":
            if all_params[model]["modelName"].endswith("Voltronics_JN"):
                body_top = cqm.make_top_Voltronics_JN(all_params[model])
                body = cqm.make_case_Voltronics_JN_JQ(all_params[model])
                pins = cqm.make_pin_Voltronics_JN_JQ(all_params[model])
            elif all_params[model]["modelName"].endswith("Voltronics_JQ"):
                body_top = cqm.make_top_Voltronics_JQ(all_params[model])
                body = cqm.make_case_Voltronics_JN_JQ(all_params[model])
                pins = cqm.make_pin_Voltronics_JN_JQ(all_params[model])
            elif all_params[model]["modelName"].endswith("Voltronics_JR"):
                body_top = cqm.make_top_Voltronics_JR(all_params[model])
                body = cqm.make_case_Voltronics_JR(all_params[model])
                pins = cqm.make_pin_Voltronics_JR(all_params[model])
            elif all_params[model]["modelName"].endswith("Voltronics_JV"):
                body_top = cqm.make_top_Voltronics_JV(all_params[model])
                body = cqm.make_case_Voltronics_JV(all_params[model])
                pins = cqm.make_pin_Voltronics_JV(all_params[model])
            elif all_params[model]["modelName"].endswith("Voltronics_JZ"):
                body_top = cqm.make_top_Voltronics_JZ(all_params[model])
                body = cqm.make_case_Voltronics_JZ(all_params[model])
                pins = cqm.make_pin_Voltronics_JZ(all_params[model])
            else:
                print("ERROR: No match found for the modelName")
                continue
        else:
            print("ERROR: No match for model_class")
            continue

        # Rotate all parts to the correct orientation
        # body_top = body_top.rotate((0, 0, 0), (0, 0, 1), all_params[model]['rotation'])
        # body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]['rotation'])
        # pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]['rotation'])

        # Add the parts to the assembly
        component.add(
            body_top,
            color=cq_color_correct.Color(
                body_top_color[0], body_top_color[1], body_top_color[2]
            ),
        )
        component.add(
            body,
            color=cq_color_correct.Color(body_color[0], body_color[1], body_color[2]),
        )
        component.add(
            pins,
            color=cq_color_correct.Color(pins_color[0], pins_color[1], pins_color[2]),
        )

        # Handle nth pins
        if all_params[model]["model_class"] == "sprague_goodman":
            nth_pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()
            component.add(
                npth_pins,
                color=cq_color_correct.Color(
                    nth_pins_color[0], nth_pins_color[1], nth_pins_color[2]
                ),
            )

        # Export the assembly to STEP
        export_tools.export_step(component, output_dir, model)

        # Export the assembly to VRML
        if enable_vrml:
            export_VRML(
                os.path.join(output_dir, model + ".wrl"),
                [body_top, body, pins],
                [
                    all_params[model]["body_top_color_key"],
                    all_params[model]["body_color_key"],
                    all_params[model]["pins_color_key"],
                ],
            )
