import enum

from KicadModTree import Container, CornerSelection, Node, Pad
from KicadModTree.util import courtyard_builder
from kilibs.geom import GeomLine, GeomRectangle, Vector2D
from scripts.tools import drawing_tools as DT
from scripts.tools.drawing_tools_silk import SilkArrowSize, draw_silk_triangle_for_pad
from scripts.tools.global_config_files import global_config as GC
from scripts.tools.nodes import pin1_arrow

from .footprint_layout import FootprintLayoutNode


class ThtAxialLayout(FootprintLayoutNode):
    """
    A layout node that represents a simple axial leaded device with a number of
    pads on either side of the body, such as:

               +--------------------------+
    +---+      |                          |      +---+
    | o |------|                          |------| o |
    +---+      |                          |      +---+
               +--------------------------+

    Usually there will be 2 pads, but there can be more, e.g. some gas
    discharge tubes have a pin in the middle.
    """

    class PolarizationStyle(enum.Enum):
        """Supported polarisation styles for this layout"""

        NONE = 0
        """
        No polarisation, no pin 1 marking.
        """
        BODY_CHAMFER = 1
        """
        Chamfer on the fab body rectangle to indicate pin 1, with pin 1 arrow.
        """
        # NOTCHED_BODY = 2
        # """
        # Notch on the fab body rectangle to indicate pin 1 (axial cap style)
        # """

    courtyard_body_offset: float | GC.GlobalConfig.CourtyardType

    def __init__(
        self,
        global_config: GC.GlobalConfig,
        pad_prototype: Pad,
        num_pads: int,
        pad_pitch: float,
        body_size: Vector2D,
        lead_diameter: float,
        pad_numbers: list[str] | None = None,
        polarization_style: PolarizationStyle = PolarizationStyle.NONE,
        ajust_pin1_shape: bool = True,
        total_length: float | None = None,
        shrink_fit_lead_courtyard: bool = True,
    ):
        """
        Args:
            global_config: The global config object
            pad_prototype: The prototype pad to use for the pads - most pad properties
                will be copied from this pad, but the position and number will be set, and
                the shape may be overridden for pin 1.
            num_pads: The number of pads to create
            pad_pitch: The pitch of the pads in mm
            body_size: The size of the body in mm (width, height)
            lead_diameter: The diameter of the lead in mm
            pad_numbers: A list of pad numbers to use, or None to use the default numbering
            polarization_style: The style of pin 1 marking to use
            ajust_pin1_shape: If True, adjust the shape of the first pad to be a
                round rectangle
            total_length: The total length of the device, including the leads, if this is
                different from the overall pad-to-pad length.
                If None, the total length will be calculated from the pads.
            shrink_fit_lead_courtyard: If True, the courtyard around the lead will be
                shrunk to fit the lead diameter, otherwise it will be the same height as the body
        """

        super().__init__(global_config=global_config)

        # Opt into nice things
        self.automatic_courtyard = False
        self.automatic_label_placement = True
        self.automatic_silk_rect = False

        self.polarization_style = polarization_style

        if self.polarization_style in [
            self.PolarizationStyle.NONE,
            self.PolarizationStyle.BODY_CHAMFER,
        ]:
            # The automatic body rectangle is suitable
            self.automatic_body_rect = True
        else:
            self.automatic_body_rect = False

        self.body_size = Vector2D(body_size)
        self.total_length = total_length
        self.courtyard_offset = global_config.get_courtyard_offset(
            GC.GlobalConfig.CourtyardType.DEFAULT
        )

        self.num_pads = num_pads
        self.pad_pitch = pad_pitch
        self.pad_prototype = pad_prototype
        self.pad_numbers = pad_numbers
        self.adjust_pin1_shape = ajust_pin1_shape

        self.lead_diameter = lead_diameter
        self.shrink_fit_lead_courtyard = shrink_fit_lead_courtyard

        self.courtyard_body_offset = GC.GlobalConfig.CourtyardType.DEFAULT

    def get_offset(self) -> Vector2D:
        """
        Put pad 1 at the origin
        """
        return Vector2D((self.num_pads - 1) * self.pad_pitch / 2, 0)

    def get_body_shape(self) -> GeomRectangle:
        return GeomRectangle(center=Vector2D(0, 0), size=self.body_size)

    def _get_courtyard_unrounded(self):
        # We need this because we draw a custom courtyard but still want
        # automatic courtyard placement.
        # a simple rectangle works well enough for this layout.
        return self.get_body_shape().inflated(self.courtyard_offset)

    def _get_fab_bevel_corner(self) -> CornerSelection:
        if self.polarization_style == self.PolarizationStyle.BODY_CHAMFER:
            # The default chamfer for pin 1 marking
            return super()._get_fab_bevel_corner()

        # Otherwise, no chamfer (either the body is not chamfered,
        # or the pin 1 marking is done some other way)
        return CornerSelection({})

    def _get_child_nodes(self, parent: Container[Node]):

        pads = []

        pad_mid_x = (self.num_pads - 1) * self.pad_pitch / 2
        for i in range(self.num_pads):

            shape_override = None
            if (
                i == 0
                and self.adjust_pin1_shape
                and self.pad_prototype.type == Pad.TYPE_THT
            ):
                # Adjust the shape of the first pad if it's a THT pad
                shape_override = Pad.SHAPE_ROUNDRECT

            pad_number = self.pad_numbers[i] if self.pad_numbers else str(i + 1)

            pad = self.pad_prototype.copy_with(
                at=Vector2D(i * self.pad_pitch - pad_mid_x, 0),
                number=pad_number,
                shape=shape_override,
            )
            parent.append(pad)
            pads.append(pad)

        pad_keepouts = DT.getKeepoutsForPads(
            pads=pads,
            clearance=self.global_config.silk_pad_offset,
        )

        silk_off = self.global_config.silk_fab_offset

        # Add the body shape
        silk_rect = self.get_body_shape().inflated(silk_off)

        parent += DT.makeNodesWithKeepout(
            geom_items=silk_rect,
            keepouts=pad_keepouts,
            layer="F.SilkS",
            width=self.global_config.silk_line_width,
        )

        pitch_length = self.pad_pitch * (self.num_pads - 1)
        if self.total_length is not None:
            total_length = self.total_length
        else:
            # Work it out from the pads
            total_length = pitch_length

        # Add the axial lead if longer than the body
        if total_length > self.body_size.x:

            fab_segs = [
                GeomLine(
                    start=Vector2D(-self.total_length / 2, 0),
                    end=Vector2D(-self.body_size.x / 2, 0),
                ),
                GeomLine(
                    start=Vector2D(self.body_size.x / 2, 0),
                    end=Vector2D(self.total_length / 2, 0),
                ),
            ]

            parent += DT.makeNodesWithKeepout(
                geom_items=fab_segs,
                keepouts=[],
                layer="F.Fab",
                width=self.global_config.fab_line_width,
            )

            silk_segs = [
                GeomLine(
                    start=Vector2D(-self.total_length / 2, 0),
                    end=Vector2D(-self.body_size.x / 2 - silk_off, 0),
                ),
                GeomLine(
                    start=Vector2D(self.body_size.x / 2 + silk_off, 0),
                    end=Vector2D(self.total_length / 2, 0),
                ),
            ]

            parent += DT.makeNodesWithKeepout(
                geom_items=silk_segs,
                keepouts=pad_keepouts,
                layer="F.SilkS",
                width=self.global_config.silk_line_width,
            )

        # Silk 1 arrow - only used when there's a body chamfer as the other styles
        # either have no pin 1 marking or use another system (e.g. notched body)
        if self.polarization_style == self.PolarizationStyle.BODY_CHAMFER:
            # Add a pin 1 arrow on the body chamfer

            # Adjust for the stroke width
            silk_arrow_size, silk_arrow_length = DT.getStandardSilkArrowSize(
                SilkArrowSize.LARGE,
                self.global_config.silk_line_width,
            )

            # The pin 1 arrow is at the end of the body rectangle or pad
            # unless it can fit above the pad
            silk_gap = 3 * self.global_config.silk_line_width
            arrow_x = self.body_size.x / 2 - silk_gap

            # If the pad extends past the body, we need to move the arrow
            arrow_x = min(
                arrow_x,
                pads[0].at.x - pads[0].size.x / 2 - self.global_config.silk_pad_offset,
            )

            if self.body_size.x < pitch_length - (silk_arrow_size + silk_gap * 2):
                # The pad sticks out more than the lead (usual for a resistor),
                # and there's space for it, so we can put the pin 1 arrow above the pad
                parent += draw_silk_triangle_for_pad(
                    pad=pads[0],
                    arrow_size=SilkArrowSize.LARGE,
                    arrow_direction=DT.Direction.SOUTH,
                    stroke_width=self.global_config.silk_line_width,
                    pad_silk_offset=self.global_config.silk_pad_offset,
                )

            elif self.total_length > pitch_length + self.pad_prototype.size.x:
                # If the lead sticks out MORE than the outer pad,
                # move the pin 1 arrow up and out of the way of the lead graphic

                parent += pin1_arrow.Pin1SilkScreenArrow45Deg(
                    apex_position=Vector2D(arrow_x, silk_gap),
                    angle=DT.Direction.SOUTHEAST,
                    size=silk_arrow_size,
                    layer="F.SilkS",
                    line_width_mm=self.global_config.silk_line_width,
                )

            else:
                # there's no stick-out lead, so we can put the pin 1 arrow
                # at the end of the body rectangle/pad

                parent += pin1_arrow.Pin1SilkscreenArrow(
                    apex_position=Vector2D(arrow_x, 0),
                    angle=DT.Direction.EAST,
                    size=silk_arrow_size,
                    length=silk_arrow_length,
                    layer="F.SilkS",
                    line_width_mm=self.global_config.silk_line_width,
                )

        # Courtyard
        crt_builder = courtyard_builder.CourtyardBuilder.from_node(
            node=parent,
            global_config=self.global_config,
            offset_fab=self.courtyard_offset,
            outline=self.get_body_shape(),
        )

        # Add the implicit axial lead, which may overrun the pads
        if self.total_length is not None:
            courtyard_height = self.lead_diameter

            if not self.shrink_fit_lead_courtyard:
                courtyard_height = max(courtyard_height, self.body_size.y)

            lead_rect = GeomRectangle(
                center=Vector2D(0, 0),
                size=Vector2D(self.total_length, courtyard_height),
            )
            crt_builder.add_rectangle(lead_rect, self.courtyard_offset)

        parent += crt_builder.node
