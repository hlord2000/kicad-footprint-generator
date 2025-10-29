#!/usr/bin/env python3

"""
Fiducial marking generator

@author Bence Csókás
"""

import argparse
from dataclasses import dataclass, asdict
import enum
from typing import Any

from kilibs.geom import GeomCircle, Vector2D
from KicadModTree import Footprint, FootprintType, Circle, Pad, Rectangle
from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files.global_config import GlobalConfig


class MarkingType(enum.Enum):
    """Enum for marking types."""

    CIRCLE = "circle"
    CROSS = "cross"


class FiducialGenerator(FootprintGenerator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @dataclass
    class FPconfiguration:

        library_name: str
        fp_name: str
        """Footprint name pattern"""
        mask_diameter: float
        """Diameter of soldermask and F.Fab circle."""
        marking_type: MarkingType
        """Type (shape) of marking"""
        marking_size: float
        """Diameter of marker circle or line width of cross."""
        marking_width: float | None
        """Width of the marking line, if it is a cross."""
        courtyard_offset: float
        pad_clearance_outset: float
        """Extra clearance around the pad beyond the solder mask aperture.

        If the clearance is exactly the same as the mask aperture, then
        tolerance issues in the polygonal void in a zone fill can cause
        DRC to detect bridging between the pad and a surrounding fill.

        Ideally, have this large enough so there is a better
        chance that the zone doesn't peek out of the mask aperture if slightly
        misaligned when manufactured but without taking too much of a bite
        from the fill.
        """
        description: str
        """Footprint description."""
        comment: str
        """To be added to end of size description."""

        def __init__(self, spec: dict[str, Any], global_config: GlobalConfig):

            self.library_name = spec.get("library", "Fiducial")
            self.fp_name = spec["fp_name"]
            self.mask_diameter = spec["mask_diameter"]
            self.marking_size = spec["marking_size"]
            self.marking_width = spec.get("marking_width", None)
            self.comment = spec.get("comment", "")
            self.description = spec.get("description", "")
            self.courtyard_offset = spec.get(
                "courtyard_offset",
                global_config.get_courtyard_offset(GlobalConfig.CourtyardType.DEFAULT),
            )

            self.pad_clearance_outset = spec["pad_clearance_outset"]

            if "marking_type" not in spec:
                raise ValueError(
                    "marking_type must be specified in the spec, "
                    "e.g., 'marking_type: circle' or 'marking_type: cross'"
                )

            match spec["marking_type"]:
                case "circle":
                    self.marking_type = MarkingType.CIRCLE
                case "cross":
                    self.marking_type = MarkingType.CROSS
                case _:
                    raise ValueError(f"Unknown marking_type: {spec['marking_type']}")

        def formatString(self, pattern: str) -> str:

            format_params = asdict(self)

            # Fill in non-default variant parameters
            if self.marking_type == MarkingType.CIRCLE:
                format_params["shape"] = ""
                format_params["human_variant"] = ", circular marking"
            elif self.marking_type == MarkingType.CROSS:
                format_params["shape"] = "Cross"
                format_params["human_variant"] = ", cross variant"

            s = pattern.format(**format_params)

            return s.replace("__", "_")

        def getFootprintName(self) -> str:
            return self.formatString(self.fp_name)

        def getDescription(self) -> str:
            return self.formatString(self.description)

    def generateFootprint(
        self, spec: dict[str, Any], pkg_id: str, header_info: dict[str, Any]
    ) -> None:
        fp_config = self.FPconfiguration(spec, self.global_config)

        # assemble footprint name
        fp_name = fp_config.getFootprintName()

        # information about what is generated
        print("  - %s" % fp_name)

        # create the footprint
        kicad_mod = Footprint(fp_name, FootprintType.SMD)
        kicad_mod.excludeFromBOM = True

        # By default, the fiducial is in the position files
        kicad_mod.excludeFromPositionFiles = False

        # set the FP description
        description = fp_config.getDescription()
        kicad_mod.description = description
        kicad_mod.tags = ["fiducial"]

        center = Vector2D(0, 0)

        # draw body outline on F.Fab
        radius = fp_config.mask_diameter / 2
        fab_outline = Circle(center=center, radius=radius, layer='F.Fab',
                     width=self.global_config.fab_line_width)
        kicad_mod.append(fab_outline)
        body_edges = GeomCircle(center=center, radius=radius).bbox()

        # handle variants
        if fp_config.marking_type == MarkingType.CROSS:

            assert fp_config.marking_width is not None

            rect_size = Vector2D.from_floats(
                fp_config.marking_size, fp_config.marking_width
            )

            # cross in the middle
            primitives = [
                Rectangle(
                    center=Vector2D.zero(),
                    size=rect_size,
                    layer="F.Cu",
                    width=0,
                    fill=True,
                ),
                Rectangle(
                    center=Vector2D.zero(),
                    size=Vector2D.from_floats(rect_size.y, rect_size.x),
                    layer="F.Cu",
                    width=0,
                    fill=True,
                ),
            ]

            kicad_mod += Pad(
                type=Pad.TYPE_SMT,
                shape=Pad.SHAPE_CUSTOM,
                at=center,
                layers=["F.Cu", "F.Mask"],
                size=fp_config.marking_width,
                primitives=primitives,
            )
            pad_circle_size = fp_config.marking_width
        else:
            pad_circle_size = fp_config.marking_size

        # We always add the circle pad, because it also makes the soldermask and fill
        # clearance.
        pad_mask_clearance = radius - pad_circle_size / 2
        pad_clearance = pad_mask_clearance + fp_config.pad_clearance_outset

        pad = Pad(
            type=Pad.TYPE_SMT,
            shape=Pad.SHAPE_CIRCLE,
            at=center,
            layers=["F.Cu", "F.Mask"],
            size=pad_circle_size,
            clearance=pad_clearance,
            solder_mask_margin=pad_mask_clearance,
        )
        kicad_mod.append(pad)

        # calculate CourtYard
        cy_radius = radius + fp_config.courtyard_offset
        cy_outline = Circle(center=[0, 0], radius=cy_radius, layer='F.CrtYd',
                    width=self.global_config.courtyard_line_width)
        kicad_mod.append(cy_outline)
        courtyard = GeomCircle(center=center, radius=cy_radius).bbox()

        # text fields
        addTextFields(kicad_mod, self.global_config, body_edges, courtyard, fp_name)

        lib_name = fp_config.library_name
        self.write_footprint(kicad_mod, lib_name)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='use config .yaml files to create footprints.')
    parser.add_argument(
        "files",
        metavar="file",
        type=str,
        nargs="*",
        help="list of files holding information about what devices should be created.",
    )
    args = FootprintGenerator.add_standard_arguments(parser)

    FootprintGenerator.run_on_files(FiducialGenerator, args)
