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

"""Keepout function."""


from kilibs.geom import (
    GeomArc,
    GeomCircle,
    GeomLine,
    GeomRectangle,
    GeomShape,
    GeomShapeClosed,
)
from kilibs.geom.tolerances import MIN_SEGMENT_LENGTH, TOL_MM
from kilibs.geom.tools.intersect import intersect

_keepout_bypass_use = True
"""Stores whether the keepout bypass shall be used or not."""

_keepout_bypass_hits = 0
"""Stores how many times the bypass successfully reduced the computational effort."""

_keepout_bypass_misses = 0
"""Stores how many times the bypass failed to reduce the computational effort."""


def keepout(
    keepout: GeomShapeClosed,
    shape_to_keep_out: GeomShape,
    min_segment_length: float = MIN_SEGMENT_LENGTH,
    tol: float = TOL_MM,
) -> list[GeomShape]:
    r"""Apply a keepout in shape of `keepout` to `shape_to_keep_out`.

    Args:
        keepout: The shape that is used as a keepout.
        shape_to_keep_out: The shape to keep out.
        min_segment_length: The minimum length of a segment. If a segment resulting
            from the cut operation is shorter than `min_segment_length`, it is
            omitted from the results.
        tol: Tolerance used to dertemine if the two points are equal.

    Returns:
        If `shape_to_keep_out` is fully outside of `keepout`, then a list containing
        `shape_to_keep_out` is returned. If `shape_to_keep_out` is fully inside of
        `keepout`, then an empty list is returned. Otherwise, `shape_to_keep_out` is
        decomposed to its atomic shapes and a list containing the parts of the
        atomic shapes that are not inside the keepout is returned.

    Example:
        When `keepout()` is called from a rectangle on these three lines:

    .. aafig::
        +--------------+
        |   -----(A)   |
      --+--------------+---(B)
        |              |   -----(C)
        +--------------+

    The result would be:

    .. aafig::
        +--------------+
        |              |
      --+              +---(B)
        |              |   -----(C)
        +--------------+
    """
    # For the keepout() operation we only need shape 1 to be cut:

    # Check if there are obvious bypasses to accelerate the keepout operation:
    global _keepout_bypass_use
    if _keepout_bypass_use:
        ret = _keepout_bypasses(shape_to_keep_out, keepout, tol)
        if ret is not None:
            return ret
    handle = intersect(
        shape1=shape_to_keep_out,
        shape2=keepout,
        strict_intersection=True,
        cut_also_shape_2=False,
        min_segment_length=min_segment_length,
        tol=tol,
    )
    if handle.number_cuts_performed[0] == 0 and not handle.intersections:
        if handle.atoms_inside_other_shape[0][0] is False:
            handle.kept_out_shapes = [handle.shape[0]]
        else:
            handle.kept_out_shapes = []
    else:
        for i, inside in enumerate(handle.atoms_inside_other_shape[0]):
            if not inside:
                handle.kept_out_shapes.append(handle.atoms[0][i])
    return handle.kept_out_shapes


def _keepout_bypasses(
    shape_to_keep_out: GeomShape,
    keepout: GeomShape,
    tol: float = TOL_MM,
) -> list[GeomShape] | None:
    """Simple checks that accelerate the keepout testing.

    Returns:
        `None` if the accelerated tests could not determine whether the keepout
        impacts the other shape or not, or, if an accelerated test was successful,
        then the shape that's kept out is returned.
    """
    global _keepout_bypass_hits
    global _keepout_bypass_misses
    global _keepout_bypass_use
    if isinstance(keepout, GeomRectangle):
        bb_rect = keepout.bbox()
        if bb_rect.min is None or bb_rect.max is None:
            return [shape_to_keep_out]
        if isinstance(shape_to_keep_out, GeomLine):
            if shape_to_keep_out.start.x < shape_to_keep_out.end.x:
                left = shape_to_keep_out.start.x
                right = shape_to_keep_out.end.x
            else:
                right = shape_to_keep_out.start.x
                left = shape_to_keep_out.end.x
            if shape_to_keep_out.start.y < shape_to_keep_out.end.y:
                top = shape_to_keep_out.start.y
                bottom = shape_to_keep_out.end.y
            else:
                bottom = shape_to_keep_out.start.y
                top = shape_to_keep_out.end.y
            if (
                bb_rect.min.x + tol >= right
                or bb_rect.max.x - tol <= left
                or bb_rect.min.y + tol >= bottom
                or bb_rect.max.y - tol <= top
            ):
                _keepout_bypass_hits += 1
                return [shape_to_keep_out]
        elif isinstance(shape_to_keep_out, GeomArc | GeomCircle):
            radius = shape_to_keep_out.radius
            if (
                bb_rect.min.x + tol >= shape_to_keep_out.center.x + radius
                or bb_rect.max.x - tol <= shape_to_keep_out.center.x - radius
                or bb_rect.min.y + tol >= shape_to_keep_out.center.y + radius
                or bb_rect.max.y - tol <= shape_to_keep_out.center.y - radius
            ):
                _keepout_bypass_hits += 1
                return [shape_to_keep_out]
    _keepout_bypass_misses += 1
    # Turn off the bypass if we see that for this generator it is not useful:
    if (
        _keepout_bypass_misses > 20
        and _keepout_bypass_hits / _keepout_bypass_misses < 2
    ):
        _keepout_bypass_use = False
    return None
