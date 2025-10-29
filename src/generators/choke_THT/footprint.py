#!/usr/bin/env python

from KicadModTree import *  # NOQA
from scripts.tools.drawing_tools import *
from scripts.tools.footprint_scripts_resistorlike import *
from scripts.tools.migrate_to_yaml import *
from typing import Any

import argparse

from scripts.tools.footprint_generator import FootprintGenerator

class ChokesTHTGenerator(FootprintGenerator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def generateFootprint(
        self, spec: dict[str, Any], pkg_id: str, header_info: dict[str, Any]
    ) -> None:
        if pkg_id == 'base':
            # Ignore base from which the entries derive
            return
        
        # Extract function to run (such as 'makeResistorRadial')
        if not spec.get("func"):
            raise ValueError(f"No func specified for {pkg_id}: {spec}")
        func = globals().get(spec["func"])
        if not func:
            raise ValueError(f"Function {spec['func']} not found for {pkg_id}: {spec}")
        
        # Remove invalid parameters
        params = spec.copy()
        del params["func"]
        # Generate !
        func(**params)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="use config .yaml files to create socket strips."
    )
    parser.add_argument(
        "files",
        metavar="file",
        type=str,
        nargs="*",
        help="list of files holding information about what devices should be created.",
    )
    args = FootprintGenerator.add_standard_arguments(parser)

    FootprintGenerator.run_on_files(ChokesTHTGenerator, args)
