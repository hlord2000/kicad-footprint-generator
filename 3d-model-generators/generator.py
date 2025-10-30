#!/usr/bin/env python3

import argparse
import concurrent.futures as cf
import datetime
import importlib
import os
import sys

from OCP.Message import Message, Message_Gravity

from _tools import export_tools, parameters


def get_package_names(dir_name):
    try:
        all_params = parameters.load_parameters(dir_name)
        return all_params.keys()
    except:
        return None


# TODO: Add log file for warnings and error messages
def main():
    parser = argparse.ArgumentParser(
        description="Controls the generation and export of KiCAD 3D models."
    )
    # Older version used --output_dir, stay backward compatible with them
    parser.add_argument(
        "-o",
        "--output-dir",
        "--output_dir",
        required=True,
        help="Sets the directory to write the generated models to.",
    )
    parser.add_argument(
        "-l",
        "--library",
        help="Selects a specific library to generate models for.",
    )
    parser.add_argument(
        "-p",
        "--package",
        action="append",
        help="Selects a specific package configuration to generate models for.",
    )
    parser.add_argument("-v", "--verbose", help="Show OCCT output", action="store_true")
    parser.add_argument(
        "--enable-vrml",
        default="True",
        help="Sets whether or not to export the VRML files in addition to the STEP files.",
    )
    parser.add_argument(
        "--dry-run",
        help="Do not run the generators, only print the list of parts and libraries.",
        action="store_true",
    )
    parser.add_argument(
        "-t",
        "--threads",
        default=1,
        help="Parallelize library generation, specify number of processes to generate libraries. Example: -t 2 will use two processes to generate libraries.",
        type=int,
    )
    parser.add_argument(
        "--one-part-per-generator",
        help="Generate only a single part per generator (the first one in the YAML file).",
        action="store_true",
    )
    args = parser.parse_args()

    # This is an odd CLI, but it's always been like this
    args.enable_vrml = args.enable_vrml.lower() == "true"

    # Error out if only package has been specified without a library
    if args.library is None and args.package:
        print("You need to specify -l/--library along with -p/--package.")
        sys.exit(1)

    # Helps filter out directories that should not be processed
    filter_dirs = ["_screenshots", "_tools", ".git", "Example", "WIP", "exportVRML"]

    # Get a list of the package directories so that we can work through them
    dir_list = [
        dir_name
        for dir_name in os.listdir(".")
        if os.path.isdir(dir_name)
        and dir_name not in filter_dirs
        and os.path.exists(os.path.join(dir_name, "__init__.py"))
    ]
    dir_list.sort()
    if not args.verbose:
        Message.DefaultMessenger_s().Printers().First().SetTraceLevel(
            Message_Gravity.Message_Warning
        )

    if args.library is None:
        # If no library is specified, generate all available ones
        print(f"Found {len(dir_list)} generators to run.")
        libraries_to_generate = dir_list
    else:
        # If the user requests that a specific library be generated,
        # only generate that
        library = os.path.normpath(args.library)
        if not library in dir_list:
            print(f"{library} is not a valid library")
            sys.exit(1)
        libraries_to_generate = [library]

    start_time = datetime.datetime.now()
    if args.threads == 1 and not args.one_part_per_generator:
        for index, library in enumerate(libraries_to_generate):
            generate_library(library, index, len(libraries_to_generate), args)
    else:
        if args.threads == 0:
            threads = os.cpu_count()
        else:
            threads = args.threads
        with cf.ProcessPoolExecutor(threads) as executor:
            for index, library in enumerate(libraries_to_generate):
                executor.submit(
                    generate_library,
                    library,
                    index,
                    len(libraries_to_generate),
                    args,
                )

    stop_time = datetime.datetime.now()
    print("Generation complete. Execution time:", stop_time - start_time)


def generate_library(library, index, libraries_count, args):
    known_packages = get_package_names(library)
    # Import the current library to run the generator
    mod = importlib.import_module(library + ".main_generator")

    packages_to_generate = []

    # Some libraries like Inductors_SMD don't list their parts, so they need special handling
    if known_packages is None:
        if not args.package:
            print(
                f"Generating library {index+1}/{libraries_count}: {library} with unknown number of entries"
            )
            packages_to_generate = ["all"]

        elif args.library is not None:
            packages_to_generate += args.package
    else:
        # Generate all or a specific package based on the command line arguments
        if not args.package:
            packages_to_generate = known_packages
        else:

            for package in args.package:
                # If the part exists in that library, generate it, otherwise error out
                if package in known_packages:
                    packages_to_generate.append(package)
                else:
                    print(f"Part '{package}' does not exist in library {library}")
                    sys.exit(1)

    if args.one_part_per_generator:
        packages_to_generate = [list(packages_to_generate)[0]]
        export_tools.make_only_one_part_per_process()

    if len(packages_to_generate) > 1:
        print(f"Generating library {index+1}/{libraries_count}: {library}")

    for package_index, package in enumerate(packages_to_generate):
        print(
            f"    => Generating part {package_index+1}/{len(packages_to_generate)}: '{package}' from library '{library}'"
        )
        if not args.dry_run:
            mod.make_models(package, args.output_dir, args.enable_vrml)


if __name__ == "__main__":
    main()
