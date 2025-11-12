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

"""Class definition for the shape node."""

from __future__ import annotations

from typing import Any, Self

from KicadModTree.nodes.Node import Node
from KicadModTree.util import LineStyle
from KicadModTree.util.shape_to_node import shape_to_node
from kilibs.geom import (
    MIN_SEGMENT_LENGTH,
    TOL_MM,
    BoundingBox,
    GeomShape,
    GeomShapeClosed,
    Vector2D,
)


class NodeShape(Node, GeomShape):
    """A node class for shapes."""

    def __init__(
        self,
        layer: str = "F.SilkS",
        width: float | None = None,
        style: LineStyle = LineStyle.SOLID,
        fill: bool = False,
        shape: Self | GeomShape | None = None,
    ) -> None:
        """Create a `NodeShape`.

        Args:
            layer: Layer.
            width: Line width in mm. If `None`, then the standard width for the given
                layer will be used when the serializing the node.
            style: Line style.
            fill: `True` if the rectangle is filled, `False` if only the outline is
                visible. `False` for open shapes.
            shape: Optional shape to copy for the creation of this shape node.
        """

        # Instance attributes:
        self.layer: str
        """The layer on which the node is drawn."""
        self.width: float | None
        """The width of the outline of the shape."""
        self.style: LineStyle
        """The line style used to draw the outline of the shape."""
        self.fill: bool
        """Whether the shape is filled, `False` for open shapes."""

        Node.__init__(self)
        self.layer = layer
        self.width = width
        self.style = style
        self.fill = fill

    def copy(self) -> Self:
        """Creates a copy of itself."""
        if isinstance(self, GeomShapeClosed):
            copy = self.__class__(
                shape=self,
                layer=self.layer,
                width=self.width,
                style=self.style,
                fill=self.fill,
            )
        else:
            copy = self.__class__(
                shape=self,
                layer=self.layer,
                width=self.width,
                style=self.style,
            )
        return copy

    def copy_with(
        self,
        shape: Self | None = None,
        layer: str | None = None,
        width: float | None = None,
        style: object | None = None,
        fill: bool | None = None,
        offset: float | None = None,
    ) -> Self:
        """Creates a copy of itself using the given parameters instead of the original ones.

        Args:
            shape: Use the shape given as parameter instead of the original one.
            layer: Use the layer given as parameter instead of the original one.
            width: Use the width given as parameter instead of the original one.
            style: Use the style given as parameter instead of the original one.
            fill: Use the fill type given as parameter instead of the original one.
            ofsset: inflate/deflate the shape by this amount.
        """
        params: dict[str, Any] = {}
        shape = shape if shape else self
        if layer or hasattr(self, "layer"):
            params.update({"layer": (layer if layer else self.layer)})
        if width or hasattr(self, "width"):
            params.update({"width": (width if width else self.width)})
        if style or hasattr(self, "style"):
            params.update({"style": (style if style else self.style)})
        if fill or hasattr(self, "fill"):
            params.update({"fill": (fill if fill else self.fill)})
        if offset:
            params.update({"offset": offset})
        return self.__class__(shape=shape, **params)

    def translate(self, vector: Vector2D) -> Self:
        """Move the node.

        Args:
            vector: The direction and distance in mm.

        Returns:
            The translated node.
        """
        return super(Node, self).translate(vector=vector)

    def rotate(
        self,
        angle: float,
        origin: Vector2D = Vector2D.zero(),
    ) -> Self:
        """Rotate the node around a given point.

        Args:
            angle: Rotation angle in degrees.
            origin: Coordinates (in mm) of the point around which to rotate.

        Returns:
            The rotated node.
        """
        return super(Node, self).rotate(angle=angle, origin=origin)

    def cut(  # type: ignore
        self,
        shape_to_cut: NodeShape,
        min_segment_length: float = MIN_SEGMENT_LENGTH,
        tol: float = TOL_MM,
    ) -> list[NodeShape]:
        """Cut the node with another node.

        Args:
            shape_to_cut: Node whose shape is cut with the shape of this node.
            min_segment_length: The minimum length of a segment. If a segment resulting
                from the `cut` operation is shorter than `min_segment_length`, it is
                omitted from the results.
            tol: The tolerance in mm that is used to determine if two points are equal.

        Return:
            Return a list of nodes that result from the cut operation.
        """
        shapes = GeomShape.cut(
            self,
            shape_to_cut=shape_to_cut,
            min_segment_length=min_segment_length,
            tol=tol,
        )
        nodes: list[NodeShape] = []
        for shape in shapes:
            node = shape_to_node(
                shape=shape,
                layer=shape_to_cut.layer,
                width=shape_to_cut.width,
                style=shape_to_cut.style,
                fill=shape_to_cut.fill,
            )
            nodes.append(node)
        return nodes

    def keepout(
        self,
        shape_to_keep_out: NodeShape,
        min_segment_length: float = MIN_SEGMENT_LENGTH,
        tol: float = TOL_MM,
    ) -> list[NodeShape]:
        """Treat this node as if it was a keepout and apply it to the node given as
        argument.

        Args:
            shape_to_keep_out: The node that is to be kept out of the keepout.
            min_segment_length: The minimum length of a segment. If a segment resulting
                from the keepout operation is shorter than `min_segment_length`, it is
                omitted from the results.
            tol: The tolerance in mm that is used to determine if two points are equal.

        Returns:
            If `shape_to_keep_out` is fully outside of this closed shape, then a list
            containing `shape_to_keep_out` is returned. If `shape_to_keep_out` is fully
            inside of this closed shape, then an empty list is returned. Otherwise,
            `shape_to_keep_out` is decomposed to its atomic nodes and a list containing
            the parts of the atomic nodes that are not inside the keepout is returned.
        """
        if isinstance(self, GeomShapeClosed):
            shapes = GeomShapeClosed.subtract(
                self,
                shape_to_keep_out=shape_to_keep_out,
                min_segment_length=min_segment_length,
                tol=tol,
            )
            nodes: list[NodeShape] = []
            for shape in shapes:
                if isinstance(shape, NodeShape):
                    return [shape]
                else:
                    node = shape_to_node(
                        shape=shape,
                        layer=shape_to_keep_out.layer,
                        width=shape_to_keep_out.width,
                        style=shape_to_keep_out.style,
                        fill=shape_to_keep_out.fill,
                    )
                    nodes.append(node)
            return nodes
        else:
            return [shape_to_keep_out]

    def bbox(self) -> BoundingBox:
        """Get the bounding box of the node."""
        return super(Node, self).bbox()

    def __repr__(self) -> str:
        """The string representation of the NodeShape."""
        class_name = self.__class__.__name__
        # Start looking for a __repr__ method in the classes that appear after
        # Node in the MRO of the current instance (this will be the class that
        # inherits from GeomShape, e.g. GeomArc, GeomLine, ...):
        node_class = super(Node, self)
        shape = f"shape={node_class.__repr__()}, "
        layer = f"layer={self.layer}, " if hasattr(self, "layer") else ""
        width = f"width={self.width}, " if hasattr(self, "width") else ""
        style = f"style={self.style}, " if hasattr(self, "style") else ""
        fill = f"fill={self.fill}, " if hasattr(self, "fill") else ""
        repr = f"{class_name}({shape}{layer}{width}{style}{fill}".removesuffix(", ")
        repr += ")"
        return repr

    def __str__(self) -> str:
        """The string representation of the NodeShape."""
        return self.__repr__()
