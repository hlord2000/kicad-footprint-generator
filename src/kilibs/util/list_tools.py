# kilibs is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# kilibs is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with kilibs.
# If not, see < http://www.gnu.org/licenses/ >.
#
# (C) The KiCad Librarian Team

"""List tools."""

from collections.abc import Sequence
from fnmatch import fnmatch
from typing import TypeVar

SeqVar = TypeVar("SeqVar")
"""Type variable for sequences."""


def list_filter(
    names: list[str], include_globs: Sequence[str], exclude_globs: Sequence[str]
) -> list[str]:
    """Filter a list of names based on explicit inclusion and exclusion globs.

    Args:
        names: The complete list of names to filter.
        include_globs: Names (or globs) to explicitly include. If non-empty, only these
            items (if present in `names`) will be returned.
        exclude_globs: Names (or globs) to explicitly exclude from the final result.

    Returns:
        A list of the filtered names.
    """
    if include_globs:
        inc = set([n for n in names for g in include_globs if fnmatch(n, g)])
    else:
        inc = set(names)
    if exclude_globs:
        exc = set([n for n in names for g in exclude_globs if fnmatch(n, g)])
    else:
        exc: set[str] = set()
    return list(inc - exc)


def list_filter_idx(
    sequences: list[SeqVar],
    idx: int,
    include_globs: Sequence[str],
    exclude_globs: Sequence[str],
) -> list[SeqVar]:
    """Filter a list of sequences based on explicit inclusion and exclusion globs.

    Args:
        sequences: The complete list of sequences to filter.
        idx: The index of the item in the sequences to match against the globs.
        include_globs: Names (or globs) to explicitly include. If non-empty, only these
            items (if present in `sequences`) will be returned.
        exclude_globs: Names (or globs) to explicitly exclude from the final result.

    Returns:
        A list of the filtered sequences.
    """
    if include_globs:
        inc = set([s for s in sequences for g in include_globs if fnmatch(s[idx], g)])
    else:
        inc = set(sequences)
    if exclude_globs:
        exc = set([s for s in sequences for g in exclude_globs if fnmatch(s[idx], g)])
    else:
        exc: set[SeqVar] = set()
    return list(inc - exc)


def list_filter_attr(
    objects: list[SeqVar],
    attr_name: str,
    include_globs: Sequence[str],
    exclude_globs: Sequence[str],
) -> list[SeqVar]:
    """Filter a list of objects based on explicit inclusion and exclusion globs.

    Args:
        objects: The complete list of objects to filter.
        attr_name: The name of the attribute in the objects to match against the globs.
        include_globs: Names (or globs) to explicitly include. If non-empty, only these
            items (if present in `objects`) will be returned.
        exclude_globs: Names (or globs) to explicitly exclude from the final result.

    Returns:
        A list of the filtered objects.
    """
    if include_globs:
        inc = set(
            [
                s
                for s in objects
                for g in include_globs
                if fnmatch(getattr(s, attr_name), g)
            ]
        )
    else:
        inc = set(objects)
    if exclude_globs:
        exc = set(
            [
                s
                for s in objects
                for g in exclude_globs
                if fnmatch(getattr(s, attr_name), g)
            ]
        )
    else:
        exc: set[SeqVar] = set()
    return list(inc - exc)
