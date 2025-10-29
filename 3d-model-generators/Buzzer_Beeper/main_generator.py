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
## the script will generate STEP and VRML parametric models
## to be used with kicad StepUp script

# * These are a FreeCAD & cadquery tools                                     *
# * to export generated models in STEP & VRML format.                        *
# *                                                                          *
# * cadquery script for generating QFP/SOIC/SSOP/TSSOP models in STEP AP214  *
# *   Copyright (c) 2015                                                     *
# * Maurice https://launchpad.net/~easyw                                     *
# * Copyright (c) 2021                                                       *
# *     Update 2021                                                          *
# *     jmwright (https://github.com/jmwright)                               *
# *     Work sponsored by KiCAD Services Corporation                         *
# *          (https://www.kipro-pcb.com/)                                    *
# * Copyright (c) 2024                                                       *
# *     Martin Sotirov <martin@libtec.org>                                   *
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

__title__ = "make Valve 3D models"
__author__ = "Stefan, based on DIP script"
__Comment__ = (
    "make varistor 3D models exported to STEP and VRML for Kicad StepUP script"
)

___ver___ = "2.0.0"

import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from . import cq_parameters_smd_generic_rectangular
from .cq_parameters_CUI_CST_931RP_A import cq_parameters_CUI_CST_931RP_A
from .cq_parameters_EMB84Q_RO_SMT_0825_S_4_R import (
    cq_parameters_EMB84Q_RO_SMT_0825_S_4_R,
)
from .cq_parameters_kingstate_KCG0601 import cq_parameters_kingstate_KCG0601
from .cq_parameters_murata_PKMCS0909E4000 import cq_parameters_murata_PKMCS0909E4000
from .cq_parameters_ProjectsUnlimited_AI_4228_TWT_R import (
    cq_parameters_ProjectsUnlimited_AI_4228_TWT_R,
)
from .cq_parameters_ProSignal_ABI_XXX_RC import cq_parameters_ProSignal_ABI_XXX_RC
from .cq_parameters_PUI_AI_1440_TWT_24V_2_R import cq_parameters_PUI_AI_1440_TWT_24V_2_R
from .cq_parameters_StarMicronics_HMB_06_HMB_12 import (
    cq_parameters_StarMicronics_HMB_06_HMB_12,
)
from .cq_parameters_TDK_PS1240P02BT import cq_parameters_TDK_PS1240P02BT
from .cq_parameters_tht_generic_round import cq_parameters_tht_generic_round


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("Buzzer_Beeper")

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

        # Collections of the components and their matching colors to export to VRML
        parts = []
        colors = []

        # Wrap the component parts in an assembly so that we can attach colors
        component = cq.Assembly(name=model)

        # Generate the current model
        if all_params[model]["model_class"] == "cq_parameters_tht_generic_round":
            cqm = cq_parameters_tht_generic_round()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            body_color = shaderColors.named_colors[
                all_params[model]["body_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()
            npth_pin_color = shaderColors.named_colors[
                all_params[model]["npth_pin_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_top(all_params[model])
            case = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])
            npth_pins = cqm.make_npth_pins(all_params[model])

            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                case,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )
            if npth_pins:
                component.add(
                    npth_pins,
                    color=cq_color_correct.Color(
                        npth_pin_color[0], npth_pin_color[1], npth_pin_color[2]
                    ),
                )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(case)
            parts.append(pins)
            if npth_pins:
                parts.append(npth_pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["body_color_key"])
            colors.append(all_params[model]["pins_color_key"])
            if npth_pins:
                colors.append(all_params[model]["npth_pin_color_key"])
        elif (
            all_params[model]["model_class"] == "cq_parameters_smd_generic_rectangular"
        ):
            cqm = cq_parameters_smd_generic_rectangular

            # Load the appropriate colors
            body_color = shaderColors.named_colors[
                all_params[model]["body_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            body = cqm.make_body(all_params[model])
            pins = cqm.make_pins(all_params[model])

            component.add(
                body,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(body)
            parts.append(pins)
            colors.append(all_params[model]["body_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        elif all_params[model]["model_class"] == "cq_parameters_murata_PKMCS0909E4000":
            cqm = cq_parameters_murata_PKMCS0909E4000()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])

            # Build the assembly
            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        elif all_params[model]["model_class"] == "cq_parameters_CUI_CST_931RP_A":
            cqm = cq_parameters_CUI_CST_931RP_A()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])

            # Build the assembly
            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        elif all_params[model]["model_class"] == "cq_parameters_kingstate_KCG0601":
            cqm = cq_parameters_kingstate_KCG0601()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            body_color = shaderColors.named_colors[
                all_params[model]["body_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_top(all_params[model])
            case = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])
            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                case,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(case)
            parts.append(pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["body_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        elif (
            all_params[model]["model_class"] == "cq_parameters_EMB84Q_RO_SMT_0825_S_4_R"
        ):
            cqm = cq_parameters_EMB84Q_RO_SMT_0825_S_4_R()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])

            # Build the assembly
            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        elif (
            all_params[model]["model_class"]
            == "cq_parameters_ProjectsUnlimited_AI_4228_TWT_R"
        ):
            cqm = cq_parameters_ProjectsUnlimited_AI_4228_TWT_R()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            body_color = shaderColors.named_colors[
                all_params[model]["body_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_top(all_params[model])
            case = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])
            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                case,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(case)
            parts.append(pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["body_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        elif all_params[model]["model_class"] == "cq_parameters_ProSignal_ABI_XXX_RC":
            cqm = cq_parameters_ProSignal_ABI_XXX_RC()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])

            # Build the assembly
            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        elif (
            all_params[model]["model_class"]
            == "cq_parameters_StarMicronics_HMB_06_HMB_12"
        ):
            cqm = cq_parameters_StarMicronics_HMB_06_HMB_12()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])

            # Build the assembly
            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        elif all_params[model]["model_class"] == "cq_parameters_TDK_PS1240P02BT":
            cqm = cq_parameters_TDK_PS1240P02BT()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            body_color = shaderColors.named_colors[
                all_params[model]["body_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_top(all_params[model])
            case = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])
            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                case,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(case)
            parts.append(pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["body_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        # cq_parameters_PUI_AI_1440_TWT_24V_2_R
        elif (
            all_params[model]["model_class"] == "cq_parameters_PUI_AI_1440_TWT_24V_2_R"
        ):
            cqm = cq_parameters_PUI_AI_1440_TWT_24V_2_R()

            # Load the appropriate colors
            case_top_color = shaderColors.named_colors[
                all_params[model]["case_top_color_key"]
            ].getDiffuseFloat()
            body_color = shaderColors.named_colors[
                all_params[model]["body_color_key"]
            ].getDiffuseFloat()
            pins_color = shaderColors.named_colors[
                all_params[model]["pins_color_key"]
            ].getDiffuseFloat()

            # Generate the models
            case_top = cqm.make_top(all_params[model])
            case = cqm.make_case(all_params[model])
            pins = cqm.make_pins(all_params[model])
            component.add(
                case_top,
                color=cq_color_correct.Color(
                    case_top_color[0], case_top_color[1], case_top_color[2]
                ),
            )
            component.add(
                case,
                color=cq_color_correct.Color(
                    body_color[0], body_color[1], body_color[2]
                ),
            )
            component.add(
                pins,
                color=cq_color_correct.Color(
                    pins_color[0], pins_color[1], pins_color[2]
                ),
            )

            # Save information for VRML export
            parts.append(case_top)
            parts.append(case)
            parts.append(pins)
            colors.append(all_params[model]["case_top_color_key"])
            colors.append(all_params[model]["body_color_key"])
            colors.append(all_params[model]["pins_color_key"])
        else:
            print("ERROR: No match found for the model_class")
            continue

        # Export the assembly to STEP
        export_tools.export_step(component, output_dir, model)

        # Export the assembly to VRML
        if enable_vrml:
            export_VRML(os.path.join(output_dir, model + ".wrl"), parts, colors)
