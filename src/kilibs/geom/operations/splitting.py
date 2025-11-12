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

"""Cut function."""

from kilibs.geom import GeomShape
from kilibs.geom.tolerances import MIN_SEGMENT_LENGTH, TOL_MM
from kilibs.geom.tools.intersect import intersect


def cut(
    cutting_shape: GeomShape,
    shape_to_cut: GeomShape,
    min_segment_length: float = MIN_SEGMENT_LENGTH,
    tol: float = TOL_MM,
) -> list[GeomShape]:
    """Cut `shape_to_cut` with `cutting_shape`.

    Args:
        cutting_shape: The shape that cuts.
        shape_to_cut: The shape that is to be cut.
        strict_intersection: If `True`, then intersection points resulting from
            shapes that are tangent to another or from segments that have their
            beginning or their ending on the outline of the other shape are omitted
            from the results. If `False` then those points are included.
        min_segment_length: The minimum length of a segment. If a segment resulting
            from the cut operation is shorter than `min_segment_length`, it is
            omitted from the results.
        tol: Tolerance used to dertemine if the two points are equal.
    Returns:
        A list containing the shapes that are created by the cut, or containing the
        uncut shape if there are no intersection points between the `cutting_shape`
        and the `shape_to_cut`.
        If the shape has been cut, the resulting line and arc segments are returned
        sorted by their proximity to the starting point of the segment.
    """
    # For the cut() operation we only need shape 1 to be cut:
    handle = intersect(
        shape1=shape_to_cut,
        shape2=cutting_shape,
        strict_intersection=True,
        cut_also_shape_2=False,
        min_segment_length=min_segment_length,
        tol=tol,
    )
    if handle.intersections:
        return list(handle.atoms[0])
    else:
        return [shape_to_cut]
