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

__title__ = "make Valve 3D models exported to STEP and VRML"
__author__ = "scripts: Stefan; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import cadquery as cq

from _tools import export_tools, parameters

from .cq_belton_socket import cq_belton_socket
from .cq_dongxin_socket import cq_dongxin_socket
from .cq_parameters_glim import cq_parameters_glim
from .cq_parameters_socket_generic import cq_parameters_socket_generic
from .cq_parameters_tube_CK6418 import cq_parameters_tube_CK6418
from .cq_parameters_tube_generic import cq_parameters_tube_generic


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Valves")

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

        if "Belton" in all_params[model]["model_name"]:
            cqm = cq_belton_socket()
        elif "Dongxin" in all_params[model]["model_name"]:
            cqm = cq_dongxin_socket()
        elif "Glimm" in all_params[model]["model_name"]:
            cqm = cq_parameters_glim()
        elif "CK6418" in all_params[model]["model_name"]:
            cqm = cq_parameters_tube_CK6418()
        elif "Tube" in all_params[model]["model_name"]:
            cqm = cq_parameters_tube_generic()
        else:
            cqm = cq_parameters_socket_generic()

        # Make the parts of the model
        (body_top, body, pins, npth_pins) = cqm.make_3D_model(all_params[model])
        body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        if body_top:
            body_top = body_top.rotate(
                (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
            )
        if pins:
            pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        if npth_pins:
            npth_pins = npth_pins.rotate(
                (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
            )

        parts: list[cq.Workplane] = []
        color_names: list[str] = []
        if body is not None:
            parts.append(body)
            color_names.append(all_params[model]["body_color_key"])
        if body_top is not None:
            parts.append(body_top)
            color_names.append(all_params[model]["body_top_color_key"])
        if pins is not None:
            parts.append(pins)
            color_names.append(all_params[model]["pin_color_key"])
        if npth_pins is not None:
            parts.append(npth_pins)
            color_names.append(all_params[model]["npth_pin_color_key"])

        export_tools.export(
            root_output_dir=output_dir_prefix,
            lib_name=all_params[model]["destination_dir"],
            model_name=all_params[model]["model_name"],
            parts=parts,
            color_names=color_names,
            export_as_vrml=enable_vrml,
        )
