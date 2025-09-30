from typing import Any, Literal, cast

from kilibs.ipc_tools import ipc_rules  # type: ignore
from kilibs.util.toleranced_size import TolerancedSize  # type: ignore
from scripts.tools.declarative_def_tools import (  # type: ignore
    common_metadata,
    fp_additional_drawing,
    rule_area_properties,
)


def _get_toleranced(
    dictionary: dict[str, Any],
    key: str,
    default_min: float | None = None,
    default_nom: float | None = None,
    default_max: float | None = None,
) -> TolerancedSize:
    if key in dictionary:
        return TolerancedSize.fromYaml(dictionary, base_name=key)
    else:
        return TolerancedSize(
            minimum=default_min,
            nominal=default_nom,
            maximum=default_max,
        )


class TopSlugConfiguration:
    """
    A type that represents the configuration of a "top slug"
    (top heat sink pad), probably from a YAML config block.
    """

    shape: str
    x: TolerancedSize
    y: TolerancedSize
    # Optional tail_x for rectangular slugs with vertical "tails" to the
    # package edge.
    tail_x: TolerancedSize | None

    def __init__(self, spec: dict[str, Any]) -> None:

        self.shape = spec["shape"]

        if self.shape not in ["rectangle", "cruciform"]:
            raise ValueError(f"Unsupported top slug shape: {self.shape}")

        self.x = TolerancedSize.fromYaml(spec, base_name="x")
        self.y = TolerancedSize.fromYaml(spec, base_name="y")

        self.tail_x = None

        if self.shape == "cruciform":
            self.tail_x = TolerancedSize.fromYaml(spec, base_name="tail_x")

    def get_name_suffix(self) -> str:

        # See https://github.com/KiCad/kicad-footprints/issues/955 for discussion
        s = "TopEP"

        if self.shape == "rectangle" or self.shape == "cruciform":
            s += f"{self.x.nominal:.2f}x{self.y.nominal:.2f}mm"
        else:
            raise ValueError(f"Unsupported top slug shape: {self.shape}")

        return s


class NoLeadConfiguration:
    """
    A type that represents the configuration of a no-lead footprint
    (probably from a YAML config block).

    Over time, add more type-safe accessors to this class, and replace
    use of the raw dictionary.
    """

    def __init__(
        self,
        pkg_id: str,
        spec: dict[str, Any],
        header: dict[str, Any],
        config: dict[str, Any],
    ) -> None:
        # Instance attributes for the raw source:
        self.pkg_id: str
        """The package name as given by the dictionary key."""
        self._spec: dict[str, Any]
        """The dictionary containing the specification of the device."""
        self._header: dict[str, Any]
        """The dictionary containing the file header."""
        self._config: dict[str, Any]
        """The dictionary containing the generator configuration."""

        # Instance attributes for generator independent data:
        self.metadata: common_metadata.CommonMetadata
        """The common meta data."""
        self.top_slug: TopSlugConfiguration | None
        """The optional top slug configuration."""
        self.additional_drawings: list[fp_additional_drawing.FPAdditionalDrawing]
        """The list containing additional drawings."""
        self.rule_areas: list[rule_area_properties.RuleAreaProperties] = []
        """The rule areas (zones)."""

        # Instance attributes for general data:
        self.device_type: str
        """The device type."""
        self.force_small_pitch_ipc_definition: bool
        """Whether the small pitch IPC definition shall be applied to this device."""
        self.ipc_density: ipc_rules.IpcDensity
        """The IPC density rules."""

        # Instance attributes related to the body:
        self.body_size_x: TolerancedSize
        """The body size in x direction."""
        self.body_size_y: TolerancedSize
        """The body size in y direction."""
        self.body_pcb_gap: float
        """The maximum gap between the PCB and the component body."""
        self.body_height: float
        """The maximum body height."""
        self.overall_height: float
        """The maximum overall height."""
        self.body_fillet: float
        """The size of the fillet of the component body."""

        # Instance attributes related to the pinning:
        self.pitch: float
        """The pitch."""
        self.num_pins_x: int
        """Number of pins of the package in x direction."""
        self.num_pins_y: int
        """Number of pins of the package in y direction."""
        self.pincount_full: int
        """The full pin count (also counting deleted and hidden pins, but not EPs)."""
        self.pincount_real: int
        """The real pin count (not counting deleted or hidden pins or EPs)."""
        self.deleted_pins: list[int]
        """The list of deleted pins."""
        self.hidden_pins: list[int]
        """The list of hidden pins."""

        # Instance attributes related to the pin shapes:
        self.lead_width: TolerancedSize
        """The lead length."""
        self.lead_len_x: TolerancedSize
        """The lead length of the pins on the x-axis."""
        self.lead_len_y: TolerancedSize
        """The lead length of the pins on the y-axis."""
        self.lead_height: TolerancedSize
        """The height of a lead."""
        self.lead_to_edge: TolerancedSize
        """The distance between the lead edge and the body edge."""
        self.lead_shape: str
        """The shape of the pins."""
        self.lead_shape_custom: list[list[list[float]]]
        """The polygon definition in case of `lead_shape = custom`."""

        # Instance attributes related to the exposed pad:
        self.has_ep: bool
        """Whether the device has an exposed pad"""
        self.ep_size_x: TolerancedSize
        """The size of the exposed pad(s) in x direction."""
        self.ep_size_y: TolerancedSize
        """The size of the exposed pad(s) in y direction."""
        self.ep_angle: float
        """The rotation angle of the exposed pad(s)."""
        self.ep_mask_x: TolerancedSize
        """The size of the mask of the exposed pad in x direction."""
        self.ep_mask_y: TolerancedSize
        """The size of the mask of the exposed pad in y direction."""
        self.ep_chamfer: TolerancedSize
        """The size of the chamfer on the exposed pad on the top left corner."""
        self.ep_num: list[int]
        """Number of exposed pads in x- and y-direction (creates a pad array)."""
        self.ep_pitch: list[float]
        """The pitch of the exposed pads in x- and y-direction."""
        self.ep_offset_x: float
        """The offset of the exposed pad(s) in the x direction."""
        self.ep_offset_y: float
        """The offset of the exposed pad(s) in the y direction."""

        # Instance attributes related to the marker:
        self.marker: Literal["circle", "bar", "none"]
        """Type of marker for the first pin."""
        self.marker_dx: float | None
        """Distance along the x-axis between the marker and the border."""
        self.marker_dy: float | None
        """Distance along the y-axis between the marker and the border."""

        # Instance attributes related to the data completeness to generate a FP or a
        # model:
        self.has_3d_data: bool
        """True if the no-lead configuration has a full data set for the 3D model."""
        self.has_fp_data: bool
        """True if the no-lead configuration has a full data set for the footprint."""

        # Instance attributes related to the names:
        self.fp_name_without_vias: str
        """Name of the footprint if it is created without vias."""
        self.fp_name_with_vias: str
        """Name of the footprint if it is created with vias."""
        self.model_name: str
        """Name of the 3D model."""
        self.lib_name: str
        """Name of the library."""

        # Assign the source parameters:
        self.pkg_id = pkg_id
        self._spec = spec
        if header:
            self._header = header
            self.has_fp_data = True
        else:
            self._header = {}
            self.has_fp_data = False
        self._config = config

        self._extract_generator_independent_data()
        self._extract_general_data()
        self._extract_body_data()
        self._extract_pinning_data()
        self._extract_pin_shape_data()
        self._extract_exposed_pad_data()
        self._extract_marker_data()
        self._compose_device_names()
        self._compose_lib_name()

    def _extract_generator_independent_data(self) -> None:
        self.metadata = common_metadata.CommonMetadata(self._spec)
        if "top_slug" in self._spec:
            self.top_slug = TopSlugConfiguration(self._spec["top_slug"])
        else:
            self.top_slug = None
        self.additional_drawings = (
            fp_additional_drawing.FPAdditionalDrawing.from_standard_yaml(self._spec)
        )  # type: ignore
        self.rule_areas = rule_area_properties.RuleAreaProperties.from_standard_yaml(  # type: ignore
            self._spec
        )

    def _extract_general_data(self) -> None:
        self.device_type = self._spec.get(
            "device_type", self._header.get("device_type", "") if self._header else ""
        )

        self.force_small_pitch_ipc_definition = self._spec.get(
            "force_small_pitch_ipc_definition", False
        )

        self.ipc_density = ipc_rules.IpcDensity.from_str(
            self._spec.get("ipc_density", "nominal")
        )

    def _extract_body_data(self) -> None:
        s = self._spec
        self.has_3d_data = True
        if "body_pcb_gap" in s and "body_height" in s:
            self.body_pcb_gap = TolerancedSize.fromYaml(s, "body_pcb_gap").maximum
            self.body_height = TolerancedSize.fromYaml(s, "body_height").maximum
            self.overall_height = self.body_pcb_gap + self.body_height
            if "overall_height" in s:
                overall_height_2 = TolerancedSize.fromYaml(s, "overall_height").maximum
                if abs(self.overall_height - overall_height_2) > 0.01:
                    raise KeyError(
                        f"Body height is over constrained and maximum dimensions "
                        f"do not match:\n"
                        f"body_pcb_gap: {self.body_pcb_gap}, "
                        f"body_height: {self.body_height}, "
                        f"overall_height: {overall_height_2}"
                    )
        elif "body_pcb_gap" in s and "overall_height" in s:
            self.body_pcb_gap = TolerancedSize.fromYaml(s, "body_pcb_gap").maximum
            self.overall_height = TolerancedSize.fromYaml(s, "overall_height").maximum
            self.body_height = self.overall_height - self.body_pcb_gap
        elif "body_height" in s and "overall_height" in s:
            self.body_height = TolerancedSize.fromYaml(s, "body_height").maximum
            self.overall_height = TolerancedSize.fromYaml(s, "overall_height").maximum
            self.body_pcb_gap = self.overall_height - self.body_height
        else:
            self.body_height = 0.0
            self.overall_height = 0.0
            self.body_pcb_gap = 0.0
            self.has_3d_data = False
        self.body_size_x = TolerancedSize.fromYaml(s, base_name="body_size_x")
        self.body_size_y = TolerancedSize.fromYaml(s, base_name="body_size_y")
        self.body_fillet = s.get("body_fillet", 0.0)

    def _extract_pinning_data(self) -> None:
        self.pitch = self._spec.get("pitch", 0.0)
        if self.pitch < 0:
            raise ValueError(f"Pitch must be positive, got {self.pitch}")
        self.num_pins_x = self._spec["num_pins_x"]
        self.num_pins_y = self._spec["num_pins_y"]

        if "deleted_pins" in self._spec:
            if type(self._spec["deleted_pins"]) is int:
                self._spec["deleted_pins"] = [self._spec["deleted_pins"]]
            self.deleted_pins = self._spec["deleted_pins"]
        else:
            self.deleted_pins = []
        if "hidden_pins" in self._spec:
            if type(self._spec["hidden_pins"]) is int:
                self._spec["hidden_pins"] = [self._spec["hidden_pins"]]
            self.hidden_pins = self._spec["hidden_pins"]
        else:
            self.hidden_pins = []
        if "deleted_pins" in self._spec and "hidden_pins" in self._spec:
            raise ValueError("A footprint may not have deleted pins and hidden pins.")

        self.pincount_full = self.num_pins_x * 2 + self.num_pins_y * 2
        self.pincount_real = (
            self.pincount_full - len(self.hidden_pins) - len(self.deleted_pins)
        )
        if "pin_count" in self._spec:
            # If the pin count is explicitly given, we use that and don't adjust for hidden/deleted pins
            self.pincount_full = cast(int, self._spec["pin_count"])

    def _extract_pin_shape_data(self) -> None:
        spec = self._spec
        self.lead_height = _get_toleranced(spec, "lead_height", default_nom=0.0)
        if not self.lead_height:
            self.has_3d_data = False
        else:
            self.has_3d_data = True
        lead_len_x = spec.get("lead_len", spec.get("lead_len_x", self.lead_height))
        lead_len_y = spec.get("lead_len", spec.get("lead_len_y", self.lead_height))
        if lead_len_x is None or lead_len_y is None:
            raise KeyError(
                f"Error in part {self.pkg_id}: 'lead_len' or 'lead_len_x' "
                "and 'lead_len_y' must be provided."
            )
        self.lead_len_x = TolerancedSize.fromYaml(lead_len_x)
        self.lead_len_y = TolerancedSize.fromYaml(lead_len_y)
        self.lead_width = TolerancedSize.fromYaml(spec, base_name="lead_width")
        self.lead_to_edge = _get_toleranced(spec, "lead_to_edge", default_nom=0.0)
        self.lead_shape = spec.get("lead_shape", "rounded")
        self.lead_shape_custom = spec.get("lead_shape_custom", [])

    def _extract_exposed_pad_data(self) -> None:
        spec = self._spec
        if "EP_size_x_min" in spec and "EP_size_x_max" in spec or "EP_size_x" in spec:
            self.ep_size_x = TolerancedSize.fromYaml(spec, base_name="EP_size_x")
            self.ep_size_y = TolerancedSize.fromYaml(spec, base_name="EP_size_y")
            self.has_ep = True
        else:
            self.ep_size_x = TolerancedSize.fromString("0")
            self.ep_size_y = TolerancedSize.fromString("0")
            self.has_ep = False
        self.ep_angle = spec.get("ep_angle", 0.0)
        self.ep_mask_x = _get_toleranced(spec, "EP_mask_x", default_nom=0.0)
        self.ep_mask_y = _get_toleranced(spec, "EP_mask_y", default_nom=0.0)
        self.ep_chamfer = _get_toleranced(spec, "ep_chamfer", default_nom=0.0)
        self.ep_num = spec.get("epad_n", [1, 1])
        self.ep_pitch = spec.get("epad_pitch", [0, 0])
        self.ep_offset_x = spec.get("epad_offst_x", 0.0)
        self.ep_offset_y = spec.get("epad_offst_y", 0.0)

    def _extract_marker_data(self) -> None:
        self.marker = self._spec.get("marker", "circle")
        self.marker_dx = self._spec.get("marker_d", self._spec.get("marker_dx"))
        self.marker_dy = self._spec.get("marker_d", self._spec.get("marker_dy"))

    def _compose_device_names(self) -> None:
        spec = self._spec

        size_x = self.body_size_x.nominal
        size_y = self.body_size_y.nominal

        if "pin_count" in spec:
            # If the pin count is explicitly given, we use that and don't adjust for hidden/deleted pins
            pincount_text = "{}".format(self.pincount_full)
        elif self.hidden_pins:
            pincount_text = "{}-{}".format(
                self.pincount_full - len(self.hidden_pins), self.pincount_full
            )
        elif self.deleted_pins:
            pincount_text = "{}-{}".format(
                self.pincount_full, self.pincount_full - len(self.deleted_pins)
            )
        else:
            pincount_text = "{}".format(self.pincount_full)

        ep_size_x = self.ep_size_x.nominal
        ep_size_y = self.ep_size_y.nominal
        if self.has_ep:
            name_format = self._config[
                "fp_name_EP_format_string_no_trailing_zero_pincount_text"
            ]
            if "EP_size_x_overwrite" in spec:
                ep_size_x = cast(float, spec["EP_size_x_overwrite"])
                ep_size_y = cast(float, spec["EP_size_y_overwrite"])
            if "EP_mask_x" in self._spec:
                name_format = self._config[
                    "fp_name_EP_custom_mask_format_string_no_trailing_zero_pincount_text"
                ]
        else:
            name_format = self._config[
                "fp_name_format_string_no_trailing_zero_pincount_text"
            ]

        if self.metadata.custom_name_format:
            name_format = self.metadata.custom_name_format

        # This suffix is always added to the footprint name, as it is important for the 3D model
        always_suffix = ""

        if self.top_slug:
            always_suffix = "_" + self.top_slug.get_name_suffix()

        suffix = spec.get("suffix", "")

        if always_suffix:
            suffix = always_suffix + suffix

        self.fp_name_without_vias = (
            name_format.format(
                man=self.metadata.manufacturer or "",
                mpn=self.metadata.part_number or "",
                pkg=self.device_type,
                pincount=pincount_text,
                size_y=size_y,
                size_x=size_x,
                pitch=spec["pitch"],
                ep_size_x=ep_size_x,
                ep_size_y=ep_size_y,
                mask_size_x=self.ep_mask_x.nominal,
                mask_size_y=self.ep_mask_y.nominal,
                suffix=suffix,
                suffix2="",
                vias="",
            )
            .replace("__", "_")
            .lstrip("_")
        )

        self.fp_name_with_vias = (
            name_format.format(
                man=self.metadata.manufacturer or "",
                mpn=self.metadata.part_number or "",
                pkg=self.device_type,
                pincount=pincount_text,
                size_y=size_y,
                size_x=size_x,
                pitch=spec["pitch"],
                ep_size_x=ep_size_x,
                ep_size_y=ep_size_y,
                mask_size_x=self.ep_mask_x.nominal,
                mask_size_y=self.ep_mask_y.nominal,
                suffix=suffix,
                suffix2="",
                vias=self._spec.get("thermal_via_suffix", "_ThermalVias"),
            )
            .replace("__", "_")
            .lstrip("_")
        )

        if self.device_type:
            suffix_3d = (
                suffix
                if spec.get("include_suffix_in_3dpath", "True") == "True"
                else always_suffix
            )
            self.model_name = (
                name_format.format(
                    man=self.metadata.manufacturer or "",
                    mpn=self.metadata.part_number or "",
                    pkg=self.device_type,
                    pincount=pincount_text,
                    size_y=size_y,
                    size_x=size_x,
                    pitch=spec["pitch"],
                    ep_size_x=ep_size_x,
                    ep_size_y=ep_size_y,
                    mask_size_x=self.ep_mask_x.nominal,
                    mask_size_y=self.ep_mask_y.nominal,
                    suffix=suffix_3d,
                    suffix2="",
                    vias="",
                )
                .replace("__", "_")
                .lstrip("_")
            )
        else:
            self.model_name = self.pkg_id

    def _compose_lib_name(self) -> None:
        if destination_dir := self._spec.get("destination_dir"):
            self.lib_name = destination_dir
        elif self._header and "override_lib_name" in self._header:
            self.lib_name = self._header["override_lib_name"]
        else:
            self.lib_name = self._config["lib_name_format_string"].format(
                category=self._header.get("library_Suffix", "DFN_QFN")
            )

    @property
    def spec_dictionary(self) -> dict[str, Any]:
        """
        Get the raw spec dictionary.

        This is only temporary, and can be piecewise replaced by
        type-safe declarative definitions, but that requires deep changes
        """
        return self._spec

    @property
    def has_top_slug(self) -> bool:
        return self.top_slug is not None
