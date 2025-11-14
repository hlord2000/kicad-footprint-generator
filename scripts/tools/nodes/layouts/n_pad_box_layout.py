import enum
from typing import Any, Callable, Generator, Iterator, TypeAlias

from KicadModTree import Container, Node, Pad
from KicadModTree.util import courtyard_builder
from kilibs.declarative_defs.packages.two_pad_dimensions import TwoPadDimensions
from kilibs.geom import (
    BoundingBox,
    CornerSelection,
    Direction,
    GeomPolygon,
    GeomRectangle,
    GeomShapeClosed,
    Vector2D,
)
from scripts.tools import drawing_tools_silk
from scripts.tools.drawing_tools import getKeepoutsForPads, makeNodesWithKeepout
from scripts.tools.global_config_files import global_config as GC
from scripts.tools.nodes import pin1_arrow

from .footprint_layout import FootprintLayoutNode


def rect_inflate_anisotropic(rect: GeomRectangle, amount: Vector2D) -> GeomRectangle:
    """Inflate a rectangle by an amount that can be different in x and y."""
    return GeomRectangle(
        center=rect.center,
        size=Vector2D(
            rect.size.x + amount.x * 2,
            rect.size.y + amount.y * 2,
        ),
    )


class NPadBoxLayout(FootprintLayoutNode):
    """
    This is one of the most common and general layout idioms - some pads, and a body:

    .. aafig::

                +-----------------------+
        +-------|---+               +---|-------+
        |       |   |               |   |       |
        +-------|---+               +---|-------+
                |                       |
        +-------|---+               +---|-------+
        |       |   |               |   |       |
        +-------|---+               +---|-------+
                +-----------------------+

    The pad layouts are not defined, and are injected by a factory function.
    The body is a rectangle, and the silk is a rectangle around the body, and can
    be configured to be tight to the body, or to extend around the pads.
    """

    PadFactoryType: TypeAlias = Callable[[], Iterator[Pad]]
    """A pad factory is a callable that returns an iterator of pads."""

    class SilkStyle(enum.Enum):
        """Supported silk styles for this layout."""

        NONE = 0
        BODY_RECT = 1
        # PARALLEL_LINES = 2
        # U_SHAPE = 3

    class SilkClearance(enum.Enum):
        TIGHT_TO_BODY = 0
        """Silk is tight to the body, even if the pads cause it to be trimmed."""
        KEEP_TOP_BOTTOM = 1
        """Silk is tight to the body, but the top and bottom edges are outset if needed
        to ensure they're not trimmed by the pads."""
        FULL_RECT = 2
        """Silk is a full rectangle around the body, with no trimming by the pads."""

    body_size: Vector2D
    """The nominal size of the rectangular body, in mm."""

    silk_clearance: SilkClearance = SilkClearance.TIGHT_TO_BODY
    """Set the silk clearance style for this layout."""

    fab_to_silk_clearance: Vector2D = Vector2D.zero()
    """Extra clearance to add to the silk rectangle around the body, in mm, used when
    drawing the silk rectangle around the body."""

    silk_arrow_size: drawing_tools_silk.SilkArrowSize | None = (
        drawing_tools_silk.SilkArrowSize.MEDIUM
    )

    silk_arrow_direction_if_inside: Direction | None = None
    """
    If the pin1 pad is completely inside the body, define a direction for the arrow.
    If not given, the arrow is placed pointing in from the nearest side
    """

    """The size of the silk arrow to draw around the body, if the footprint is polarized.
    If None, no arrow is drawn."""

    body_to_courtyard_clearance: Vector2D | float | GC.GlobalConfig.CourtyardType = (
        GC.GlobalConfig.CourtyardType.DEFAULT
    )
    """Clearance to add to the courtyard rectangle around the body. This can be different in
    x and y directions."""

    def __init__(
        self,
        global_config: GC.GlobalConfig,
        pad_factory: PadFactoryType,
        body_size: Vector2D,
        body_offset: Vector2D,
        silk_style: SilkStyle,
        is_polarized: bool,
    ):
        """
        Create a two-pad SMD layout.

        Args:
            global_config: The global config object

            body_size: The nominal size of the body, in mm.
            silk_style: The style of the silk rectangle to draw around the body.
            is_polarized: Whether the footprint is polarised
        """

        super().__init__(global_config=global_config)

        # Opt into nice things

        # We don't do automatic courtyard for this layout, as it can have a custom
        # courtyard size in x and y for handling weird tolerance stackups.
        self.automatic_courtyard = False
        self.automatic_label_placement = True
        self.automatic_body_rect = True
        self.automatic_silk_rect = False

        self.pad_factory = pad_factory
        self.courtyard_body_offset = GC.GlobalConfig.CourtyardType.DEFAULT
        self.body_size = body_size
        self.body_offset = body_offset
        self.silk_style = silk_style
        self.is_polarized = is_polarized

        self.fab_to_silk_clearance = Vector2D.zero()

    def get_body_shape(self) -> GeomShapeClosed:
        """Get the body shape of the footprint."""
        return GeomRectangle(
            center=self.body_offset,
            size=self.body_size,
        )

    def _get_courtyard_unrounded(self):
        return self._courtyard_rect

    def _get_fab_bevel_corner(self) -> CornerSelection:
        if self.is_polarized:
            # The default
            return super()._get_fab_bevel_corner()

        return CornerSelection(None)

    def _get_child_nodes(self, parent: Container[Node]) -> None:

        pad_nodes: list[Pad] = []

        pad_bbox = BoundingBox()

        for pad in self.pad_factory():
            pad_bbox.include_bbox(pad.bbox())
            pad_nodes.append(pad)

        parent += pad_nodes

        # Add keepouts for the pads
        keepouts = getKeepoutsForPads(pad_nodes, self.global_config.silk_pad_offset)

        # Work out the silk graphics extents to stay clear of the pads and body as needed
        body_rect = GeomRectangle(center=self.body_offset, size=self.body_size)
        silk_rect = body_rect.copy()

        # If we have a fab to silk clearance, then use that
        if self.fab_to_silk_clearance.is_nullvec():
            # No extra clearance, use the global config value
            silk_rect.inflate(self.global_config.silk_fab_offset)
        else:
            silk_rect = rect_inflate_anisotropic(
                silk_rect,
                self.fab_to_silk_clearance + self.global_config.silk_fab_offset,
            )

        # If needed, extend the silk rectangle to ensure it does not clip the pads
        # in one or both direction.

        silk_rect_top = silk_rect.top
        silk_rect_bottom = silk_rect.bottom
        silk_rect_left = silk_rect.left
        silk_rect_right = silk_rect.right

        pad_bbox.inflate(self.global_config.silk_pad_offset)

        if self.silk_clearance == self.SilkClearance.TIGHT_TO_BODY:
            # Nothing to do
            pass
        elif self.silk_clearance == self.SilkClearance.KEEP_TOP_BOTTOM:
            # Extend the silk rectangle to ensure it does not clip the pads at the top and bottom
            silk_rect_top = min(pad_bbox.top, silk_rect_top)
            silk_rect_bottom = max(pad_bbox.bottom, silk_rect_bottom)
        elif self.silk_clearance == self.SilkClearance.FULL_RECT:
            # Extend the silk rectangle to ensure it does not clip the pads at all
            silk_rect_left = min(pad_bbox.left, silk_rect_left)
            silk_rect_right = max(pad_bbox.right, silk_rect_right)
            silk_rect_top = min(pad_bbox.top, silk_rect_top)
            silk_rect_bottom = max(pad_bbox.bottom, silk_rect_bottom)

        silk_rect = GeomRectangle(
            start=Vector2D(silk_rect_left, silk_rect_top),
            end=Vector2D(silk_rect_right, silk_rect_bottom),
        )

        # Add the silk arrow - fow now we defer to the auto arrow
        # method, but if we have U-shaped silk, we will need to skip.
        if self.is_polarized and self.silk_arrow_size is not None:
            arrow = drawing_tools_silk.auto_silk_triangle_for_pad_and_box(
                self.global_config,
                pad_nodes[0],
                silk_rect,
                self.silk_arrow_size,
                direction_if_inside=self.silk_arrow_direction_if_inside,
            )

            arrow_poly = arrow.as_polygon(self.global_config.silk_line_width * 2)
            keepouts.append(arrow_poly)

            parent += arrow

        # Add the body silk graphics

        silk_primitives: list[GeomRectangle | GeomPolygon] = []
        if self.silk_style == self.SilkStyle.NONE:
            # No silk
            pass
        elif self.silk_style == self.SilkStyle.BODY_RECT:
            silk_primitives.append(silk_rect)

        parent += makeNodesWithKeepout(
            silk_primitives,
            keepouts=keepouts,
            layer="F.SilkS",
            width=self.global_config.silk_line_width,
        )

        # Resolve the courtyard offsets
        if isinstance(self.body_to_courtyard_clearance, GC.GlobalConfig.CourtyardType):
            courtyard_body_offset = self.global_config.get_courtyard_offset(
                self.body_to_courtyard_clearance
            )
        elif isinstance(self.body_to_courtyard_clearance, Vector2D):
            # we'll use the min of the two for the auto courtyard
            courtyard_body_offset = self.body_to_courtyard_clearance.min_val
        else:
            courtyard_body_offset = self.body_to_courtyard_clearance

        # This does the usual courtyard building and handles the pads
        crt_builder = courtyard_builder.CourtyardBuilder.from_node(
            node=parent,
            global_config=self.global_config,
            offset_fab=courtyard_body_offset,
            outline=body_rect,
        )

        # If we have an uneven x/y courtyard offset, add a rectangle, which we
        # know is greater than or equal to the auto courtyard in each axis
        if (
            isinstance(self.body_to_courtyard_clearance, Vector2D)
            and not self.body_to_courtyard_clearance.x_y_equal
        ):
            self._courtyard_rect = rect_inflate_anisotropic(
                body_rect,
                self.body_to_courtyard_clearance,
            )
            crt_builder.add_rectangle(self._courtyard_rect, 0)
        else:
            self._courtyard_rect = body_rect.copy().inflate(courtyard_body_offset)

        parent += crt_builder.node


def make_layout_for_smd_two_pad_dimensions(
    global_config: GC.GlobalConfig,
    pad_dims: TwoPadDimensions,
    body_size: Vector2D,
    silk_style: NPadBoxLayout.SilkStyle,
    is_polarized: bool,
) -> NPadBoxLayout:
    """
    Create a NPadBoxLayout from the given two-pad dimensions, assuming the
    pads are simple SMD pads.

    This is one of the most common layouts - two-lead chips, SMD inductors
    and so on may all want to use this layout.

    Args:
        global_config: The global config object
        pad_dims: The dimensions of the pads, including spacing and size. This is intepreted
            with the 'inline' direction being in x and the 'crosswise' direction being in y.
        body_size: The nominal size of the body, in mm.
        silk_style: The style of the silk rectangle to draw around the body.
        is_polarized: Whether the footprint is polarised

    Returns:
        The layout Node.
    """

    pos_positions = [
        Vector2D.from_floats(
            -pad_dims.spacing_centre / 2, -pad_dims.offset_crosswise / 2
        ),
        Vector2D.from_floats(
            pad_dims.spacing_centre / 2, pad_dims.offset_crosswise / 2
        ),
    ]
    pad_size = Vector2D.from_floats(pad_dims.size_inline, pad_dims.size_crosswise)

    def smd_pad_factory() -> Generator[Pad, Any, None]:

        pad_prototype = Pad(
            at=Vector2D.zero(),
            size=pad_size,
            number="",
            type=Pad.TYPE_SMT,
            shape=Pad.SHAPE_ROUNDRECT,
            layers=Pad.LAYERS_SMT,
            round_radius_handler=global_config.roundrect_radius_handler,
        )

        for i, pos in enumerate(pos_positions):
            yield pad_prototype.copy_with(
                at=pos,
                number=f"{i + 1}",
            )

    return NPadBoxLayout(
        global_config=global_config,
        pad_factory=smd_pad_factory,
        body_size=body_size,
        body_offset=Vector2D.zero(),
        silk_style=silk_style,
        is_polarized=is_polarized,
    )
