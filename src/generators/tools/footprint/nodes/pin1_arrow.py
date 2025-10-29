from KicadModTree import Polygon
from kilibs.geom import Direction, GeomPolygon, Vector2D, BoundingBox
import copy
from typing import Self

class SilkscreenArrow(Polygon):
    """
    Generic silkscreen arrow base class
    """

    def __init__(
        self,
        shape: GeomPolygon,
        layer: str = "F.SilkS",
        width: float | None = None,
        fill: bool = True,
    ) -> None:
        super().__init__(
            shape=shape,
            layer=layer,
            width=width,
            fill=fill,
        )

    def bbox(self) -> BoundingBox:
        width = self.width/2 if self.width is not None else 0.0
        return self.bbox().inflate(width)

    def as_polygon(self, inflation: float = 0) -> GeomPolygon:
        """
        Get this arrow's bounding polygon, possibly with inflation.

        This is useful for clearing a space for the arrow in other silk features.
        """
        return GeomPolygon(shape=self).inflated(inflation)
    
    def copy(self) -> Self:
        return copy.copy(self)


class Pin1SilkscreenArrow(SilkscreenArrow):

    def __init__(
        self,
        apex_position: Vector2D,
        angle: float | Direction,
        size: float,
        length: float,
        layer: str,
        line_width_mm: float,
    ):
        """
        This is the generic constructor for a modern (2024-era) pin 1 silkscreen arrow.

               |<>|---length
        ------ +\
          |    | \
        size   |  +<--pos
          |    | /
        ------ +/

        :param pos: The position of the arrow
        :param angle: The angle of the arrow - this is the direction the arrow points in - 0 is rightwards
        :param size: size of the triangle (node to node, line width is not included)
        :param length: length of the triangle (node to node)
        :param layer: layer of the arrow
        :param line_width_mm: line width of the arrow (can be 0)
        """
        pos = Vector2D(apex_position)

        if isinstance(angle, Direction):
            angle = angle.value

        arrow_pts = [
            pos,
            pos + Vector2D.from_floats(-length, size * 0.50),
            pos + Vector2D.from_floats(-length, -size * 0.50),
            pos
        ]

        gpoly = GeomPolygon(shape=arrow_pts)

        # Rotate the arrow backwards (so it points in the right direction)
        gpoly.rotate(angle=-angle, origin=pos)

        super().__init__(
            shape=gpoly, layer=layer, width=line_width_mm, fill=True
        )


class Pin1SilkScreenArrow45Deg(SilkscreenArrow):
    """
    Makea 45-degree filled triangle with H/V sides of equal length

    Size is between nodes, overall size will include 1*line_width overall

        + ---
       /|  |<-size   (this is a SE pointing arrow)
      +-+ ---

    :param size: size of the triangle
    :angle: angle of the arrow - this is the direction the arrow points in. This is usually NE/SE/SW/NW
    """

    def __init__(
        self, apex_position: Vector2D, angle: float | Direction,
        size: float, layer: str, line_width_mm: float
    ) -> None:

        arrow_pts = [
            apex_position,
            apex_position + Vector2D.from_floats(-size, 0),
            apex_position + Vector2D.from_floats(0, -size),
            apex_position,
        ]

        gpoly = GeomPolygon(shape=arrow_pts)

        if isinstance(angle, Direction):
            angle = angle.value

        # SE (315) is the default
        angle = angle - Direction.SOUTHEAST.value

        if angle != 0:
            gpoly.rotate(-angle, origin=apex_position)

        super().__init__(
            shape=gpoly, layer=layer, width=line_width_mm, fill=True
        )
