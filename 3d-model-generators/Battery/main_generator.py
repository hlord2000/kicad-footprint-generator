#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is derived from a cadquery script for generating Converter_DCDC 3D
# format
#
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
# This is a
# Dimensions are from Microchips Packaging Specification document:
# DS00000049BY. Body drawing is the same as QFP generator#
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

__title__ = "make various battery 3D models"
__author__ = "Stefan, jmwright"
__Comment__ = "make battery 3D models exported to STEP and VRML"

___ver___ = "2.0.0"

import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

# import .battery_casebutton
from .battery_casebutton import *

# import .battery_caseBX0036
from .battery_caseBX0036 import *

# import .battery_casecylinder
from .battery_casecylinder import *

# import .battery_common
from .battery_common import *

# import .battery_contact
from .battery_contact import *

# import .battery_pins
from .battery_pins import *

# import .cq_Keystone_2993
from .cq_Keystone_2993 import *

# import .cq_Seiko_MSXXXX
from .cq_Seiko_MSXXXX import *

dest_dir_prefix = "Battery.3dshapes"


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Battery")

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

    if output_dir_prefix == None:
        print("ERROR: An output directory must be provided.")
        return
    else:
        # Construct the final output directory
        output_dir = os.path.join(output_dir_prefix, dest_dir_prefix)

    # Step through the selected models
    for model in models:
        # Safety check to make sure the selected model is valid
        if not model in all_params.keys():
            print("Parameters for %s doesn't exist in 'all_params', skipping." % model)
            continue

        # Handle each model type
        if model == "BatteryHolder_Seiko_MS621F":
            case = make_case_Seiko_MS621F(all_params[model])
            pins = make_pins_Seiko_MS621F(all_params[model])
        elif model == "BatteryHolder_Keystone_2993":
            case = make_case_Keystone_2993(all_params[model])
            pins = make_pins_Keystone_2993(all_params[model])
        elif all_params[model]["modeltype"] == "BX0036":
            case = make_case_BX0036(all_params[model])
            pins = make_pins(all_params[model])
        elif all_params[model]["modeltype"] == "Button1":
            case = make_case_Button1(all_params[model])
            pins = make_pins(all_params[model])
        elif all_params[model]["modeltype"] == "Button2":
            case = make_case_Button2(all_params[model])
            pins = make_pins(all_params[model])
        elif all_params[model]["modeltype"] == "Button3":
            case = make_case_Button3(all_params[model])
            pins = make_pins(all_params[model])
        elif all_params[model]["modeltype"] == "Button4":
            case = make_case_Button4(all_params[model])
            pins = make_pins(all_params[model])
        elif all_params[model]["modeltype"] == "Cylinder1":
            case = make_case_Cylinder1(all_params[model])
            pins = make_pins(all_params[model])

        # Load the appropriate colors
        body_color = shaderColors.named_colors[
            all_params[model]["body_color_key"]
        ].getDiffuseFloat()
        pins_color = shaderColors.named_colors[
            all_params[model]["pins_color_key"]
        ].getDiffuseFloat()

        # Wrap the component parts in an assembly so that we can attach colors
        component = cq.Assembly(name=model)
        if case:
            component.add(
                case,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
        if pins:
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

        # Export the assembly to STEP
        export_tools.export_step(component, output_dir, model)

        # Export the assembly to VRML
        if enable_vrml:
            if case is not None:
                export_VRML(
                    os.path.join(output_dir, model + ".wrl"),
                    [case, pins],
                    [
                        all_params[model]["body_color_key"],
                        all_params[model]["pins_color_key"],
                    ],
                )
            else:
                export_VRML(
                    os.path.join(output_dir, model + ".wrl"),
                    [pins],
                    [all_params[model]["pins_color_key"]],
                )
