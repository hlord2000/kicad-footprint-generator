#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is derived from a cadquery script for generating QFP models in X3D format
#
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
#
# Dimensions are from Jedec MS-026D document.
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

__title__ = "make GullWings ICs 3D models exported to STEP and VRML"
__author__ = "scripts: maurice and hyOzd; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import glob
import multiprocessing
import multiprocessing.pool
import os
import sys
from pathlib import Path
from typing import Any

import cadquery as cq
import yaml

from _tools import cq_color_correct, export_tools, shaderColors  # type: ignore
from exportVRML.export_part_to_VRML import export_VRML  # type: ignore

from .gw_qfp_soic_ssop_tssop_sot import make_gw

FUSED_AND_COMPRESSED = True


def make_models(
    model_to_build: str | None = None,
    output_dir_prefix: str | None = None,
    enable_vrml: bool = True,
) -> None:
    """
    Main entry point into this generator.
    """

    if output_dir_prefix is None:
        print("ERROR: An output directory must be provided.")
        return

    # model_to_build can be 'all', or a specific model that could be in any yaml file.
    # In either case we have to load all the model files to memory. This method could
    # be optimized in the future.

    gullwing_path = os.path.dirname(os.path.realpath(__file__))
    all_yaml_files = glob.glob(f"{gullwing_path}/../../data/Gullwing/*.yaml")

    if not all_yaml_files:
        print("No YAML files found to process.")
        return

    all_model_definitions: dict[str, Any] = {}
    for yaml_file in all_yaml_files:
        file_path = Path(yaml_file)
        with open(file_path, "r") as stream:
            all_model_definitions.update(yaml.safe_load(stream))  # type: ignore

    models_to_build: dict[str, Any] = {}
    if model_to_build == "all" or model_to_build == None:
        models_to_build = all_model_definitions
    else:
        models_to_build[model_to_build] = all_model_definitions[model_to_build]

    # for idx, (model_name, model_params) in enumerate(models_to_build.items()):
    #     make_single_gullwing_model(
    #             output_dir_prefix,
    #             model_name,
    #             model_params,
    #             enable_vrml,
    #         )

    # Always use maximum number of processes
    number_of_models = len(models_to_build)
    number_of_processes = os.cpu_count()
    print(
        f"Creating {number_of_models} threads (one per model) and executing them "
        f"in {number_of_processes} asynchronous processes.",
        flush=True,
    )
    with multiprocessing.Pool(processes=number_of_processes) as pool:
        async_results: list[multiprocessing.pool.AsyncResult[None]] = []
        for idx, (model_name, model_params) in enumerate(models_to_build.items()):
            str_display = (
                f"    => Executing thread {idx+1}/{number_of_models}: "
                f"'{model_name}' from library 'Gullwing'"
            )
            async_result = pool.apply_async(
                make_single_gullwing_model,
                args=(
                    output_dir_prefix,
                    model_name,
                    model_params,
                    enable_vrml,
                    str_display,
                ),
            )
            async_results.append(async_result)
        for async_result in async_results:
            try:
                async_result.get()
            except Exception as e:
                print(f"An error occurred in a subprocess: {e}", file=sys.stderr)
        pool.close()
        pool.join()


def make_single_gullwing_model(
    output_dir_prefix: str,
    model_name: str,
    model_params: dict[str, Any],
    enable_vrml: bool,
    str_display: str,
) -> None:
    print(str_display, flush=True)

    output_dir = os.path.join(output_dir_prefix, model_params["library"] + ".3dshapes")
    # Load the appropriate colors
    rgb_body = shaderColors.named_colors["black body"].getDiffuseFloat()
    rbg_pin = shaderColors.named_colors["metal grey pins"].getDiffuseFloat()
    rgb_mark = shaderColors.named_colors["light brown label"].getDiffuseFloat()

    body_color = cq_color_correct.Color(rgb_body[0], rgb_body[1], rgb_body[2])
    pin_color = cq_color_correct.Color(rbg_pin[0], rbg_pin[1], rbg_pin[2])
    mark_color = cq_color_correct.Color(rgb_mark[0], rgb_mark[1], rgb_mark[2])

    # Make the parts of the model
    (body, pins, epad, mark) = make_gw(model_params)

    # Used to wrap all the parts into an assembly
    component = cq.Assembly()

    # Add the parts to the assembly
    component.add(body, color=body_color)  # type: ignore
    component.add(pins, color=pin_color)  # type: ignore
    if mark:
        component.add(mark, color=mark_color)  # type: ignore
    if epad:
        component.add(epad, color=pin_color)  # type: ignore

    # Create the output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Export the assembly to STEP
    component.name = model_name

    if not FUSED_AND_COMPRESSED:
        component.save(  # type: ignore
            os.path.join(output_dir, model_name + ".step"),
            cq.exporters.ExportTypes.STEP,
            mode=cq.exporters.assembly.ExportModes.DEFAULT,  # type: ignore
            write_pcurves=False,
        )
    else:
        component.save(  # type: ignore
            os.path.join(output_dir, model_name + ".step"),
            cq.exporters.ExportTypes.STEP,
            mode=cq.exporters.assembly.ExportModes.FUSED,  # type: ignore
            write_pcurves=False,
        )
        # Check for a proper union
        export_tools.check_step_export_union(component, output_dir, model_name)

        # Do STEP post-processing
        export_tools.postprocess_step(component, output_dir, model_name)

        # Export the assembly to VRML
        if enable_vrml:
            components = [body, pins]
            colors = ["black body", "metal grey pins"]
            if epad:
                components.append(epad)
                colors.append("metal grey pins")
            if mark:
                components.append(mark)
                colors.append("light brown label")
            export_VRML(
                os.path.join(output_dir, model_name + ".wrl"),
                components,
                colors,
            )

        # Update the license
        from _tools import add_license  # type: ignore

        add_license.addLicenseToStep(  # type: ignore
            output_dir,
            model_name + ".step",
            add_license.LIST_int_license,
            add_license.STR_int_licAuthor,
            add_license.STR_int_licEmail,
            add_license.STR_int_licOrgSys,
            add_license.STR_int_licPreProc,
        )
