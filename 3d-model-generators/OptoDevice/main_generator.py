#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# * These are cadquery tools to export                                       *
# * generated models in STEP & VRML format.                                  *
# *                                                                          *
# * cadquery script for generating coil models in STEP AP214                 *
# * Copyright (c) 2025 KiCad Library Team                                    *
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

__title__ = "make opto device 3D models exported to STEP and VRML"
__author__ = "scripts: aris-kimi"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import cadquery as cq

from _tools import export_tools, parameters

from .vishay_cny70 import make_Vishay_CNY70
from .vishay_tcrt5000 import make_Vishay_TCRT5000


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("OptoDevice")

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

        modelName = all_params[model]["model_name"]
        # Make the parts of the model
        if modelName == "Vishay_CNY70":
            (body, em, dt, text, pin) = make_Vishay_CNY70(all_params[model])
        elif modelName == "Vishay_TCRT5000":
            (body, em, dt, text, pin) = make_Vishay_TCRT5000(all_params[model])

        body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        em = em.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        dt = dt.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        text = text.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        pin = pin.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])

        parts: list[cq.Workplane] = [body, em, dt, text, pin]
        color_names: list[str] = [
            all_params[model]["body_color_key"],
            all_params[model]["emitter_color_key"],
            all_params[model]["detector_color_key"],
            all_params[model]["text_color_key"],
            all_params[model]["pin_color_key"],
        ]

        export_tools.export(
            root_output_dir=output_dir_prefix,
            lib_name=all_params[model]["destination_dir"],
            model_name=all_params[model]["model_name"],
            parts=parts,
            color_names=color_names,
            export_as_vrml=enable_vrml,
        )
