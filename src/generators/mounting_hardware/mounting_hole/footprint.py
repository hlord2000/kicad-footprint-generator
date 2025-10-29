#!/usr/bin/env python3

"""
Mounting Hole generator
Based on Fiducial generator

@author Kliment
@author Bence Csókás
"""

import argparse
import math
from dataclasses import asdict, dataclass

from KicadModTree import *  # NOQA
from kilibs.geom import GeomCircle
from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files.global_config import GlobalConfig


class MountingHoleGenerator(FootprintGenerator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @dataclass
    class FPconfiguration:
        library_name: str
        fp_name: str
        # @param drill_diameter diameter of drilled hole
        drill: float
        # @param marking_width diameter of marker circle or line width of cross
        courtyard_offset: float
        # @param Optional thread name
        thread: str
        # @param comment to be added to end of size description
        comment: str
        # @param styles of footprint to emit - list of keys and mechanical sizes
        styles: dict
        pth: str
        standard: str
        mech: float
        styledesc: str
        stylestring: str
        suffix: str
        via_size: float

        def __init__(self, spec: dict, global_config: GlobalConfig):
            self.library_name = spec.get("library", "Fiducial")
            self.fp_name = spec["fp_name"]
            self.drill = spec["drill"]
            self.mech = spec.get("mech", self.drill)
            self.styledesc = ""
            self.stylestring = ""
            self.thread = spec.get("thread", "")
            self.comment = spec.get("comment", "")
            self.styles = spec.get("styles", {})
            self.suffix = spec.get("suffix", "")
            self.via_size = spec["via_size"]
            self.description = spec.get("description", "")
            self.courtyard_offset = spec.get(
                "courtyard_offset",
                global_config.get_courtyard_offset(GlobalConfig.CourtyardType.DEFAULT),
            )

        def formatString(self, s: str) -> str:
            return s.format(**asdict(self))

        def getFootprintName(self) -> str:
            return self.formatString(self.fp_name)

        def getDescription(self) -> str:
            return self.formatString(self.description)

        def expandVariants(self) -> list:
            variants = []
            for style in self.styles.keys():
                if style == "npth":
                    variants.append(
                        {
                            "pth": "none",
                            "mech": self.styles[style],
                            "comment": "no annular",
                        }
                    )
                elif style == "pth":
                    variants.append(
                        {"pth": "all", "mech": self.styles[style], "suffix": "Pad"}
                    )
                    variants.append(
                        {
                            "pth": "top",
                            "mech": self.styles[style],
                            "suffix": "Pad_TopOnly",
                        }
                    )
                    variants.append(
                        {
                            "pth": "TB",
                            "mech": self.styles[style],
                            "suffix": "Pad_TopBottom",
                        }
                    )
                    variants.append(
                        {"pth": "via", "mech": self.styles[style], "suffix": "Pad_Via"}
                    )
                elif style in ["DIN965", "ISO7380", "ISO14580"]:
                    variants.append(
                        {
                            "pth": "none",
                            "standard": style,
                            "mech": self.styles[style],
                            "comment": "no annular",
                        }
                    )
                    variants.append(
                        {
                            "pth": "all",
                            "standard": style,
                            "mech": self.styles[style],
                            "suffix": "Pad",
                        }
                    )
                    variants.append(
                        {
                            "pth": "top",
                            "standard": style,
                            "mech": self.styles[style],
                            "suffix": "Pad_TopOnly",
                        }
                    )
                    variants.append(
                        {
                            "pth": "TB",
                            "standard": style,
                            "mech": self.styles[style],
                            "suffix": "Pad_TopBottom",
                        }
                    )
            return variants

        def setVariant(self, variant: dict):
            self.pth = variant.get("pth", "none")
            self.standard = variant.get("standard", "")
            self.mech = variant.get("mech", "")
            var_suffix = variant.get("suffix", "")
            var_comment = variant.get("comment", "")
            self.styledesc = ""
            self.stylestring = ""
            if self.thread != "":
                self.styledesc += f", {self.thread:s}"
                self.stylestring += f"_{self.thread:s}"
            if var_comment != "":
                self.styledesc += f", {var_comment:s}"
            if self.comment != "":
                self.styledesc += f", {self.comment:s}"
            if self.standard != "":
                self.stylestring += f"_{self.standard:s}"
            if var_suffix != "":
                self.stylestring += f"_{var_suffix:s}"
            if self.suffix != "":
                self.stylestring += f"_{self.suffix:s}"
            self.styledesc += ", generated by kicad-footprint-generator mountinghole.py"

    def generateFootprint(self, spec: dict, pkg_id: str, header_info: dict):
        fp_config = self.FPconfiguration(spec, self.global_config)
        for variant in fp_config.expandVariants():
            fp_config.setVariant(variant)
            self.generateFootprintVariant(fp_config)

    def _add_via_ring(
        self, fp: Footprint, fp_config: FPconfiguration, via_count: int = 8
    ):
        ring_radius = fp_config.mech / 2 - (fp_config.mech - fp_config.drill) / 4
        for i in range(via_count):
            angle = i * 2 * math.pi / via_count
            via_position = Vector2D(
                math.cos(angle) * ring_radius, math.sin(angle) * ring_radius
            )
            pad = Pad(
                type=Pad.TYPE_THT,
                shape=Pad.SHAPE_CIRCLE,
                at=via_position,
                layers=Pad.LAYERS_THT,
                size=fp_config.via_size + 0.3,
                drill=fp_config.via_size,
                number="1",
                zone_connection=Pad.ZoneConnection.SOLID,
            )
            fp.append(pad)

    def generateFootprintVariant(self, fp_config: FPconfiguration):
        # assemble footprint name
        fp_name = fp_config.getFootprintName()

        # information about what is generated
        print("  - %s" % fp_name)

        # create the footprint
        kicad_mod = Footprint(fp_name, FootprintType.UNSPECIFIED)
        kicad_mod.excludeFromBOM = True
        kicad_mod.excludeFromPositionFiles = True

        # set the FP description
        description = fp_config.getDescription()
        kicad_mod.description = description
        kicad_mod.tags = ["mountinghole"]
        if fp_config.thread != "":
            kicad_mod.tags += [f"{fp_config.thread:s}"]
        if fp_config.standard != "":
            kicad_mod.tags += [f"{fp_config.standard:s}"]

        center = Vector2D(0, 0)

        # draw body outline on F.Fab
        pad_radius = fp_config.mech / 2
        # fab_outline = Circle(center=center, radius=fp_config.mech/2, layer='F.Fab',
        #             width=self.global_config.fab_line_width)
        # kicad_mod.append(fab_outline)
        body_edges = GeomCircle(center=center, radius=pad_radius).bbox()

        # draw mechanical line
        fab_outline = Circle(
            center=center, radius=fp_config.mech / 2, layer="Cmts.User", width=0.15
        )
        kicad_mod.append(fab_outline)
        # create Pad
        pth = fp_config.pth
        if pth == "none":
            pad = Pad(
                type=Pad.TYPE_NPTH,
                shape=Pad.SHAPE_CIRCLE,
                at=center,
                layers=Pad.LAYERS_NPTH,
                size=fp_config.drill,
                drill=fp_config.drill,
            )
            kicad_mod.append(pad)
        elif pth == "all":
            pad = Pad(
                type=Pad.TYPE_THT,
                shape=Pad.SHAPE_CIRCLE,
                at=center,
                layers=Pad.LAYERS_THT,
                size=fp_config.mech,
                drill=fp_config.drill,
                number="1",
                zone_connection=Pad.ZoneConnection.SOLID,
            )
            kicad_mod.append(pad)
        elif pth == "via":
            pad = Pad(
                type=Pad.TYPE_THT,
                shape=Pad.SHAPE_CIRCLE,
                at=center,
                layers=Pad.LAYERS_THT,
                size=fp_config.mech,
                drill=fp_config.drill,
                number="1",
                zone_connection=Pad.ZoneConnection.SOLID,
            )
            kicad_mod.append(pad)
            self._add_via_ring(kicad_mod, fp_config)
        elif pth == "top":
            pad = Pad(
                type=Pad.TYPE_THT,
                shape=Pad.SHAPE_CIRCLE,
                at=center,
                layers=Pad.LAYERS_THT,
                size=fp_config.drill + 0.4,
                drill=fp_config.drill,
                number="1",
                zone_connection=Pad.ZoneConnection.SOLID,
            )
            kicad_mod.append(pad)
            pad = Pad(
                type=Pad.TYPE_CONNECT,
                shape=Pad.SHAPE_CIRCLE,
                at=center,
                layers=Pad.LAYERS_CONNECT_FRONT,
                size=fp_config.mech,
                number="1",
                zone_connection=Pad.ZoneConnection.SOLID,
            )
            kicad_mod.append(pad)
        elif pth == "TB":
            pad = Pad(
                type=Pad.TYPE_THT,
                shape=Pad.SHAPE_CIRCLE,
                at=center,
                layers=Pad.LAYERS_THT,
                size=fp_config.drill + 0.4,
                drill=fp_config.drill,
                number="1",
                zone_connection=Pad.ZoneConnection.SOLID,
            )
            kicad_mod.append(pad)
            pad = Pad(
                type=Pad.TYPE_CONNECT,
                shape=Pad.SHAPE_CIRCLE,
                at=center,
                layers=Pad.LAYERS_CONNECT_FRONT,
                size=fp_config.mech,
                number="1",
                zone_connection=Pad.ZoneConnection.SOLID,
            )
            kicad_mod.append(pad)
            pad = Pad(
                type=Pad.TYPE_CONNECT,
                shape=Pad.SHAPE_CIRCLE,
                at=center,
                layers=Pad.LAYERS_CONNECT_BACK,
                size=fp_config.mech,
                number="1",
                zone_connection=Pad.ZoneConnection.SOLID,
            )
            kicad_mod.append(pad)

        # calculate Courtyard
        cy_radius = fp_config.mech / 2 + fp_config.courtyard_offset
        cy_outline = Circle(
            center=[0, 0],
            radius=cy_radius,
            layer="F.CrtYd",
            width=self.global_config.courtyard_line_width,
        )
        kicad_mod.append(cy_outline)
        courtyard = GeomCircle(center=center, radius=cy_radius).bbox()

        # text fields
        addTextFields(kicad_mod, self.global_config, body_edges, courtyard, fp_name)

        lib_name = fp_config.library_name
        self.write_footprint(kicad_mod, lib_name)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="use config .yaml files to create footprints."
    )
    parser.add_argument(
        "files",
        metavar="file",
        type=str,
        nargs="*",
        help="list of files holding information about what devices should be created.",
    )
    args = FootprintGenerator.add_standard_arguments(parser)

    FootprintGenerator.run_on_files(MountingHoleGenerator, args)
