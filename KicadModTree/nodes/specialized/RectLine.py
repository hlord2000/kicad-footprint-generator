# KicadModTree is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# KicadModTree is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with kicad-footprint-generator. If not, see < http://www.gnu.org/licenses/ >.
#
# (C) 2016 by Thomas Pointhuber, <thomas.pointhuber@gmx.at>

from typing import Optional, Self

from KicadModTree.nodes.Node import Node
from KicadModTree.util.line_style import LineStyle
from kilibs.geom import BoundingBox, GeomRectangle, Vec2DCompatible, Vector2D

from .PolygonLine import PolygonLine


class RectLine(PolygonLine):
    def __init__(
        self,
        layer: str = "F.SilkS",
        width: Optional[float] = None,
        style: LineStyle = LineStyle.SOLID,
        fill: bool = False,
        offset: float | list[float] | tuple[float] = None,
        shape: Optional[Self | GeomRectangle | BoundingBox] = None,
        center: Optional[Vec2DCompatible] = None,
        size: Optional[Vec2DCompatible] = None,
        start: Optional[Vec2DCompatible] = None,
        end: Optional[Vec2DCompatible] = None,
        angle: float = 0.0,
    ):
        """Create a rectangle.

        Args:
            layer: Layer.
            width: Line width in mm. If `None`, then the standard width for the given
                layer will be used when the serializing the node.
            style: Line style.
            fill: If the shape is filled or only the outline is visible.
            offset: amount by which the shape is inflated or deflated (if offset negative).
            shape: Rectangle or bounding box from which to derive the parameters.
            center: Center point of the rectangle.
            size: Size of the rectangle.
            start: Top left corner of the rectangle
            end: Bottom right corner of the rectangle
            angle: angle of the rectangle in degrees.
        """
        # New code. Currently commented out and the old code is used for backwards compatibility.
        # Node.__init__(self)
        # if offset:
        #     if isinstance(offset, float):
        #         offset = Vector2D(offset, offset)
        #     else:
        #         offset = Vector2D(offset.x, offset.y)
        # else:
        #     offset = Vector2D(0, 0)
        # GeomRectangle.__init__(
        #     self,
        #     shape=shape,
        #     center=center,
        #     size=size,
        #     start=start,
        #     end=end,
        #     angle=angle)
        # self.size += 2* offset
        if shape is not None:
            self.start = shape.start
            self.end = shape.end
        else:
            self.start = Vector2D(start)
            self.end = Vector2D(end)
        # If specified, an 'offset' can be applied to the RectLine.
        # For example, creating a border around a given Rectangle of a specified size
        if offset is not None:
            # Has an offset / inset been specified?
            if type(offset) in [int, float]:
                offset = Vector2D(offset, offset)
            elif type(offset) in [list, tuple] and len(offset) == 2:
                # Ensure that all offset params are numerical
                if all([type(i) in [int, float] for i in offset]):
                    offset = Vector2D(offset)
            else:
                offset = Vector2D(0, 0)
            # For the offset to work properly, start-pos must be top-left, and end-pos must be bottom-right
            s = Vector2D(min(self.start.x, self.end.x), min(self.start.y, self.end.y))
            e = Vector2D(max(self.start.x, self.end.x), max(self.start.y, self.end.y))
            # Put the offset back in
            self.start = s - offset
            self.end = e + offset
        polygon_line = [
            Vector2D(self.start.x, self.start.y),
            Vector2D(self.start.x, self.end.y),
            Vector2D(self.end.x, self.end.y),
            Vector2D(self.end.x, self.start.y),
            Vector2D(self.start.x, self.start.y),
        ]
        # Add center and size properties for the courtyard function
        self.center = (self.start + self.end) / 2
        self.size = (self.start - self.end).positive()
        PolygonLine.__init__(
            self, shape=polygon_line, layer=layer, width=width, style=style, fill=fill
        )

    def _getRenderTreeText(self):
        render_text = Node._getRenderTreeText(self)
        render_text += " [start: [x: {sx}, y: {sy}] end: [x: {ex}, y: {ey}]]".format(
            sx=self.start.x, sy=self.start.y, ex=self.end.x, ey=self.end.y
        )

        return render_text
