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


from dataclasses import dataclass

from generators.tools.spec.spec_generator import DD, get_file_name_ids_specs


@dataclass
class SpecIdsDiff:
    """A dataclass containing the result of a spec diff."""

    new_ids: list[str]
    """The list of IDs of the specs that are new."""
    deleted_ids: list[str]
    """The list of IDs of the specs that are deleted."""
    modified_ids: list[str]
    """The list of IDs of the specs that are modified."""
    identical_ids: list[str]
    """The list of IDs of the specs that are identical."""


def compare_specs(
    ids_specs_new: list[tuple[str, DD]],
    ids_specs_old: list[tuple[str, DD]],
) -> SpecIdsDiff:
    """Compare two lists of ID-spec pairs.

    Args:
        ids_specs_new: The new list of ID-spec pairs.
        ids_specs_old: The old list of ID-spec pairs.

    Returns:
        A `SpecIdsDiff` that contains the IDs of the new, deleted, modified and
        identical specs.
    """
    ids_old: list[str] = [id_spec_new[0] for id_spec_new in ids_specs_old]
    specs_old: list[DD] = [id_spec_new[1] for id_spec_new in ids_specs_old]
    new_ids: list[str] = []
    deleted_ids: list[str] = []
    modified_ids: list[str] = []
    identical_ids: list[str] = []
    for id_new, spec_new in ids_specs_new:
        try:
            idx = ids_old.index(id_new)
            spec_old = specs_old[idx]
            if spec_new == spec_old:
                identical_ids.append(id_new)
            else:
                modified_ids.append(id_new)
            del ids_old[idx]
            del specs_old[idx]
        except ValueError:
            new_ids.append(id_new)
    deleted_ids = ids_old
    return SpecIdsDiff(new_ids, deleted_ids, modified_ids, identical_ids)


def compare_specs_in_files(file_new: str, file_old: str) -> SpecIdsDiff:
    """Compare the specs of two files.

    Args:
        file_new: The path of the file with the new specs.
        file_old: The path of the file with the old specs.

    Returns:
        A `SpecIdsDiff` that contains the IDs of the new, deleted, modified and
        identical specs.
    """
    _, ids_specs_old = get_file_name_ids_specs(file_name=file_old)[0]
    _, ids_specs_new = get_file_name_ids_specs(file_name=file_new)[0]
    return compare_specs(ids_specs_new, ids_specs_old)
