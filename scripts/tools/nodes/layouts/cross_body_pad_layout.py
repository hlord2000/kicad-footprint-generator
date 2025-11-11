import enum

from KicadModTree import Container, CornerSelection, Node, Pad
from kilibs.geom import GeomRectangle, GeomShapeClosed, Vector2D
from scripts.tools import drawing_tools_silk
from scripts.tools.drawing_tools import getKeepoutsForPads
from scripts.tools.global_config_files import global_config as GC
from scripts.tools.nodes import pin1_arrow

from .footprint_layout import FootprintLayoutNode


class CrossBodyPadLayout(FootprintLayoutNode):
    """
    A layout node that represents a rectangular device with a number of pads
    that cross the body vertically:

         +------+     +------+     +------+ <--- pads
         |      |     |      |     |      |
    +-------------------------------------------+
    |    |      |     |      |     |      |     |
    |    |      |     |      |     |      |     | <--- body
    |    |      |     |      |     |      |     |
    +-------------------------------------------+
         |      |     |      |     |      |
         +------+     +------+     +------+

    THe pads may or may not extend beyond the body at the ends.

    In the 2-pad case, this is a lot like a 2-pad chip, and either could be
    appropriate (if the device has 2/3-pad variants, it's a good sign).
    """

    class SilkStyle(enum.Enum):
        """Supported silk styles for this layout"""

        NONE = 0
        BODY_RECT = 1

    courtyard_body_offset: float | GC.GlobalConfig.CourtyardType

    def __init__(
        self,
        global_config: GC.GlobalConfig,
        pad_size: Vector2D | list[Vector2D],
        pad_pitch: float | list[float],
        pad_count: int,
        body_size: Vector2D,
        pads_body_offset: Vector2D = Vector2D(0, 0),
        silk_style: SilkStyle = SilkStyle.BODY_RECT,
        has_pin1_arrow: bool = False,
    ):
        """
        Args:
            global_config: The global config object
            pad_size: The size of the pads
            pad_pitch: The pitch of the pads in x/y
            body_size: The size of the body
            pads_body_offset: The offset of the pads centre
                         relative to the centre of the body.
            courtyard_body_offset: The offset of the body courtyard, if different.
            polarized: Draw a polarized silk marker (currently, a U shape)
        """
        super().__init__(global_config=global_config)

        # Opt into nice things
        self.automatic_courtyard = True
        self.automatic_label_placement = True
        self.automatic_body_rect = True
        self.automatic_silk_rect = silk_style == self.SilkStyle.BODY_RECT

        self.body_size = body_size.copy()
        self.courtyard_offset = global_config.get_courtyard_offset(
            GC.GlobalConfig.CourtyardType.DEFAULT
        )

        self._pad_size = pad_size
        self.pad_count = pad_count
        self.pad_body_offset = pads_body_offset.copy()

        self.pad_positions = self._compute_pad_positions(pad_pitch)

        self.courtyard_body_offset = GC.GlobalConfig.CourtyardType.DEFAULT

        self.silk_style = silk_style
        self.has_pin1_arrow = has_pin1_arrow

    def _get_pad_size(self, n: int) -> Vector2D:
        if isinstance(self._pad_size, list):
            assert (
                len(self._pad_size) == self.pad_count
            ), "pad_size must be a list of the same length as pad_count"
            return self._pad_size[n]
        else:
            return self._pad_size

    def _get_fab_bevel_corner(self):
        if self.has_pin1_arrow:
            # The default
            return super()._get_fab_bevel_corner()

        return CornerSelection(None)

    def _get_courtyard_offset_body(self):
        return self.courtyard_body_offset

    def _compute_pad_positions(self, pad_pitch: float | list[float]):

        pad_pos_x = []

        if isinstance(pad_pitch, list):
            assert (
                len(pad_pitch) == self.pad_count - 1
            ), "pad_pitch must be a list of the same length as pad_count - 1"

            for i in range(self.pad_count):
                if i == 0:
                    pad_pos_x.append(0)
                else:
                    pad_pos_x.append(pad_pos_x[i - 1] + pad_pitch[i - 1])
        else:
            for i in range(self.pad_count):
                pad_pos_x.append(i * pad_pitch)

        array_len = pad_pos_x[-1] - pad_pos_x[0]

        return [
            Vector2D(
                pos_x + self.pad_body_offset.x - array_len / 2, self.pad_body_offset.y
            )
            for pos_x in pad_pos_x
        ]

    def get_body_shape(self) -> GeomRectangle:
        # The body is always at 0, 0, even if the pads are offset
        return GeomRectangle(center=Vector2D(0, 0), size=self.body_size)

    def _get_pad_bounds(self) -> GeomRectangle:
        max_pad_t, max_pad_b = 0, 0

        # This already includes the pad-body offset
        for i, pad_pos in enumerate(self.pad_positions):
            pad_size = self._get_pad_size(i)
            pad_t = pad_pos.y - pad_size.y / 2
            pad_b = pad_pos.y + pad_size.y / 2

            max_pad_b = max(max_pad_b, pad_b)
            max_pad_t = min(max_pad_t, pad_t)

        pad0_l = self.pad_positions[0].x - self._get_pad_size(0).x / 2
        padn_r = self.pad_positions[-1].x + self._get_pad_size(-1).x / 2

        return GeomRectangle(
            start=Vector2D(pad0_l, max_pad_t),
            end=Vector2D(padn_r, max_pad_b),
        )

    def _get_silk_keepouts(self) -> list[GeomShapeClosed]:
        return self._keepouts

    def _get_child_nodes(self, parent: Container[Node]) -> None:

        pad_opts = {
            "type": Pad.TYPE_SMT,
            "shape": Pad.SHAPE_ROUNDRECT,
            "layers": Pad.LAYERS_SMT,
            "round_radius_handler": self.global_config.roundrect_radius_handler,
        }

        # Because we allow for different pad sizes, we just do it directly
        pad_nodes: list[Pad] = []

        for i, pad_pos in enumerate(self.pad_positions):

            pad_size = self._get_pad_size(i)
            pad_nodes.append(
                Pad(
                    at=pad_pos,
                    number=i + 1,
                    size=pad_size,
                    **pad_opts,
                )
            )

        # Add keepouts for the pads
        self._keepouts = getKeepoutsForPads(
            pad_nodes, self.global_config.silk_pad_offset
        )

        parent += pad_nodes

        if self.silk_style == self.SilkStyle.BODY_RECT and self.has_pin1_arrow:

            # If the left pad extends past the body, we'll use an end-on eastward arrow
            # Otherwise, we'll nestle it in the corner of the body and pad.

            body_rect = self.get_body_shape()

            left_edge_pad_defined: bool = (
                pad_nodes[0].at.x - pad_nodes[0].size.x / 2
            ) < (body_rect.left + 2 * self.global_config.silk_fab_offset)

            if left_edge_pad_defined:
                triangle = drawing_tools_silk.draw_silk_triangle_for_pad(
                    pad_nodes[0],
                    arrow_direction=pin1_arrow.Direction.EAST,
                    arrow_size=drawing_tools_silk.SilkArrowSize.MEDIUM,
                    pad_silk_offset=self.global_config.silk_pad_offset,
                    stroke_width=self.global_config.silk_line_width,
                )
                parent.append(triangle)
            else:
                triangle = (
                    drawing_tools_silk.draw_silk_triangle45_clear_of_fab_hline_and_pad(
                        global_config=self.global_config,
                        pad=pad_nodes[0],
                        arrow_direction=pin1_arrow.Direction.NORTHEAST,
                        line_y=body_rect.bottom,
                        line_clearance_y=self.global_config.silk_fab_offset,
                        arrow_size=drawing_tools_silk.SilkArrowSize.MEDIUM,
                    )
                )

                tri_bbox = triangle.bbox()
                tri_bbox.inflate(self.global_config.silk_line_width * 2.5)

                self._keepouts.append(
                    GeomRectangle(
                        center=tri_bbox.center,
                        size=tri_bbox.size,
                    )
                )

                parent.append(triangle)
