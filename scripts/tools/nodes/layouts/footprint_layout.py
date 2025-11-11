import abc

from KicadModTree import Container, CornerSelection, Node, Translation
from KicadModTree.nodes.specialized.ChamferedRect import ChamferRect
from KicadModTree.util import courtyard_builder
from kilibs.geom import GeomRectangle, GeomShapeClosed, Vector2D
from scripts.tools import drawing_tools as DT
from scripts.tools import footprint_text_fields
from scripts.tools.global_config_files import global_config as GC


class FootprintLayoutNode(Node, abc.ABC):
    """
    A FootprintLayoutNode is a node that draws the (main) layout of a footprint
    of a certain type. It is mainly used for devices which have "common"
    layouts, but can be used for any footprint. The main use is allowing many
    generators to share the geometry of the footprint, but drive them with
    different parameters as they need.

    They are usually driven in fairly generic terms (e.g. device 2x3mm, 4pins,
    pitch) etc, and detailed metadata is appended to the parent FP as siblings
    to this node.  In particular, layouts do not care what kind of device it is,
    they only care about the geometry of the footprint (so they are a graphical
    abstraction).

    If geometry needs to be derived from a complex calculation such as IPC
    formulae using various input parameters, it may be better to add a factory
    fuction that does this. For example, instead of the layout node taking "pin
    size" and "global config", the factory function distills it into "pad size"
    and "drill size", and the layout node doesn't need to know about IPC rules,
    it just takes pure geometry. The means it can be driven directly if needed,
    or by another factory function.

    On the other hand, driving silk/fab/courtyard line properties with global
    config is probably a good idea, as it saves a lot of repetition.

    This is distinct from Footprint, which is also a Node, but represents the
    entire footprint, including all other nodes and metadata.

    E.g.:

    - Footprint
       - FootprintLayoutNode (some subclass of)
          - Pad (creared by the layout)
          - Line ....
          - Text
       - Model
       - Additional drawings
    """

    def __init__(self, global_config: GC.GlobalConfig):
        super().__init__()

        # Instance attributes:
        self.global_config: GC.GlobalConfig
        """A copy of the global config."""
        self._cached_child_nodes: list[Node] | None
        """The list of the cached child nodes."""
        self._cached_courtyard_builder: courtyard_builder.CourtyardBuilder | None
        """The cached courtyard builder."""
        # Inheritors can set these to True to opt into useful common functions
        # They must be set by the end of _get_child_nodes() to be effective.
        self.automatic_label_placement: bool
        """Automatically place labels based on body/couryard rects."""
        self.automatic_courtyard: bool
        """Draw an automatic courtyard, outset from the body rect and pads."""
        self.automatic_silk_rect: bool
        """Draw a simple rectangle for the silk, outset from the body rect
        Requires get_body_rect() to be implemented"""
        self.automatic_body_rect: bool
        """Draw a simple chamfered rectangle for the body, on the Fab layer,
        in line with the body nominal"""

        self.global_config = global_config

        self.automatic_label_placement = False
        self.automatic_courtyard = False
        self.automatic_body_rect = False
        self.automatic_silk_rect = False

        self._cached_child_nodes = None
        self._cached_courtyard_builder = None

    def get_body_shape(self) -> GeomShapeClosed:
        """
        Get the body rect of the device. This is not necessarily the same as the
        body outline, whih may have more detail. This is the rect that drives
        label placement (if automatic).

        You must implement this in your subclass if you want any automatic features.
        """
        raise NotImplementedError(
            "get_body_shape() must be implemented by this subclass"
        )

    def _get_courtyard_unrounded(self) -> GeomShapeClosed:
        """
        Get the courtyard of the device. This is not necessarily the same as the
        drawn courtyard, which may have more detail. This is the shape that drives
        things like label placement (if automatic). Usaully, this is a rectangle.

        It doesn't need to be rounded, that will be done for you.

        You only need to implement this if you want automatic label placement, and you
        have not requested an automatic courtyard.
        """
        raise NotImplementedError(
            "_get_courtyard_unrounded() must be implemented by this subclass"
        )

    def _get_courtyard_rect(self) -> GeomRectangle:
        """
        Get the courtyard rectangle of the device. This is used to place
        labels.
        """
        bbox = GeomRectangle(self._get_courtyard_unrounded().bbox())

        rect = bbox.round_to_grid(outwards=True, grid=self.global_config.courtyard_grid)
        return rect

    def _get_fab_bevel_corner(self) -> CornerSelection:
        """
        Get the corner selection for the fab bevel. This is used to generate the
        fab rectangle.

        Normal Rotation A parts have this in the top left.
        """
        return CornerSelection({CornerSelection.TOP_LEFT: True})

    @abc.abstractmethod
    def _get_child_nodes(self, parent: Container[Node]) -> None:
        """
        Add the child nodes to the parent node. This is where inheritors
        add their own pads, lines, text, etc. to the footprint.
        """
        pass

    def _get_silk_keepouts(self) -> list[GeomShapeClosed]:
        """
        Get the keepouts for the silk layer. These are used to trim automatic
        silk patterns, but inheritors can also use it for their own silk.

        This will only be called after _get_child_nodes() has been called, so
        you can use the child nodes to generate the keepouts if you want.
        """
        return []

    def get_offset(self) -> Vector2D:
        """
        Get the offset for this node. This is used to place the node in
        the footprint.

        For most SMD footprints, this will be the origin (0, 0), but for
        through-hole footprints, this may be pin 1.
        """
        return Vector2D(0, 0)

    def get_flattened_nodes(self) -> list[Node]:
        """Return the nodes to serialize."""
        # This cache is important, because the output sorting functions and so on
        # call get_flattened_nodes() multiple times, and we don't want to regenerate
        # everything (including keepout maths) every time.
        if self._cached_child_nodes is None:
            self._cached_child_nodes = self._generate_child_nodes()
        nodes: list[Node] = []
        for node in self._cached_child_nodes:
            nodes += node.get_flattened_nodes()
        return nodes

    def _get_fab_ref_y_pos(self) -> float | str:
        """
        Get the Y position of the reference designator. This is used to place
        the reference designator in the footprint.

        Return "top", "bottom", "center", or an explicit position
        """
        return "center"

    def _get_courtyard_offset_pads(self) -> float | GC.GlobalConfig.CourtyardType:
        """
        Get the courtyard offset for the pads. This is used to generate the
        courtyard rect.
        """
        return GC.GlobalConfig.CourtyardType.DEFAULT

    def _get_courtyard_offset_body(self) -> float | GC.GlobalConfig.CourtyardType:
        """
        Get the courtyard offset from the body. This is used to generate the
        courtyard rect.
        """
        return GC.GlobalConfig.CourtyardType.DEFAULT

    def _get_courtyard(
        self, node: Container[Node]
    ) -> courtyard_builder.CourtyardBuilder:
        """Calculate (if not done so before) the courtyard based on the body shape
        and the pads that have been added until this point to the layout and return the
        courtyard builder.
        """
        if self._cached_courtyard_builder:
            return self._cached_courtyard_builder

        def resolve_cy_off(offset: float | GC.GlobalConfig.CourtyardType) -> float:
            """
            Resolve the courtyard offset as an absolute value in mm.
            """
            if isinstance(offset, GC.GlobalConfig.CourtyardType):
                return self.global_config.get_courtyard_offset(offset)
            return offset

        offset_pads = resolve_cy_off(self._get_courtyard_offset_pads())
        offset_fab = resolve_cy_off(self._get_courtyard_offset_body())

        self._cached_courtyard_builder = courtyard_builder.CourtyardBuilder.from_node(
            node=node,
            global_config=self.global_config,
            offset_fab=offset_fab,
            offset_pads=offset_pads,
            outline=self.get_body_shape().bbox(),
        )
        return self._cached_courtyard_builder

    def _generate_child_nodes(self) -> list[Node]:

        translate = self.get_offset()

        translation = Translation(translate)
        translation._parent = self

        body_shape = self.get_body_shape()
        body_bbox = body_shape.bbox()

        # Defer to the inheritor to generate the child nodes
        # that are specific to this layout
        self._get_child_nodes(translation)

        if self.automatic_body_rect:
            # whatever the body shape is, we are asked to draw a chamfered rectangle
            translation += ChamferRect(
                at=body_bbox.center,
                size=body_bbox.size,
                chamfer=self.global_config.fab_bevel,
                corners=self._get_fab_bevel_corner(),
                layer="F.Fab",
                width=self.global_config.fab_line_width,
            )

        if self.automatic_silk_rect:
            kos = self._get_silk_keepouts()

            silk_shape = body_shape.inflated(self.global_config.silk_fab_offset)

            silk_nodes = DT.makeNodesWithKeepout(
                silk_shape,
                layer="F.SilkS",
                keepouts=kos,
                width=self.global_config.silk_line_width,
            )

            translation += silk_nodes

        # We do this after storing the nodes in the translation, so that
        # we can then use the translation as the root node for the
        # courtyard calculations

        courtyard_bbox = None

        if self.automatic_courtyard:
            courtyard = self._get_courtyard(translation)

            # Actually add the courtyard to the translation
            translation += courtyard.node

            # And keep the bbox in case we need it for the labels
            courtyard_bbox = courtyard.bbox

        if self.automatic_label_placement:

            # We didn't autogen a courtyard, so we need to use the bbox the
            # inheritor provides
            if courtyard_bbox is None:
                courtyard_bbox = self._get_courtyard_rect()

            footprint_text_fields.addTextFields(
                translation,
                configuration=self.global_config,
                body_edges=body_bbox,
                courtyard=courtyard_bbox,
                fp_name=self._parent.name,
                text_y_inside_position=self._get_fab_ref_y_pos(),
                allow_rotation=True,
            )

        return [translation]
