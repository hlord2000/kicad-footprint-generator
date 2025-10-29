#!/usr/bin/env python3

"""
TerminalBlock Barrier generator

@author Philippe Hartmann (harty911)
"""

import argparse
from typing import Any

import scripts.tools.drawing_tools as DT
from KicadModTree import (
    Footprint,
    FootprintType,
    Model,
    Pad,
    Property,
    Rectangle,
    Translation,
)
from kilibs.declarative_defs.packages.terminal_block_barrier_properties import (
    TerminalBlockBarrierProperties,
)
from kilibs.geom import Direction, GeomRectangle, Vector2D
from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.footprint_scripts_terminal_blocks import (
    make_silk_outline_with_pin1_arrow,
)
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files.global_config import GlobalConfig


class TerminalBlockBarrierGenerator(FootprintGenerator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def generateFootprintVariant(self, cfg: TerminalBlockBarrierProperties, n_pin: int):
        #    """ Generate one footprints variant (by pin number)"""

        footprint_name = cfg.getFootprintName(n_pin)
        print(f"  - {footprint_name}")

        courtyard_offset = self.global_config.get_courtyard_offset(
            GlobalConfig.CourtyardType.CONNECTOR
        )

        # Footprint Assembly Board outline
        cell_size = Vector2D(cfg.cell_size.x, cfg.cell_size.y)
        fab_rect = GeomRectangle(
            start=(
                -(cell_size.x / 2 + cfg.side_border),
                -(cell_size.y / 2 + cfg.back_border),
            ),
            size=(
                (n_pin - 1) * cfg.pitch + cell_size.x + cfg.side_border * 2,
                cell_size.y + cfg.back_border,
            ),
        )
        silk_rect = fab_rect.inflated(self.global_config.silk_line_width)
        crt_rect = fab_rect.inflated(courtyard_offset).round_to_grid(
            grid=self.global_config.courtyard_grid, outwards=True
        )

        # Meta
        description = (
            f"{cfg.lib_description}, {cfg.metadata.manufacturer} {cfg.metadata.part_number}, {n_pin} pins, pitch {cfg.pitch:.3g}mm, "
            f"size {fab_rect.size.x:.3g}x{fab_rect.size.y:.3g}mm, "
            f"drill diameter {cfg.drill_diameter:.3g}mm, pad size {max(cfg.pad_size):.3g}mm, "
            f"{cfg.metadata.datasheet}, "
            f"{self.global_config.get_generated_by_description('https://gitlab.com/kicad/libraries/kicad-footprint-generator/-/tree/master/scripts/TerminalBlock_Barrier')}"
        )
        tags = ["THT"]

        # create the footprint
        kicad_mod = Footprint(footprint_name, FootprintType.THT)
        kicad_mod.description = description
        kicad_mod.tags = tags
        kicad_draw = Translation(0, cfg.back_border + cell_size.y / 2 - cfg.pad_to_back)
        kicad_mod.append(kicad_draw)

        addTextFields(
            kicad_mod=kicad_draw,
            configuration=self.global_config,
            body_edges=fab_rect,
            courtyard=crt_rect,
            fp_name=footprint_name,
            text_y_inside_position=cfg.ref_y_position,
        )

        for n in range(1, n_pin + 1):
            pos = Vector2D((n - 1) * cfg.pitch, 0)
            kicad_mod.append(
                Pad(
                    number=n,
                    type=Pad.TYPE_THT,
                    shape=Pad.SHAPE_ROUNDRECT if n == 1 else Pad.SHAPE_OVAL,
                    at=pos,
                    size=cfg.pad_size,
                    drill=cfg.drill_diameter,
                    layers=Pad.LAYERS_THT,
                    round_radius_handler=self.global_config.roundrect_radius_handler,
                )
            )

            # Cell
            kicad_draw.append(
                Rectangle(
                    start=pos - cell_size / 2,
                    end=pos + cell_size / 2,
                    width=self.global_config.fab_line_width,
                    layer="F.Fab",
                )
            )

            # Screw
            screw_pos = pos - Vector2D(0, cfg.screw_offset)
            DT.addSlitScrew(
                kicad_draw,
                screw_pos,
                cfg.screw_diameter / 2,
                "F.Fab",
                self.global_config.fab_line_width,
            )

            # Screw base
            base = Vector2D(cfg.screw_base_size.x, cfg.screw_base_size.y)
            kicad_draw.append(
                Rectangle(
                    start=screw_pos - base / 2,
                    end=screw_pos + base / 2,
                    width=self.global_config.fab_line_width,
                    layer="F.Fab",
                )
            )

            # Screw base extensions
            ext = Vector2D(base.x / 2, base.y / 5)
            kicad_draw.append(
                Rectangle(
                    start=screw_pos + Vector2D(-ext.x / 2, -base.y / 2 - ext.y),
                    end=screw_pos + Vector2D(ext.x / 2, -base.y / 2),
                    width=self.global_config.fab_line_width,
                    layer="F.Fab",
                )
            )
            kicad_draw.append(
                Rectangle(
                    start=screw_pos + Vector2D(-ext.x / 2, +base.y / 2),
                    end=screw_pos + Vector2D(ext.x / 2, +base.y / 2 + ext.y),
                    width=self.global_config.fab_line_width,
                    layer="F.Fab",
                )
            )

        kicad_draw.append(
            Rectangle(
                shape=fab_rect, width=self.global_config.fab_line_width, layer="F.Fab"
            )
        )

        kicad_draw += make_silk_outline_with_pin1_arrow(
            silk_rect,
            0,
            self.global_config.silk_line_width,
            keepouts=[],
            pin1_keepouts=[],
            arrow_direction=Direction.SOUTH,
        )

        # create courtyard
        kicad_draw.append(
            Rectangle(
                shape=crt_rect,
                layer="F.CrtYd",
                width=self.global_config.courtyard_line_width,
            )
        )

        # 3D model definition
        self.add_standard_3d_model_to_footprint(kicad_mod, cfg.lib_name, footprint_name)

        self.write_footprint(kicad_mod, cfg.lib_name)

    """ Generate a serie of footprints (pin number range)"""

    def generateFootprint(
        self, spec: dict[str, Any], pkg_id: str, header_info: dict[str, Any]
    ) -> None:

        cfg = TerminalBlockBarrierProperties(spec, pkg_id)

        for n_pin in cfg.n_pin_variants:
            self.generateFootprintVariant(cfg, n_pin)


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

    FootprintGenerator.run_on_files(TerminalBlockBarrierGenerator, args)
