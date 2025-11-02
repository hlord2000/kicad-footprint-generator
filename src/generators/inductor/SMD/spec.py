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

from pathlib import Path

from .smd_inductor_properties import InductorSeriesProperties
import yaml


def create_specs(file_name: str, generator_name: str) -> list[InductorSeriesProperties]:
    """Create specs for the SMD inductors.

    Args:
        file_name: The name of the specs file to create the specs from.
        generator_name: The name of this generator.

    Returns:
        A list containing all the SMD inductor specifications.
    """
    specs: list[InductorSeriesProperties] = []
    with open(file_name, "r", encoding="utf-8") as stream:
        if yaml.__with_libyaml__:
            loader = yaml.CSafeLoader
        else:
            loader = yaml.SafeLoader  # type: ignore
        yaml_file_content = yaml.load(stream, Loader=loader)
        csv_dir = Path(file_name).parent
        # For each series block in the yaml file, process it
        for series_block in yaml_file_content:
            specs.append(InductorSeriesProperties(series_block, csv_dir))
    return specs
