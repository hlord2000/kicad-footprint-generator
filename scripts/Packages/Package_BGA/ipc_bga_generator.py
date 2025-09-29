#!/usr/bin/env python3

import argparse
import logging
import math
import os
from typing import Any

from KicadModTree import (
    Footprint,
    FootprintType,
    Pad,
    PolygonLine,
    Property,
    RectLine,
    ReferencedPad,
    RoundRadiusHandler,
    Text,
)
from kilibs.geom import Direction, Vector2D
from scripts.tools.declarative_def_tools import (
    ast_evaluator,
    fp_additional_drawing,
)
from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.global_config_files import global_config as GC
from scripts.tools.nodes import pin1_arrow
from src.generators.BGA.bga_configuration import (
    BGAConfiguration,
    LayoutData,
    load_config,
)


class BGAGenerator(FootprintGenerator):
    def __init__(self, configuration: dict[str, Any], **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)  # type: ignore

        self.configuration = configuration

    def generateFootprint(
        self,
        device_params: dict[str, Any],
        pkg_id: str,
        header_info: dict[str, Any] | None = None,
    ) -> None:
        # Thin wrapper around generateBGAFootprint
        logging.info(f"Generating BGA footprint: {pkg_id}")
        self.generateBGAFootprint(
            self.configuration, device_params, pkg_id, header_info
        )

    def generateBGAFootprint(
        self,
        config: dict[str, Any],
        fpParams: dict[str, Any],
        fpId: str,
        header_info: dict[str, Any] | None = None,
    ) -> None:
        device_config = BGAConfiguration(fpId, fpParams, header_info, config)
        if device_config.has_fp_data:
            if "pad_diameter" in fpParams:
                pad_diameter = fpParams["pad_diameter"]
                logging.info(
                    f"Pad size of {fpId} is set by the footprint definition. "
                    "This should only be done for manufacturer-specific footprints."
                )
            elif "ball_type" in fpParams and "ball_diameter" in fpParams:
                ball_diameter = fpParams["ball_diameter"]
                ball_type = fpParams["ball_type"]
                # IPC-7352 Table 3-11 Median (Nominal) Material Level B
                if ball_type == "collapsible":
                    pad_diameter = round(0.8 * ball_diameter, 2)
                elif ball_type == "non-collapsible":
                    pad_diameter = round(1.1 * ball_diameter, 2)
                else:
                    raise KeyError(
                        f"{fpId}: '{ball_type}' is an invalid ball type. Only "
                        "'collapsible' and 'non-collapsible' are accepted values. "
                        "Aborting."
                    )
            elif "ball_type" in fpParams and "ball_diameter" not in fpParams:
                raise KeyError(f"{fpId}: Ball diameter is missing. Aborting.")
            elif "ball_diameter" in fpParams and "ball_type" not in fpParams:
                raise KeyError(f"{fpId}: Ball type is missing. Aborting.")
            else:
                raise KeyError(
                    f"{fpId}: The config file must include 'ball_type' and "
                    "'ball_diameter' or 'pad_diameter'. Aborting."
                )
            fpParams["pad_size"] = [pad_diameter, pad_diameter]
            self._createFootprintVariant(device_config)

    def _createFootprintVariant(self, bga_conf: BGAConfiguration) -> None:
        # Pull out the old-style parameter dictionary
        spec = bga_conf.spec

        evaluator_params = {"pitch": bga_conf.pitch}

        fp_evaluator = ast_evaluator.ASTevaluator(symbols=evaluator_params)  # type: ignore

        pkg_x = bga_conf.body_size_x
        pkg_y = bga_conf.body_size_y
        f_fab_ref_rot = 0.0

        f = Footprint(bga_conf.name, FootprintType.SMD)
        if "mask_margin" in spec:
            f.setMaskMargin(spec["mask_margin"])
        if "paste_margin" in spec:
            f.setPasteMargin(spec["paste_margin"])
        if "paste_ratio" in spec:
            f.setPasteMarginRatio(spec["paste_ratio"])

        s1 = [1.0, 1.0]
        if pkg_x < 4.3 and pkg_y > pkg_x:
            s2 = [
                min(1.0, round(pkg_y / 4.3, 2))
            ] * 2  # Y size is greater, so rotate F.Fab reference
            f_fab_ref_rot = -90.0
        else:
            s2 = [min(1.0, round(pkg_x / 4.3, 2))] * 2

        t1 = 0.15 * s1[0]
        t2 = 0.15 * s2[0]

        chamfer = self.global_config.fab_bevel.get_chamfer_size(min(pkg_x, pkg_y))

        crtYdOffset = self.global_config.get_courtyard_offset(
            GC.GlobalConfig.CourtyardType.BGA
        )

        def crt_round(x: float) -> float:
            # Round away from zero for proper courtyard calculation
            neg = x < 0
            if neg:
                x = -x
            x = math.ceil(x * 100) / 100.0
            if neg:
                x = -x
            return x

        pitchX, pitchY, staggered = bga_conf.calculate_stagger()

        xCenter = 0.0
        xLeftFab = xCenter - pkg_x / 2.0
        xRightFab = xCenter + pkg_x / 2.0
        xChamferFab = xLeftFab + chamfer
        xPadLeft = xCenter - pitchX * ((bga_conf.layout_x - 1) / 2.0)
        xLeftCrtYd = crt_round(xCenter - (pkg_x / 2.0 + crtYdOffset))
        xRightCrtYd = crt_round(xCenter + (pkg_x / 2.0 + crtYdOffset))

        yCenter = 0.0
        yTopFab = yCenter - pkg_y / 2.0
        yBottomFab = yCenter + pkg_y / 2.0
        yChamferFab = yTopFab + chamfer
        yPadTop = yCenter - pitchY * ((bga_conf.layout_y - 1) / 2.0)
        yTopCrtYd = crt_round(yCenter - (pkg_y / 2.0 + crtYdOffset))
        yBottomCrtYd = crt_round(yCenter + (pkg_y / 2.0 + crtYdOffset))
        yRef = yTopFab - 1.0
        yValue = yBottomFab + 1.0

        wFab = self.global_config.fab_line_width
        wCrtYd = self.global_config.courtyard_line_width
        wSilkS = self.global_config.silk_line_width

        # silkOffset should comply with pad clearance as well
        yPadTopEdge = yPadTop - spec["pad_size"][1] / 2.0
        xPadLeftEdge = xPadLeft - spec["pad_size"][0] / 2.0

        xSilkOffset = max(
            self.global_config.silk_fab_offset,
            xLeftFab + self.global_config.silk_pad_offset - xPadLeftEdge,
        )
        ySilkOffset = max(
            self.global_config.silk_fab_offset,
            yTopFab + self.global_config.silk_pad_offset - yPadTopEdge,
        )

        silkSizeX = pkg_x + 2 * (xSilkOffset - self.global_config.silk_fab_offset)
        silkSizeY = pkg_y + 2 * (ySilkOffset - self.global_config.silk_fab_offset)

        silkChamfer = self.global_config.fab_bevel.get_chamfer_size(
            min(silkSizeX, silkSizeY)
        )

        xLeftSilk = xLeftFab - xSilkOffset
        xRightSilk = xRightFab + xSilkOffset
        xChamferSilk = xLeftSilk + silkChamfer
        yTopSilk = yTopFab - ySilkOffset
        yBottomSilk = yBottomFab + ySilkOffset
        yChamferSilk = yTopSilk + silkChamfer

        # Text
        f.append(
            Property(
                name=Property.REFERENCE,
                text="REF**",
                at=[xCenter, yRef],
                layer="F.SilkS",
                size=s1,
                thickness=t1,
            )
        )
        f.append(
            Property(
                name=Property.VALUE,
                text=bga_conf.name,
                at=[xCenter, yValue],
                layer="F.Fab",
                size=s1,
                thickness=t1,
            )
        )
        f.append(
            Text(
                text="${REFERENCE}",
                at=[xCenter, yCenter],
                layer="F.Fab",
                size=s2,
                thickness=t2,
                rotation=f_fab_ref_rot,
            )
        )

        # Fab
        f.append(
            PolygonLine(
                shape=[
                    [xRightFab, yBottomFab],
                    [xLeftFab, yBottomFab],
                    [xLeftFab, yChamferFab],
                    [xChamferFab, yTopFab],
                    [xRightFab, yTopFab],
                    [xRightFab, yBottomFab],
                ],
                layer="F.Fab",
                width=wFab,
            )
        )

        # Courtyard
        f.append(
            RectLine(
                start=[xLeftCrtYd, yTopCrtYd],
                end=[xRightCrtYd, yBottomCrtYd],
                layer="F.CrtYd",
                width=wCrtYd,
            )
        )

        # Silk

        arrow_apex = Vector2D(xLeftSilk, yTopSilk)
        min_arrow_size = wSilkS * 3
        arrow_size = max(min_arrow_size, crtYdOffset / 2)

        f.append(
            pin1_arrow.Pin1SilkScreenArrow45Deg(
                arrow_apex, Direction.SOUTHEAST, arrow_size, "F.SilkS", wSilkS
            )
        )

        f.append(
            PolygonLine(
                shape=[
                    [xChamferSilk, yTopSilk],
                    [xRightSilk, yTopSilk],
                    [xRightSilk, yBottomSilk],
                    [xLeftSilk, yBottomSilk],
                    [xLeftSilk, yChamferSilk],
                ],
                layer="F.SilkS",
                width=wSilkS,
            )
        )

        # Pads
        for layout_data in bga_conf.layout_data_list:
            self._make_pad_grid(
                f, layout_data, bga_conf, x_center=xCenter, y_center=yCenter
            )

        dwg_nodes = fp_additional_drawing.create_additional_drawings(  # type: ignore
            bga_conf.additional_drawings, self.global_config, fp_evaluator
        )
        f.extend(dwg_nodes)

        if staggered:
            pdesc = str(spec.get("pitch")) if "pitch" in spec else f"{pitchX}x{pitchY}"
            sdesc = f"{staggered.upper()}-staggered "
        else:
            pdesc = str(pitchX) if pitchX == pitchY else f"{pitchX}x{pitchY}"
            sdesc = ""

        description_parts = [
            bga_conf.metadata.description if bga_conf.metadata.description else "",
            f"{pkg_x}x{pkg_y}mm",
            f"{bga_conf.num_balls} Ball",
            f"{sdesc}{bga_conf.layout_x}x{bga_conf.layout_y} Layout",
            f"{pdesc}mm Pitch",
            f"generated with kicad-footprint-generator {os.path.basename(__file__)}",
        ]

        if bga_conf.metadata.datasheet:
            description_parts.append(bga_conf.metadata.datasheet)

        f.description = ", ".join(description_parts)

        f.tags = [bga_conf.package_type, str(bga_conf.num_balls), pdesc]
        f.tags += bga_conf.metadata.compatible_mpns
        f.tags += bga_conf.metadata.additional_tags

        # #################### Output and 3d model ############################
        self.add_standard_3d_model_to_footprint(f, bga_conf.lib_name, bga_conf.name)
        self.write_footprint(f, bga_conf.lib_name)

    def _make_pad_grid(
        self,
        f: Footprint,
        layout_info: LayoutData,
        bga_conf: BGAConfiguration,
        x_center: float = 0.0,
        y_center: float = 0.0,
    ) -> None:
        layout_dict = layout_info.layout_dict
        spec = bga_conf.spec
        pad_data_list = layout_info.pad_data_list

        pad_shape = layout_dict.get("pad_shape", spec.get("pad_shape", "circle"))
        paste_shape = layout_dict.get("paste_shape", spec.get("paste_shape"))

        if paste_shape and paste_shape != pad_shape:
            layers = ["F.Cu", "F.Mask"]
        else:
            layers = Pad.LAYERS_SMT

        ref_pad = Pad(
            number=pad_data_list[0].name,
            type=Pad.TYPE_SMT,
            fab_property=Pad.FabProperty.BGA,
            shape=pad_shape,
            at=pad_data_list[0].position,
            size=layout_dict.get("pad_size") or spec["pad_size"],
            layers=layers,
            radius_ratio=self.global_config.roundrect_radius_handler,  # type: ignore
        )
        f.append(ref_pad)

        ref_paste_pad: Pad | None = None

        if paste_shape and paste_shape != pad_shape:
            # Footgun warning: When pcbnew renders a paste-only pad like this, it actually
            # ignores all paste `margin settings both of the pad and of the footprint, and
            # creates a stencil opening of exactly the size of the pad. Thus, we have to
            # pre-compute paste margin here. Note that KiCad implements paste margin with an
            # actual geometric offset, i.e. yielding a rounded rect for square pads. Thus,
            # we have to implement similar offsetting logic here to stay consistent.

            pasteMargin = layout_dict.get("paste_margin", spec.get("paste_margin", 0))
            size = list(layout_dict.get("pad_size") or spec["pad_size"])
            corner_ratio = self.global_config.roundrect_radius_handler.radius_ratio

            if paste_shape == "circle":
                size[0] += 2 * pasteMargin
                size[1] += 2 * pasteMargin

            elif paste_shape == "rect":
                if pasteMargin <= 0:
                    size[0] += 2 * pasteMargin
                    size[1] += 2 * pasteMargin

                else:
                    corner_ratio = pasteMargin / min(size)
                    size[0] += 2 * pasteMargin
                    size[1] += 2 * pasteMargin
                    paste_shape = "roundrect"

            elif paste_shape == "roundrect":
                corner_radius = min(size) * corner_ratio
                size[0] += 2 * pasteMargin
                size[1] += 2 * pasteMargin
                corner_radius += pasteMargin

                if corner_radius < 0:
                    paste_shape = "rect"
                else:
                    corner_ratio = corner_radius / min(size)

            paste_radius_handler = RoundRadiusHandler(
                radius_ratio=corner_ratio,
            )

            ref_paste_pad = Pad(
                number="",
                type=Pad.TYPE_SMT,
                shape=paste_shape,
                at=pad_data_list[0].position,
                size=size,  # type: ignore
                layers=["F.Paste"],
                round_radius_handler=paste_radius_handler,
            )
            f.append(ref_paste_pad)

        for i in range(1, len(pad_data_list)):
            f.append(
                ReferencedPad(
                    reference_pad=ref_pad,
                    number=pad_data_list[i].name,
                    at=pad_data_list[i].position,
                )
            )
            if ref_paste_pad:
                f.append(
                    ReferencedPad(
                        reference_pad=ref_paste_pad,
                        number="",
                        at=pad_data_list[i].position,
                    )
                )


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
    parser.add_argument(
        "--global_config",
        type=str,
        nargs="?",
        help="the config file defining how the footprint will look like. (KLC)",
        default="../../tools/global_config_files/config_KLCv3.0.yaml",
    )
    parser.add_argument(
        "--naming_config",
        type=str,
        nargs="?",
        help="the config file defining footprint naming.",
        default="../package_config_KLCv3.yaml",
    )

    args = FootprintGenerator.add_standard_arguments(parser)  # type: ignore

    configuration = load_config(args.naming_config)

    FootprintGenerator.run_on_files(  # type: ignore
        BGAGenerator,
        args,
        file_autofind_dir="../../../data/BGA/",
        configuration=configuration,
    )
