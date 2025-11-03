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
__author__ = (
    "scripts: Stefan, based on DIP script; models: see cq_model files; update: jmwright"
)
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import cadquery as cq

from _tools import export_tools, parameters

from .cq_parameters_Resonator_AT310 import *
from .cq_parameters_Resonator_C26_LF import *
from .cq_parameters_Resonator_C38_LF import *
from .cq_parameters_Resonator_peterman_smd import *
from .cq_parameters_Resonator_SMD_muRata_CSTx import *
from .cq_parameters_Resonator_smd_type_2 import *


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Crystal")

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

        # Make the parts of the model
        if model.startswith("AT310"):
            cqm = cq_parameters_Resonator_AT310()
        elif model.startswith("C26-LF"):
            cqm = cq_parameters_Resonator_C26_LF()
        elif model.startswith("C38-LF"):
            cqm = cq_parameters_Resonator_C38_LF()
        elif model.startswith("SMD"):
            cqm = cq_parameters_Resonator_peterman_smd()
        elif model.startswith("Murata"):
            cqm = cq_parameters_Resonator_SMD_muRata_CSTx()
        elif model.startswith("MicroCrystal"):
            cqm = cq_parameters_Resonator_smd_type_2()
        else:
            print("Model type {} not recognized.".format(model))

        body_top = cqm.make_top(all_params[model])
        body = cqm.make_case(all_params[model])
        # The Murata code tries to mutate the body model which does not work anymore, so we have to work around it
        if model.startswith("Murata"):
            pins, body = cqm.make_pins(body, all_params[model])
        else:
            pins = cqm.make_pins(body, all_params[model])

        body_top = body_top.rotate(
            (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
        )  # .translate((all_params[model]['F'] / 2.0, 0, 0))
        body = body.rotate(
            (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
        )  # .translate((all_params[model]['F'] / 2.0, 0, 0))
        pins = pins.rotate(
            (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
        )  # .translate((all_params[model]['F'] / 2.0, 0, 0))

        parts: list[cq.Workplane] = [body_top, body, pins]
        color_names: list[str] = [
            all_params[model]["body_top_color_key"],
            all_params[model]["body_color_key"],
            all_params[model]["pin_color_key"],
        ]
        # Handle the case of the SMD models that have a bottom as well as the other parts
        if model.startswith("SMD") or model.startswith("MicroCrystal"):
            bottom = cqm.make_bottom(body, all_params[model])
            bottom = bottom.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            parts.append(bottom)
            color_names.append(all_params[model]["bottom_color_key"])

        export_tools.export(
            root_output_dir=output_dir_prefix,
            lib_name=all_params[model]["destination_dir"],
            model_name=all_params[model]["file_name"],
            parts=parts,
            color_names=color_names,
            export_as_vrml=enable_vrml,
        )
