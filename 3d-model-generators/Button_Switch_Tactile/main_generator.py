#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# CadQuery script for generating tactile button 3D models
#
# This is derived from a CadQuery script for generating QFP models in
# X3D format, from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
#
# Thanks to Frank Severinsen (Shack) for including the orignal VRML
# materials.
#
# Copyright (c) 2015 Maurice https://launchpad.net/~easyw
# Copyright (c) 2021 jmwright (https://github.com/jmwright)
# Work sponsored by KiCAD Services Corporation
#      (https://www.kipro-pcb.com/)
#
# Copyright (c) 2024-2025 Martin Sotirov <martin@libtec.org>
#
# All trademarks within this guide belong to their legitimate owners.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License (LGPL)
# as published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.
# for detail see the LICENCE text file.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Button_Switch_Tactile")

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
        shell_color = shaderColors.named_colors[
            all_params[model]["shell_color_key"]
        ].getDiffuseFloat()
        actuator_color = shaderColors.named_colors[
            all_params[model]["actuator_color_key"]
        ].getDiffuseFloat()
        if all_params[model].get("actuator_base_color_key"):
            actuator_base_color = shaderColors.named_colors[
                all_params[model]["actuator_base_color_key"]
            ].getDiffuseFloat()
        else:
            actuator_base_color = None
        pins_color = shaderColors.named_colors[
            all_params[model]["pins_color_key"]
        ].getDiffuseFloat()

        # Generate the current model
        if all_params[model]["model_class"] == "tactile":
            from .cq_models import cq_tactile as cqm
        else:
            print("ERROR: No match found for the model_class")
            continue

        body = cqm.make_body(all_params[model])
        shell = cqm.make_shell(all_params[model])
        pins = cqm.make_pins(all_params[model])
        actuator = cqm.make_actuator(all_params[model])
        actuator_base = cqm.make_actuator_base(all_params[model])

        if all_params[model].get("rotation"):
            body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            shell = shell.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            actuator = actuator.rotate(
                (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
            )
            if actuator_base:
                actuator_base = actuator_base.rotate(
                    (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
                )

        if all_params[model].get("translation"):
            body = body.translate(all_params[model]["translation"])
            shell = shell.translate(all_params[model]["translation"])
            pins = pins.translate(all_params[model]["translation"])
            actuator = actuator.translate(all_params[model]["translation"])
            if actuator_base:
                actuator_base = actuator_base.translate(
                    all_params[model]["translation"]
                )

        # Wrap the component parts in an assembly so that we can attach colors
        component = cq.Assembly(name=model)
        component.add(body, color=cq_color_correct.Color(*body_color))
        component.add(shell, color=cq_color_correct.Color(*shell_color))
        component.add(pins, color=cq_color_correct.Color(*pins_color))
        component.add(actuator, color=cq_color_correct.Color(*actuator_color))
        if actuator_base:
            component.add(
                actuator_base, color=cq_color_correct.Color(*actuator_base_color)
            )

        # Export the assembly to STEP
        export_tools.export_step(component, output_dir, model)

        # Export the assembly to VRML
        if enable_vrml:
            meshes = [body, shell, pins, actuator]
            colors = [
                all_params[model]["body_color_key"],
                all_params[model]["shell_color_key"],
                all_params[model]["pins_color_key"],
                all_params[model]["actuator_color_key"],
            ]

            if actuator_base:
                meshes.append(actuator_base)
                colors.append(all_params[model]["actuator_base_color_key"])

            export_VRML(os.path.join(output_dir, model + ".wrl"), meshes, colors)
