#!/usr/bin/env python3

# CadQuery script for generating rotary switch 3D models
#
# Copyright (c) 2015 Maurice https://launchpad.net/~easyw
# Copyright (c) 2022 jmwright (https://github.com/jmwright)
# Work sponsored by KiCAD Services Corporation
#      (https://www.kipro-pcb.com/)
#
# Copyright (c) 2024 Martin Sotirov <martin@libtec.org>
#
# All trademarks within this guide belong to their legitimate owners.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License (GPL)
# as published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.
# For detail see the LICENCE text file.
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

    all_params = parameters.load_parameters("Button_Switch_Rotary")

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

        # Select the model script
        if all_params[model]["model_class"] == "rotary":
            from .cq_models import cq_rotary as cqm
        else:
            print("ERROR: No match found for the model_class")
            continue

        # Make the parts of the model
        body = cqm.make_body(all_params[model])
        dial = cqm.make_dial(all_params[model])
        shell = cqm.make_shell(all_params[model])
        pins = cqm.make_pins(all_params[model])
        labels = cqm.make_labels(all_params[model])

        # Load the appropriate colors
        body_color = shaderColors.named_colors[
            all_params[model]["body_color_key"]
        ].getDiffuseFloat()
        dial_color = shaderColors.named_colors[
            all_params[model]["dial_color_key"]
        ].getDiffuseFloat()
        shell_color = shaderColors.named_colors[
            all_params[model]["shell_color_key"]
        ].getDiffuseFloat()
        pin_color = shaderColors.named_colors[
            all_params[model]["pin_color_key"]
        ].getDiffuseFloat()
        labels_color = shaderColors.named_colors[
            all_params[model]["labels_color_key"]
        ].getDiffuseFloat()

        if all_params[model].get("rotation"):
            body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            dial = dial.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            shell = shell.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
            labels = labels.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])

        if all_params[model].get("translation"):
            body = body.translate(all_params[model]["translation"])
            pins = pins.translate(all_params[model]["translation"])
            dial = dial.translate(all_params[model]["translation"])
            shell = shell.translate(all_params[model]["translation"])
            labels = labels.translate(all_params[model]["translation"])

        # Used to wrap all the parts into an assembly
        component = cq.Assembly(name=model)
        component.add(body, color=cq_color_correct.Color(*body_color))
        component.add(dial, color=cq_color_correct.Color(*dial_color))
        component.add(shell, color=cq_color_correct.Color(*shell_color))
        component.add(pins, color=cq_color_correct.Color(*pin_color))
        component.add(labels, color=cq_color_correct.Color(*labels_color))

        # Export the assembly to STEP
        export_tools.export_step(component, output_dir, model)

        # Export the assembly to VRML
        if enable_vrml:
            export_VRML(
                os.path.join(output_dir, model + ".wrl"),
                [body, dial, shell, pins, labels],
                [
                    all_params[model]["body_color_key"],
                    all_params[model]["dial_color_key"],
                    all_params[model]["shell_color_key"],
                    all_params[model]["pin_color_key"],
                    all_params[model]["labels_color_key"],
                ],
            )
