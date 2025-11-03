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

__title__ = "make Altech connector 3D models exported to STEP and VRML"
__author__ = "scripts: Stefan; models: see cq_model files; update: jmwright"
__Comment__ = """This generator loads cadquery model scripts and generates step/wrl files for the official kicad library."""

___ver___ = "2.0.0"

import cadquery as cq

from _tools import export_tools, parameters

from .cq_models.conn_phoenix_mc import generate_part as generate_part_mc
from .cq_models.conn_phoenix_mc import seriesParams as series_params_mc
from .cq_models.conn_phoenix_mkds import (
    make_case_MKDS_1_5_10_5_08,
    make_pins_MKDS_1_5_10_5_08,
)
from .cq_models.conn_phoenix_mstb import generate_part as generate_part_mstb
from .cq_models.conn_phoenix_mstb import seriesParams as series_params_mstb


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    all_params = parameters.load_parameters("phoenix_contact")

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

        # Convert the number of pins to an array of one if there is only one pin
        num_pins_list = (
            [all_params[model]["num_pins"]]
            if type(all_params[model]["num_pins"]).__name__ == "int"
            else all_params[model]["num_pins"]
        )
        for num_pins in num_pins_list:
            insert = None
            mount_screw = None

            if model == "AK300" or model == "MKDS_1_5":
                # Make the parts of the model
                body = make_case_MKDS_1_5_10_5_08(all_params[model], num_pins)
                pins = make_pins_MKDS_1_5_10_5_08(all_params[model], num_pins)
                body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
                pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])

            elif model.startswith("MC"):

                (pins, body, insert, mount_screw, _, _) = generate_part_mc(
                    all_params[model], num_pins
                )

                body = body.rotate(
                    (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
                ).translate((0, -3.0, 3.0))
                pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
                if not all_params[model]["angled"]:
                    pins = pins.translate((0, 0, 3.0))
                if insert != None:
                    insert = insert.rotate(
                        (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
                    ).translate((0, -3.0, 3.0))
                if mount_screw != None:
                    if all_params[model]["angled"]:
                        mount_screw = mount_screw.rotate(
                            (0, 0, 0), (1, 0, 0), -90
                        ).translate(
                            (
                                0,
                                -series_params_mc.mount_screw_head_height
                                - series_params_mc.body_height / 2.0,
                                series_params_mc.thread_insert_r,
                            )
                        )
                    else:
                        mount_screw = mount_screw.rotate(
                            (1, 0, 0), (0, 0, 0), 180
                        ).translate(
                            (
                                0,
                                series_params_mc.mount_screw_head_height
                                - series_params_mc.body_height / 2.0,
                                series_params_mc.body_height
                                + series_params_mc.mount_screw_head_height,
                            )
                        )

            elif model.startswith("MSTB") or model.startswith("GMSTB"):

                (pins, body, insert, mount_screw, plug, plug_screws) = (
                    generate_part_mstb(all_params[model], num_pins)
                )
                # print(pins)
                # Rotate and translate parts so they end up in the correct location/orientation
                body = body.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
                if (
                    model.startswith("MSTB") or model.startswith("GMSTB")
                ) and all_params[model]["angled"]:
                    body = body.translate((0, -3.0, 3.0))
                pins = pins.rotate((0, 0, 0), (0, 0, 1), all_params[model]["rotation"])
                if insert != None and all_params[model]["angled"]:
                    insert = insert.rotate(
                        (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
                    ).translate((0, -3.0, 3.0))
                if mount_screw != None:
                    if all_params[model]["angled"]:
                        mount_screw = mount_screw.rotate(
                            (1, 0, 0), (0, 0, 0), 90
                        ).translate(
                            (
                                0,
                                -series_params_mstb.mount_screw_head_height
                                - series_params_mstb.body_height / 2.0,
                                series_params_mstb.thread_r / 2.0,
                            )
                        )
                    else:
                        mount_screw = mount_screw.rotate(
                            (1, 0, 0), (0, 0, 0), 180
                        ).translate(
                            (
                                0,
                                0,
                                series_params_mstb.body_height
                                - series_params_mstb.mount_screw_head_height,
                            )
                        )

            # Assemble the filename
            file_name = all_params[model]["file_name"].format(
                pin_num=num_pins,
                pad_pin_num="0" + str(num_pins) if num_pins < 10 else str(num_pins),
                row_num=1,
                pitch=all_params[model]["pin_pitch"],
                comma_pitch=str(all_params[model]["pin_pitch"]).replace(".", ","),
                pad_pitch=(
                    all_params[model]["pin_pitch"]
                    if len(str(all_params[model]["pin_pitch"]).split(".")[1]) == 2
                    else str(all_params[model]["pin_pitch"]) + "0"
                ),
                prefix=all_params[model]["series_name"].split("-")[0],
                midfix=all_params[model]["series_name"].split("-")[1],
                orientation=(
                    "Horizontal"
                    if "angled" in all_params[model]
                    and all_params[model]["angled"] == True
                    else "Vertical"
                ),
                flanged=(
                    "_ThreadedFlange"
                    if "flanged" in all_params[model]
                    and all_params[model]["flanged"] == True
                    else ""
                ),
                mount_hole=(
                    "_MountHole"
                    if "mount_hole" in all_params[model]
                    and all_params[model]["mount_hole"] == True
                    else ""
                ),
            )

            parts: list[cq.Workplane] = [body, pins]
            color_names: list[str] = [
                all_params[model]["body_color_key"],
                all_params[model]["pin_color_key"],
            ]
            if insert != None:
                parts.append(insert)
                color_names.append(all_params[model]["insert_color_key"])
            if mount_screw != None:
                parts.append(mount_screw)
                color_names.append(all_params[model]["screw_color_key"])

            export_tools.export(
                root_output_dir=output_dir_prefix,
                lib_name=all_params[model]["destination_dir"],
                model_name=file_name,
                parts=parts,
                color_names=color_names,
                export_as_vrml=enable_vrml,
            )
