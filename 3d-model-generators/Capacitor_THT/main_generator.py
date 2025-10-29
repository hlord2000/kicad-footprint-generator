#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This was originaly derived from a cadquery script for generating PDIP models in X3D format
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
#
# Adapted by easyw for step and vrlm export
# See https://github.com/easyw/kicad-3d-models-in-freecad
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
# * These are FreeCAD & cadquery tools                                       *
# * to export generated models in STEP & VRML format.                        *
# *                                                                          *
# * cadquery script for generating Molex models in STEP AP214                *
# *   Copyright (c) 2016                                                     *
# * Rene Poeschl https://github.com/poeschlr                                 *
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
__author__ = "scripts: maurice and hyOzd; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import os
from math import radians, tan

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from .cq_models import c_axial_tht, c_disc_tht, c_rect_tht, cp_axial_tht

# dest_dir_prefix = "Package_BGA.3dshapes"


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Capacitor_THT")

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
            all_params[model]["body_color_key"]
        ].getDiffuseFloat()
        pins_color = shaderColors.named_colors[
            all_params[model]["pins_color_key"]
        ].getDiffuseFloat()

        # Generate the current model
        if all_params[model]["model_class"] == "c_axial_tht":
            cqm = c_axial_tht
        elif all_params[model]["model_class"] == "c_disc_tht":
            cqm = c_disc_tht
        elif all_params[model]["model_class"] == "c_rect_tht":
            cqm = c_rect_tht
        elif all_params[model]["model_class"] == "cp_axial_tht":
            cqm = cp_axial_tht
        else:
            print("ERROR: No match found for the model_class")
            continue

        # Used to collect the parts and their colors for VRML export
        parts = []
        colors = []

        # Used to wrap all the parts into an assembly
        component = cq.Assembly(name=model)

        # The CP Axial capacitors are a special case
        if all_params[model]["model_class"] == "cp_axial_tht":
            # Get the extra colors
            mark_vg_color = shaderColors.named_colors[
                all_params[model]["mark_vg_color_key"]
            ].getDiffuseFloat()
            mark_bg_color = shaderColors.named_colors[
                all_params[model]["mark_bg_color_key"]
            ].getDiffuseFloat()
            endcaps_color = shaderColors.named_colors[
                all_params[model]["endcaps_color_key"]
            ].getDiffuseFloat()

            body, mmb, bar, leads, top = cqm.generate_part(all_params[model])

            body = body.translate(
                (
                    all_params[model]["body_setback_distance"],
                    0.0,
                    all_params[model]["body_board_distance"],
                )
            ).rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            leads = leads.translate(
                (
                    all_params[model]["body_setback_distance"],
                    0.0,
                    all_params[model]["body_board_distance"],
                )
            ).rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            mmb = mmb.translate(
                (
                    all_params[model]["body_setback_distance"],
                    0.0,
                    all_params[model]["body_board_distance"],
                )
            ).rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            bar = bar.translate(
                (
                    all_params[model]["body_setback_distance"],
                    0.0,
                    all_params[model]["body_board_distance"],
                )
            ).rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            top = top.translate(
                (
                    all_params[model]["body_setback_distance"],
                    0.0,
                    all_params[model]["body_board_distance"],
                )
            ).rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])

            component.add(
                body,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                leads,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )
            component.add(
                mmb,
                color=cq_color_correct.Color(
                    mark_vg_color[0], mark_vg_color[1], mark_vg_color[2]
                ),
            )
            component.add(
                bar,
                color=cq_color_correct.Color(
                    mark_bg_color[0], mark_bg_color[1], mark_bg_color[2]
                ),
            )
            component.add(
                top,
                color=cq_color_correct.Color(
                    endcaps_color[0], endcaps_color[1], endcaps_color[2]
                ),
            )

            # Collect the VRML information
            parts.append(body)
            parts.append(leads)
            parts.append(mmb)
            parts.append(bar)
            parts.append(top)
            colors.append(all_params[model]["body_color_key"])
            colors.append(all_params[model]["pins_color_key"])
            colors.append(all_params[model]["mark_vg_color_key"])
            colors.append(all_params[model]["mark_bg_color_key"])
            colors.append(all_params[model]["endcaps_color_key"])
        else:
            body, leads = cqm.generate_part(all_params[model])

            body = body.translate(
                (
                    all_params[model]["body_setback_distance"],
                    0.0,
                    all_params[model]["body_board_distance"],
                )
            ).rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            leads = leads.translate(
                (all_params[model]["body_setback_distance"], 0.0, 0.0)
            ).rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])

            # Wrap the component parts in an assembly so that we can attach colors
            component.add(
                body,
                name="body",
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                leads,
                name="leads",
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Collect the VRML information
            parts.append(body)
            parts.append(leads)
            colors.append(all_params[model]["body_color_key"])
            colors.append(all_params[model]["pins_color_key"])

        # Export the assembly to STEP
        export_tools.export_step(component, output_dir, model)

        # Export the assembly to VRML
        if enable_vrml:
            export_VRML(os.path.join(output_dir, model + ".wrl"), parts, colors)
