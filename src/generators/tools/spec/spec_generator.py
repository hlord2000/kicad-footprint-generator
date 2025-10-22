# generators is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# generators is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# generators. If not, see < http://www.gnu.org/licenses/ >.
#
# (C) The KiCad Librarian Team

from __future__ import annotations

import os
from typing import Any

import yaml

from kilibs.config.cli_args import CLI_ARGS
from kilibs.config.paths import DATA_PATH
from kilibs.util import dict_tools, list_filter, list_filter_idx

from .base_spec import BaseSpec, TypeSpec


def get_spec_file_names(
    generator_name: str, globs: list[str] = ["*.yaml"]
) -> list[str]:
    """Get the list of the names of the YAML files containing the specs for a given
    generator.

    Args:
        globs: The list of the globs the file names need to match with.
        generator_name: The generator name.

    Returns:
        The list of the file names.
    """
    generator_path = DATA_PATH / generator_name
    # Workaround for legacy generators: We ignore "cq_parameters.yaml". Those files are
    # only used by `create_specs()` in `legacy_model_spec.py`:
    cq_file = generator_path / "cq_parameters.yaml"
    file_names = [
        str(f) for glob in globs for f in generator_path.glob(glob) if f != cq_file
    ]
    if CLI_ARGS.category or CLI_ARGS.category_exclude:
        return list_filter(file_names, CLI_ARGS.category, CLI_ARGS.category_exclude)
    else:
        return file_names


def get_spec_dicts(
    generator_name: str | None = None, file_name: str | None = None
) -> list[tuple[str, dict[str, Any]]]:
    """Get the list of the contents of the YAML files for a given generator.

    Args:
        generator_name: The generator name. If `None`, `file_name` must be provided.
        file_name: Optional name of the file to load the specs from. If `None`, then
            `generator_name` must be provided. In that case all specs of that generator
            are loaded. If `file_name` is a relative path, then `generator_name` must
            be provided.

    Returns:
        A list of tuples, where each tuple represents one YAML file
            * YAML file name: str
            * YAML file content: dict[str, Any]).
    """
    specs_raw: list[tuple[str, dict[str, Any]]] = []
    if file_name is None:
        if generator_name is not None:
            file_names = get_spec_file_names(generator_name)
        else:
            raise ValueError("Either `file_name` or `generator_name` must be provided.")
    else:
        if generator_name is None or os.path.isabs(file_name):
            file_names = [file_name]
        else:
            file_names = [str(DATA_PATH / generator_name / file_name)]
    for file_name in file_names:
        with open(file_name, "r", encoding="utf-8") as stream:
            if yaml.__with_libyaml__:
                loader = yaml.CSafeLoader
            else:
                loader = yaml.SafeLoader  # type: ignore
            yaml_dict = yaml.load(stream, Loader=loader)
            dict_tools.dictInherit(yaml_dict)
            specs_raw.append((file_name, yaml_dict))
    return specs_raw


def get_headers_ids_specs(
    generator_name: str | None = None, file_name: str | None = None
) -> list[tuple[str, dict[str, Any], list[tuple[str, dict[str, Any]]]]]:
    """Extract the file names, headers, IDs, and specs of all the spec files.

    Args:
        generator_name: The generator name. If `None`, `file_name` must be provided.
        file_name: Optional name of the file to load the specs from. If `None`, then
            `generator_name` must be provided. In that case all specs of that generator
            are loaded.

    Returns:
        A list of tuples where each tuple represents one YAML file with:
            * YAML file name: str
            * YAML file header: dict[str, Any]
            * List of entries with:
                * ID: str
                * entry: dict[str, Any]
    """
    ret: list[tuple[str, dict[str, Any], list[tuple[str, dict[str, Any]]]]] = []
    for file_name, raw_specs in get_spec_dicts(generator_name, file_name):
        if "FileHeader" in raw_specs.keys():
            header: dict[str, Any] = raw_specs["FileHeader"]
        else:
            header = {}
        ids_specs: list[tuple[str, dict[str, Any]]] = []
        for id, spec in raw_specs.items():
            if id == "FileHeader" or id.startswith("defaults"):
                continue
            else:
                ids_specs.append((id, spec))
        if CLI_ARGS.part or CLI_ARGS.part_exclude:
            ids_specs = list_filter_idx(
                ids_specs, 0, CLI_ARGS.part, CLI_ARGS.part_exclude
            )
        ret.append((file_name, header, ids_specs))
    return ret


def get_specs(
    generator_name: str | None = None,
    file_name: str | None = None,
    spec_type: type[TypeSpec] = BaseSpec,
) -> list[TypeSpec]:
    """Get the list of the specs for a given generator (from its YAML files).

    Args:
        generator_name: The generator name. If `None`, `file_name` must be provided.
        file_name: Optional name of the file to load the specs from. If `None`, then
            `generator_name` must be provided. In that case all specs of that generator
            are loaded.
        spec_type: The class of the specs that shall be created.

    Returns:
        The unified list of the specs derived from all the generator's YAML files.
    """
    specs: list[TypeSpec] = []
    make_fps = True if CLI_ARGS.output_dir_footprints else False
    make_mods = True if CLI_ARGS.output_dir_models else False
    for file_name, header, ids_specs in get_headers_ids_specs(
        generator_name, file_name
    ):
        for id, spec in ids_specs:
            spec = spec_type(id, spec, header, file_name)
            if make_fps and spec.has_fp_data or make_mods and spec.has_3d_data:
                specs.append(spec)
    return specs


def create_specs(file_name: str, generator_name: str) -> list[BaseSpec]:
    """Default implementation for `create_specs`.

    Args:
        file_name: The name of the specs file to create the specs from.
        generator_name: The name of the generator to create the specs for.

    Return:
        The created specs.
    """
    from .spec_registry import get_spec_class

    spec_class = get_spec_class(generator_name)

    if spec_class is None:
        raise ModuleNotFoundError(
            f"No class in {generator_name}/spec.py was decorated with `@register_spec`."
        )
    return get_specs(None, file_name, spec_class)
