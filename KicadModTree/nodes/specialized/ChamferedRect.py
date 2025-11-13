from KicadModTree.nodes.base.Polygon import Polygon
from KicadModTree.nodes.base.Rectangle import Rectangle
from KicadModTree.nodes.Node import Node
from KicadModTree.util.corner_handling import ChamferSizeHandler
from KicadModTree.util.corner_selection import CornerSelection
from kilibs.geom.vector import Vector2D


class ChamferRect(Node):
    """
    Draws a rectangle with some number of chamfered, centered on the origin by
    default.
    """

    def __init__(
        self,
        at: Vector2D,
        size: Vector2D,
        chamfer: ChamferSizeHandler,
        corners: CornerSelection,
        layer: str,
        width: float,
        fill: bool = False,
    ):
        super().__init__()

        self.size = size
        self.chamfer = chamfer
        self.corners = corners
        self.layer = layer
        self.width = width
        self.fill = fill
        self.at = at

    def get_flattened_nodes(self) -> list[Rectangle | Polygon]:
        """Return the nodes to serialize."""

        pts: list[Vector2D] = []

        tl = Vector2D(0, 0) - self.size / 2 + self.at
        br = Vector2D(0, 0) + self.size / 2 + self.at

        if self.corners.is_any_selected():
            chamfer_size: float = self.chamfer.get_chamfer_size(
                min(self.size.x, self.size.y)
            )

            # anti-clockwise from top left (not including chamfer)

            if self.corners.top_left:
                pts.append(Vector2D(tl.x, tl.y + chamfer_size))
            else:
                pts.append(tl)

            if self.corners.bottom_left:
                pts.append(Vector2D(tl.x, br.y - chamfer_size))
                pts.append(Vector2D(tl.x + chamfer_size, br.y))
            else:
                pts.append(Vector2D(tl.x, br.y))

            if self.corners.bottom_right:
                pts.append(Vector2D(br.x - chamfer_size, br.y))
                pts.append(Vector2D(br.x, br.y - chamfer_size))
            else:
                pts.append(br)

            if self.corners.top_right:
                pts.append(Vector2D(br.x, tl.y + chamfer_size))
                pts.append(Vector2D(br.x - chamfer_size, tl.y))
            else:
                pts.append(Vector2D(br.x, tl.y))

            # and now include the top-left chamfer if any
            if self.corners.top_left:
                pts.append(Vector2D(tl.x + chamfer_size, tl.y))

            # For a Polygon (not PolygonLine), the last point is automatically connected
            # to the first
            poly = Polygon(
                shape=pts, layer=self.layer, width=self.width, fill=self.fill
            )
            poly._parent = self
            return [poly]
        else:
            rect = Rectangle(
                start=tl, end=br, layer=self.layer, width=self.width, fill=self.fill
            )
            rect._parent = self
            return [rect]
