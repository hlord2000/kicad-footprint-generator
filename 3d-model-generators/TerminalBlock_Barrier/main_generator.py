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
# * Copyright (c) 2020                                                       *
# *     sethhillbrand (https://gitlab.com/sethhillbrand)                     *
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
__author__ = "scripts: harty911; models: see cq_model files"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "1.0.0"

import os

from _tools import parameters

from kilibs.declarative_defs.packages.terminal_block_barrier_properties import (
    TerminalBlockBarrierProperties,
)

from .terminalblock_barrier import generate_model


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """

    model_ids = []

    all_params = parameters.load_data_parameters("TerminalBlock_Barrier")

    # Handle the case where no model has been passed or all models
    if model_to_build == "all" or model_to_build is None:
        model_ids = all_params.keys()
    else:
        model_ids = [model_to_build]

    # Step through the selected models
    for model_id in model_ids:

        cfg = TerminalBlockBarrierProperties(all_params[model_id], model_id)

        # Construct the final output directory
        if output_dir_prefix == None:
            print("ERROR: An output directory must be provided.")
            return
        else:
            output_dir = os.path.join(output_dir_prefix, cfg.lib_name + ".3dshapes")

        # Create the output directory if it does not exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Safety check to make sure the selected model is valid
        if not model_id in all_params.keys():
            print(f"Parameters for {model_id} doesn't exist in 'all_params', skipping.")
            continue

        print(f"       {model_id}:")

        generate_model(cfg, output_dir, enable_vrml)
