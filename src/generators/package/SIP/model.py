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

__title__ = "make SMD inductors 3D models exported to STEP and VRML"
__author__ = "scripts: Stefan; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import cadquery as cq

from _tools import export_tools, parameters

from .cq_eSIP import cq_eSIP
from .cq_Sanyo_STK4xx import cq_Sanyo_STK4xx
from .cq_SIP_3 import cq_SIP_3


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Package_SIP")

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

        if model == "PowerIntegrations_eSIP-7C":
            cqm = cq_eSIP()
            body_top = cqm.make_top_eSIP_7C(all_params[model])
            body = cqm.make_case_eSIP_7C(all_params[model])
            pins = cqm.make_pins_eSIP_7C(all_params[model])
            npth_pins = cqm.make_npth_pins(all_params[model])
        elif model == "PowerIntegrations_eSIP-7F":
            cqm = cq_eSIP()
            body_top = cqm.make_top_eSIP_7F(all_params[model])
            body = cqm.make_case_eSIP_7F(all_params[model])
            pins = cqm.make_pins_eSIP_7F(all_params[model])
            npth_pins = cqm.make_npth_pins(all_params[model])
        elif model == "Sanyo_STK4xx_59_2":
            cqm = cq_Sanyo_STK4xx()
            body_top = cqm.make_top_Sanyo_STK4xx_59_2(all_params[model])
            body = cqm.make_case_Sanyo_STK4xx_59_2(all_params[model])
            pins = cqm.make_pins_Sanyo_STK4xx_59_2(all_params[model])
            npth_pins = cqm.make_npth_pins(all_params[model])
        elif model == "Sanyo_STK4xx_78_0":
            cqm = cq_Sanyo_STK4xx()
            body_top = cqm.make_top_Sanyo_STK4xx_78_0(all_params[model])
            body = cqm.make_case_Sanyo_STK4xx_78_0(all_params[model])
            pins = cqm.make_pins_Sanyo_STK4xx_78_0(all_params[model])
            npth_pins = cqm.make_npth_pins(all_params[model])
        elif model == "SIP4_Sharp_Angled":
            cqm = cq_SIP_3()
            body_top = cqm.make_top_dummy(all_params[model])
            body = cqm.make_case_SIP4_Sharp_Angled(all_params[model])
            pins = cqm.make_pins_SIP4_Sharp_Angled(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        elif model == "SIP4_Sharp_Straight":
            cqm = cq_SIP_3()
            body_top = cqm.make_top_dummy(all_params[model])
            body = cqm.make_case_SIP4_Sharp_Straight(all_params[model])
            pins = cqm.make_pins_SIP4_Sharp_Straight(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        elif model == "SIP-3_P1.30mm":
            cqm = cq_SIP_3()
            body_top = cqm.make_top_dummy(all_params[model])
            body = cqm.make_case_SIP_3_P1_30mm(all_params[model])
            pins = cqm.make_pins_SIP_3_P1_30mm(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        elif model == "SIP-3_P2.90mm":
            cqm = cq_SIP_3()
            body_top = cqm.make_top_dummy(all_params[model])
            body = cqm.make_case_SIP_3_P2_90mm(all_params[model])
            pins = cqm.make_pins_SIP_3_P2_90mm(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        elif model == "SIP-8":
            cqm = cq_SIP_3()
            body_top = cqm.make_top_dummy(all_params[model])
            body = cqm.make_case_SIP_8(all_params[model])
            pins = cqm.make_pins_SIP_8(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        elif model == "SIP-9":
            cqm = cq_SIP_3()
            body_top = cqm.make_top_dummy(all_params[model])
            body = cqm.make_case_SIP_9(all_params[model])
            pins = cqm.make_pins_SIP_9(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        elif model == "SLA704XM":
            cqm = cq_SIP_3()
            body_top = cqm.make_top_dummy(all_params[model])
            body = cqm.make_case_SLA704XM(all_params[model])
            pins = cqm.make_pins_SLA704XM(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        elif model == "STK672-040-E":
            cqm = cq_SIP_3()
            body_top = cqm.make_top_dummy(all_params[model])
            body = cqm.make_case_STK672_040_E(all_params[model])
            pins = cqm.make_pins_STK672_040_E(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        elif model == "STK672-080-E":
            cqm = cq_SIP_3()
            body_top = cqm.make_top_dummy(all_params[model])
            body = cqm.make_case_STK672_080_E(all_params[model])
            pins = cqm.make_pins_STK672_080_E(all_params[model])
            npth_pins = cqm.make_npth_pins_dummy(all_params[model])
        else:
            print(
                "Match for model name {} not found.".format(
                    all_params[model]["model_name"]
                )
            )
            continue

        # Make the parts of the model
        body_top = body_top.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
        npth_pins = npth_pins.rotate(
            (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
        )

        parts: list[cq.Workplane] = [body, pins]
        color_names: list[str] = [
            all_params[model]["body_color_key"],
            all_params[model]["pin_color_key"],
        ]
        # Make sure we do not have a dummy top
        if not isinstance(body_top.val(), cq.Vector):
            parts.append(body_top)
            color_names.append(all_params[model]["body_top_color_key"])
        # Make sure we do not have dummy nth pins
        if not isinstance(npth_pins.val(), cq.Vector):
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
