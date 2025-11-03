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
import os
from pathlib import Path

import cadquery as cq
import yaml

from _tools import export_tools  # type: ignore
from exportVRML.export_part_to_VRML import export_VRML  # type: ignore

from kilibs.declarative_defs.packages.gullwing_configuration import (  # type: ignore
    GullwingConfiguration,
)
from kilibs.util import dict_tools  # type: ignore

from .gullwing import make_gw

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
    all_yaml_files = glob.glob(f"{gullwing_path}/../../data/gullwing/*.yaml")

    if not all_yaml_files:
        print("No YAML files found to process.")
        return

    # We load the configuration file (of the footprint generators):
    with open("../scripts/Packages/package_config_KLCv3.yaml", "r") as config_stream:
        try:
            config = yaml.safe_load(config_stream)
        except yaml.YAMLError as exc:
            print(exc)
            raise FileNotFoundError("Could not load 'package_config_KLCv3.yaml'")

    gw_configs: list[GullwingConfiguration] = []
    for yaml_file in all_yaml_files:
        file_path = Path(yaml_file)
        with open(file_path, "r") as stream:
            yaml_dict = yaml.safe_load(stream)
            dict_tools.dictInherit(yaml_dict)
            header = yaml_dict.get("FileHeader")
            for key, value in yaml_dict.items():
                if key != "FileHeader":
                    if (
                        model_to_build == key
                        or model_to_build == "all"
                        or model_to_build == None
                    ):
                        gwc = GullwingConfiguration(value, header, key, config)
                        if gwc.has_3d_data:
                            gw_configs.append(gwc)

    for spec in gw_configs:
        make_single_gullwing_model(output_dir_prefix, spec, enable_vrml)


def make_single_gullwing_model(
    output_dir_prefix: str,
    gwc: GullwingConfiguration,
    enable_vrml: bool,
) -> None:
    print(gwc.model_name, flush=True)

    # Make the parts of the model
    (body, pins, epad, mark) = make_gw(gwc)

    parts: list[cq.Workplane] = [body, pins]
    color_names: list[str] = ["black body", "metal grey pins"]
    if epad:
        parts.append(epad)
        color_names.append("metal grey pins")
    if mark:
        parts.append(mark)
        color_names.append("light brown label")

    export_tools.export(
        root_output_dir=output_dir_prefix,
        lib_name=gwc.lib_name,
        model_name=gwc.model_name,
        parts=parts,
        color_names=color_names,
        export_as_vrml=enable_vrml,
    )
