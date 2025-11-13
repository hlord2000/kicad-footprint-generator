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
# (C) 2016 by Thomas Pointhuber, <thomas.pointhuber@gmx.at>
# (C) The KiCad Librarian Team

"""Class definition for the translation node."""

from KicadModTree.nodes.Node import Node
from kilibs.geom.bounding_box import BoundingBox
from kilibs.geom.vector import Vector2D


class Translation(Node):
    """A translation that is applied to every child node."""

    def __init__(self, x: float | Vector2D, y: float = 0.0) -> None:
        """Create a translation node.

        Args:
            x: The distance in mm in the x-direction.
            y: The distance in mm in the y-direction.
        """

        # Instance attributes:
        self.offset: Vector2D
        """The direction and distance in mm of the translation."""

        Node.__init__(self)
        if isinstance(x, Vector2D):
            self.offset = x
        else:
            self.offset = Vector2D.from_floats(x, y)

    def get_flattened_nodes(self) -> list[Node]:
        """Return a list of the translated copies of all child nodes from the node tree.

        Returns:
            The list of a translated copy of all child nodes.
        """
        transformed_nodes: list[Node] = []
        for child in self._children:
            nodes = child.get_flattened_nodes()
            for n in nodes:
                transformed_nodes.append(n.translated(vector=self.offset))
        return transformed_nodes

    def bbox(self) -> BoundingBox:
        """Return the translated bounding box of every child node."""
        bbox = BoundingBox()
        for child in self._children:
            child_bbox = child.bbox()
            bbox.include_bbox(child_bbox)
        if bbox.min is not None and bbox.max is not None:
            # translate the bounding box
            bbox.min += self.offset
            bbox.max += self.offset
            return bbox
        else:
            return bbox

    def __repr__(self) -> str:
        """The string representation of the translation."""
        return f"Translation(offset={self.offset})"
