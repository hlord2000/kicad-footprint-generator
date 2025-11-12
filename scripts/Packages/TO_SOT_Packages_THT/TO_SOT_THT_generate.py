#!/usr/bin/env python3


import argparse
import logging
import math
import os

import yaml

from KicadModTree import (
    Arc,
    Circle,
    Footprint,
    FootprintType,
    Line,
    Node,
    Pad,
    Property,
    Rectangle,
    Text,
    Translation,
)
from KicadModTree.util.courtyard_builder import CourtyardBuilder
from kilibs.geom import GeomRectangle
from kilibs.geom.operations import round_to_grid_e
from scripts.tools.declarative_def_tools import common_metadata
from scripts.tools.drawing_tools import (
    addCircleLF,
    addHDLineWithKeepout,
    addHLineWithKeepout,
    addKeepoutRect,
    addKeepoutRound,
    addRectAngledBottom,
    addRectAngledBottomNoTop,
    addRectAngledTop,
    addRectAngledTopNoBottom,
    addVDLineWithKeepout,
    addVLineWithKeepout,
    makeRectWithKeepout,
)
from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files import global_config


class CommonToPackage:
    """Class for properties common to both types of TO packages"""

    metadata: common_metadata.CommonMetadata

    def __init__(self, device_params: dict, pkg_id: str):
        try:
            self.pins: int = device_params["number_of_pins"]
            self.pad_dimensions: list[float] = device_params["pad_dimensions_xy"]
            self.drill: float = device_params["pad_hole_diameter"]
        except Exception as e:
            msg = f"Error in '{pkg_id}': Parameter '{e.args[0]}' must be provided!"
            print("\n" + msg + "\n")
            raise KeyError(msg)

        self.name_base: str = ""
        self.metadata = common_metadata.CommonMetadata(device_params)
        self.fpnametags = []
        self.additional_package_names: list[str] = device_params.get(
            "additional_package_names", []
        )
        self.device_type = device_params.get("device_type", "")

        if "device_type" in device_params:
            self.name_base = device_params["device_type"] + "-" + f"{self.pins}"
        else:
            self.name_base = pkg_id

    def init_footprint(self, description: str, tags: list[str], name: str):
        fp = Footprint(name, FootprintType.THT)
        fp.description = description
        fp.tags = tags
        return fp


class RectangularToPackage(CommonToPackage):
    """Class for properties of rectangular shaped TO packages"""

    def __init__(self, device_params: dict, pkg_id: str):
        super().__init__(device_params, pkg_id)
        try:
            self.plastic_dimensions: list[float] = device_params["plastic_dimensions_xyz"]  # fmt: skip
            self.pitch: float = device_params["pitch"]
        except Exception as e:
            msg = f"Error in '{pkg_id}': Parameter '{e.args[0]}' must be provided!"
            print("\n" + msg + "\n")
            raise KeyError(msg)

        self.metal_dimensions: list[float] = device_params.get(
            "metal_dimensions_xyz", [0, 0, 0]
        )
        self.metal_offset_x: float = device_params.get(
            "metal_offset_x", 0
        )  # offset of metal from left
        self.mounting_hole_position: list[int] = device_params.get(
            "mounting_hole_position", [0, 0]
        )
        self.mounting_hole_diameter: float = device_params.get(
            "mounting_hole_diameter_on_package", 0
        )
        self.mounting_hole_drill: float = device_params.get(
            "mounting_hole_diameter_on_pcb", 0
        )
        self.pin_min_length_before_90deg_bend: float = device_params.get(
            "pin_min_length_before_90deg_bend", 0
        )
        self.pin_width_height: list[float] = device_params.get(
            "pin_width_height", [0, 0]
        )
        self.pin_offset_x: float = 0
        self.pin_offset_z: float = device_params.get("pin_offset_z", 0)
        self.additional_pin_pad_size: list[float] = device_params.get(
            "additional_pin_pad_size", []
        )
        self.plastic_angled: list[float] = device_params.get("plastic_angled", [])
        self.metal_angled: list[float] = device_params.get("metal_angled", [])

        self.generate_footprint_type: int = device_params.get("generate_footprint_type")
        self.staggered_pitch: list[float] = device_params.get("staggered_pitch")
        self.pitch_list: list[float] = device_params.get("pitch_list", [])

        if self.pitch_list:
            self.pin_spread = sum(self.pitch_list)
        else:
            self.pin_spread = (self.pins - 1) * self.pitch
        self.pin_offset_x = (self.plastic_dimensions[0] - self.pin_spread) / 2

        # If pads are too wide, make them narrower for non-staggered devices
        if "staggered_pitch" not in device_params:
            self.pad_dimensions[0] = min(self.pad_dimensions[0], 0.75 * self.pitch)

    def init_footprint(
        self, orientation: str, modifier: str, staggered_type: int, config: dict
    ):
        description, tags, name = self._get_descr_tags_fpname(
            orientation, modifier, staggered_type, config
        )
        return super().init_footprint(description, tags, name)

    def _get_descr_tags_fpname(
        self, orientation: str, modifier: str, staggered_type: int, config: dict
    ):
        # Tags
        tags = [
            self.name_base,
            orientation,
            f"RM {self.pitch}mm",
        ] + self.metadata.additional_tags
        fpnametags = self.fpnametags
        if staggered_type == 1:
            tags.append("staggered type-1")
            fpnametags = ["StaggeredType1"] + fpnametags
        elif staggered_type == 2:
            tags.append("staggered type-2")
            fpnametags = ["StaggeredType2"] + fpnametags

        # Description
        description = self.name_base
        for tag in tags[1:]:
            description += ", " + tag
        if self.metadata.datasheet:
            description += ", see " + self.metadata.datasheet
        description += ", generated with kicad-footprint-generator {scriptname}".format(
            scriptname=os.path.basename(__file__)
        )

        # Footprint name
        if staggered_type > 0:
            name_format = config[
                "fp_name_to_tht_staggered_format_string_no_trailing_zero"
            ]
            if orientation == "Vertical":
                pitch_y = self.staggered_pitch[0]
                lead = pitch_y - self.plastic_dimensions[2] + self.pin_offset_z
            else:
                pitch_y = self.staggered_pitch[1]
                lead = pitch_y + self.pin_min_length_before_90deg_bend
            footprint_name = (
                name_format.format(
                    man=self.metadata.manufacturer or "",
                    mpn=self.metadata.part_number or "",
                    pkg=self.device_type,
                    pincount=self.pins,
                    pitch_x=2 * self.pitch,
                    pitch_y=pitch_y,
                    parity="Odd" if staggered_type == 1 else "Even",
                    lead=lead,
                    orientation=orientation if orientation == "Vertical" else modifier,
                )
                .replace("__", "_")
                .lstrip("_")
            )
        else:
            footprint_name = self.name_base
            if orientation == "Horizontal" and self.additional_pin_pad_size:
                footprint_name += "-1EP"
            for t in self.additional_package_names:
                footprint_name += "_" + t
            footprint_name += "_" + orientation
            if modifier:
                footprint_name += "_" + modifier
            for t in fpnametags:
                footprint_name += "_" + t
        return description, tags, footprint_name


class RoundToPackage(CommonToPackage):
    """Class for properties of round shaped TO packages"""

    def __init__(self, device_params: dict, pkg_id: str):
        super().__init__(device_params, pkg_id)
        try:
            self.pin_circle_diameter: float = device_params["pin_circle_diameter"]
            self.diameter_inner: float = device_params[
                "diameter_inner"
            ]  # diameter of top can
            self.diameter_outer: float = device_params[
                "diameter_outer"
            ]  # diameter of bottom can
        except Exception as e:
            msg = f"Error in '{pkg_id}': Parameter '{e.args[0]}' must be provided!"
            print("\n" + msg + "\n")
            raise KeyError(msg)

        self.mark_width: float = device_params.get("mark_width", 0)
        self.mark_length: float = device_params.get("mark_length", 0)
        self.pin1_angle: float = device_params.get("pin1_angle", 180)
        self.angle_between_pins: float = device_params.get(
            "angle_between_pins", -90 if self.pins == 3 else -360 / self.pins
        )
        self.mark_angle: float = device_params.get("mark_angle", self.pin1_angle + 45)
        self.window_diameter: float = device_params.get("window_diameter", 0)
        self.deleted_pins: list[int] = device_params.get("deleted_pins", [])

    def init_footprint(self, footprint_type: str):
        description, tags, name = self._get_descr_tags_fpname(footprint_type)
        return super().init_footprint(description, tags, name)

    def _get_descr_tags_fpname(self, footprint_type: str):
        # Tags
        name = self.name_base
        tags = []
        if footprint_type == "window" or footprint_type == "lens":
            name += "_" + footprint_type.capitalize()
            tags.append(footprint_type.capitalize())

        # Footprint name
        for t in self.additional_package_names:
            name += "_" + t
        for t in self.fpnametags:
            name += "_" + t

        # Description
        tags = [self.name_base] + tags + self.metadata.additional_tags
        description = self.name_base
        for t in tags[1:]:
            description += ", " + t
        if self.metadata.datasheet:
            description += ", see " + self.metadata.datasheet

        description += ", generated with kicad-footprint-generator {scriptname}".format(
            scriptname=os.path.basename(__file__)
        )

        return description, tags, name


class TOGenerator(FootprintGenerator):
    def __init__(self, configuration, **kwargs):
        super().__init__(**kwargs)
        self.configuration = configuration

    def save_footprint(self, fp: Footprint):
        self.add_standard_3d_model_to_footprint(fp, "Package_TO_SOT_THT", fp.name)
        self.write_footprint(fp, "Package_TO_SOT_THT")

    def generateFootprint(
        self, device_params: dict, pkg_id: str, header_info: dict = None
    ):
        footprint_type = device_params.get("generate_footprint_type", [])

        if isinstance(footprint_type, str):
            footprint_type = footprint_type.replace(" ", "")
            footprint_type = footprint_type.split(",")

        if "plastic_dimensions_xyz" in device_params:
            pkg = RectangularToPackage(device_params, pkg_id)
            if "vertical" in footprint_type:
                self.generate_rect_to_fp_vertical(pkg, pkg_id)
            if "horizontal" in footprint_type:
                self.generate_rect_to_fp_horizontal_tab_down(pkg, pkg_id)
                self.generate_rect_to_fp_horizontal_tab_up(pkg, pkg_id)
            if "vertical-odd" in footprint_type:
                self.generate_rect_to_fp_vertical(pkg, pkg_id, 1)
            if "vertical-even" in footprint_type:
                self.generate_rect_to_fp_vertical(pkg, pkg_id, 2)
            if "horizontal-odd" in footprint_type:
                self.generate_rect_to_fp_horizontal_tab_down(pkg, pkg_id, 1)
            if "horizontal-even" in footprint_type:
                self.generate_rect_to_fp_horizontal_tab_down(pkg, pkg_id, 2)
        elif "diameter_inner" in device_params:
            pkg = RoundToPackage(device_params, pkg_id)
            for type in footprint_type:
                self.generate_round_to_fp(pkg, pkg_id, type)

    def generate_rect_to_fp_vertical(
        self, pkg: RectangularToPackage, pkg_id: str, staggered_type: int = 0
    ):
        fp = pkg.init_footprint("Vertical", "", staggered_type, self.configuration)
        c = self.global_config
        courtyard_offset = self.global_config.get_courtyard_offset(
            global_config.GlobalConfig.CourtyardType.DEFAULT
        )

        width_fab_plastic = pkg.plastic_dimensions[0]
        height_fab_plastic = pkg.plastic_dimensions[2]
        left_fab_plastic = -pkg.pin_offset_x
        right_fab_plastic = left_fab_plastic + width_fab_plastic
        top_fab_plastic = -pkg.pin_offset_z
        bottom_fab_plastic = top_fab_plastic + height_fab_plastic

        height_fab_metal = pkg.metal_dimensions[2]
        bottom_fab_metal = top_fab_plastic + height_fab_metal

        bottom_silk_plastic = bottom_fab_plastic + c.silk_fab_offset
        x_mount_hole = left_fab_plastic + pkg.mounting_hole_position[0]

        # calculate y-translation of pin 1
        yshift = 0
        y1 = 0
        y2 = 0
        if staggered_type:
            if staggered_type == 1:
                y1 = pkg.staggered_pitch[0]
                yshift = -pkg.staggered_pitch[0]
            else:
                y2 = pkg.staggered_pitch[0]

        fpt = Translation(0, yshift)
        fp.append(fpt)

        ###  PADS  ############################################################

        pads = []
        y = y1
        x = 0
        for p in range(pkg.pins):
            y = y2 if p % 2 else y1
            pads.append((x, y))
            if pkg.pitch_list and p < len(pkg.pitch_list):
                x += pkg.pitch_list[p]
            else:
                x += pkg.pitch

        for p in range(len(pads)):
            if p == 0:
                pad_shape = Pad.SHAPE_RECT
            else:
                pad_shape = Pad.SHAPE_OVAL
            fpt.append(
                Pad(
                    number=p + 1,
                    type=Pad.TYPE_THT,
                    shape=pad_shape,
                    at=pads[p],
                    size=pkg.pad_dimensions,
                    drill=pkg.drill,
                    layers=Pad.LAYERS_THT,
                )
            )

        ###  FAB LAYER   ######################################################

        outline = GeomRectangle(
            start=[left_fab_plastic, top_fab_plastic],
            end=[right_fab_plastic, bottom_fab_plastic],
        )
        fab_outline = Rectangle(
            shape=outline,
            layer="F.Fab",
            width=c.fab_line_width,
        )
        fpt.append(fab_outline)

        for pad in pads:
            yl1 = bottom_fab_plastic
            yl2 = pad[1]
            if yl2 > yl1:
                fpt.append(
                    Rectangle(
                        start=[pad[0] - pkg.pin_width_height[0] / 2, yl1],
                        end=[pad[0] + pkg.pin_width_height[0] / 2, yl2],
                        layer="F.Fab",
                        width=c.fab_line_width,
                    )
                )

        if pkg.metal_dimensions[2] > 0:
            metal_h_line = Line(
                start=[left_fab_plastic, bottom_fab_metal],
                end=[right_fab_plastic, bottom_fab_metal],
                layer="F.Fab",
                width=c.fab_line_width,
            )
            fpt.append(metal_h_line)
            y_hole_bottom = bottom_fab_metal
            y_hole_bottom_slk = bottom_fab_metal
        else:
            y_hole_bottom = bottom_fab_plastic
            y_hole_bottom_slk = bottom_fab_metal + c.silk_fab_offset
        if pkg.mounting_hole_diameter > 0:
            x_hole_left = x_mount_hole - pkg.mounting_hole_diameter / 2
            x_hole_right = x_mount_hole + pkg.mounting_hole_diameter / 2
            hole_v_line_left = Line(
                start=[x_hole_left, top_fab_plastic],
                end=[x_hole_left, y_hole_bottom],
                layer="F.Fab",
                width=c.fab_line_width,
            )
            hole_v_line_right = Line(
                start=[x_hole_right, top_fab_plastic],
                end=[x_hole_right, y_hole_bottom],
                layer="F.Fab",
                width=c.fab_line_width,
            )
            fpt.append(hole_v_line_left)
            fpt.append(hole_v_line_right)

        ###  COURTYYRD  #######################################################

        cb = CourtyardBuilder.from_node(
            node=fpt, global_config=self.global_config, offset_fab=courtyard_offset
        )
        fpt += cb.node

        ###  SILKSCREEN LAYER  ################################################

        keepouts = []
        for p in range(len(pads)):
            if p == 0:
                addKeepout = addKeepoutRect
            else:
                addKeepout = addKeepoutRound
            keepouts += addKeepout(
                pads[p][0],
                pads[p][1],
                pkg.pad_dimensions[0] + 2 * c.silk_pad_clearance + c.silk_line_width,
                pkg.pad_dimensions[1] + 2 * c.silk_pad_clearance + c.silk_line_width,
            )

        silk_rect = outline.inflated(self.global_config.silk_fab_offset)
        silk_nodes = makeRectWithKeepout(
            rect=silk_rect,
            layer="F.SilkS",
            keepouts=keepouts,
            width=self.global_config.silk_line_width,
        )
        fpt += silk_nodes

        if pkg.metal_dimensions[2] > 0:
            addHLineWithKeepout(
                fpt,
                x0=left_fab_plastic - c.silk_fab_offset,
                x1=right_fab_plastic + c.silk_fab_offset,
                y=bottom_fab_metal,
                layer="F.SilkS",
                width=c.silk_line_width,
                keepouts=keepouts
            )

        if pkg.mounting_hole_diameter > 0:
            addVLineWithKeepout(
                fpt,
                x=x_hole_left,
                y0=top_fab_plastic - c.silk_fab_offset,
                y1=y_hole_bottom_slk,
                layer="F.SilkS",
                width=c.silk_line_width,
                keepouts=keepouts
            )
            addVLineWithKeepout(
                fpt,
                x=x_hole_right,
                y0=top_fab_plastic - c.silk_fab_offset,
                y1=y_hole_bottom_slk,
                layer="F.SilkS",
                width=c.silk_line_width,
                keepouts=keepouts
            )

        for p in range(len(pads)):
            yl1 = bottom_silk_plastic
            yl2 = pads[p][1]
            if yl2 > yl1:
                addVLineWithKeepout(
                    fpt,
                    pads[p][0] - pkg.pin_width_height[0] / 2 - c.silk_fab_offset,
                    yl1,
                    yl2,
                    "F.SilkS",
                    c.silk_line_width,
                    keepouts,
                )
                addVLineWithKeepout(
                    fpt,
                    pads[p][0] + pkg.pin_width_height[0] / 2 + c.silk_fab_offset,
                    yl1,
                    yl2,
                    "F.SilkS",
                    c.silk_line_width,
                    keepouts,
                )

        ### TEXT FIELDS  ######################################################

        addTextFields(
            fpt,
            configuration=self.global_config,
            body_edges=outline,
            courtyard=cb.bbox,
            fp_name=fp.name,
            text_y_inside_position="center",
            allow_rotation=True,
        )

        self.save_footprint(fp)

    def generate_rect_to_fp_horizontal_tab_down(
        self, pkg: RectangularToPackage, pkg_id: str, staggered_type: int = 0
    ):
        fp = pkg.init_footprint(
            "Horizontal", "TabDown", staggered_type, self.configuration
        )
        c = self.global_config
        courtyard_offset = self.global_config.get_courtyard_offset(
            global_config.GlobalConfig.CourtyardType.DEFAULT
        )

        width_fab_plastic = pkg.plastic_dimensions[0]
        height_fab_plastic = pkg.plastic_dimensions[1]
        bottom_fab_plastic = -pkg.pin_min_length_before_90deg_bend
        top_fab_plastic = bottom_fab_plastic - height_fab_plastic
        left_fab_plastic = -pkg.pin_offset_x
        right_fab_plastic = left_fab_plastic + width_fab_plastic

        width_fab_metal = pkg.metal_dimensions[0]
        height_fab_metal = pkg.metal_dimensions[1]
        top_fab_metal = bottom_fab_plastic - height_fab_metal
        left_fab_metal = left_fab_plastic + pkg.metal_offset_x
        right_fab_metal = left_fab_metal + width_fab_metal

        width_silk_plastic = width_fab_plastic + 2 * c.silk_fab_offset
        height_silk_plastic = height_fab_plastic + 2 * c.silk_fab_offset
        left_silk_plastic = left_fab_plastic - c.silk_fab_offset
        right_silk_plastic = left_silk_plastic + width_silk_plastic
        bottom_silk_plastic = bottom_fab_plastic + c.silk_fab_offset
        top_silk_plastic = bottom_silk_plastic - height_silk_plastic

        height_silk_metal = height_fab_metal + 2 * c.silk_fab_offset
        top_silk_metal = bottom_silk_plastic - height_silk_metal
        x_mount_hole = left_fab_plastic + pkg.mounting_hole_position[0]
        y_mount_hole = bottom_fab_plastic - pkg.mounting_hole_position[1]

        # calculate y-translation of pin 1
        yshift = 0
        y1 = 0
        y2 = 0
        if staggered_type == 1:
            y1 = pkg.staggered_pitch[1]
            yshift = -pkg.staggered_pitch[1]
            y2 = 0
        elif staggered_type == 2:
            y1 = 0
            yshift = 0
            y2 = pkg.staggered_pitch[1]

        fpt = Translation(0, yshift)
        fp.append(fpt)

        ###  PADS  ############################################################

        pads = []
        y = y1
        x = 0
        for p in range(1, pkg.pins + 1):
            if (p % 2) == 1:
                y = y1
            else:
                y = y2
            pads.append([x, y])
            if len(pkg.pitch_list) > 0 and p <= len(pkg.pitch_list):
                x += pkg.pitch_list[p - 1]
            else:
                x += pkg.pitch

        # create additional pad
        if len(pkg.additional_pin_pad_size) > 0:
            additional_pin_pad_position_x = round(pkg.plastic_dimensions[0] / 2, 3)
            additional_pin_pad_position_y = round(
                pkg.metal_dimensions[1] - pkg.additional_pin_pad_size[1] / 3, 3
            )
            additional_pad_x = left_fab_plastic + additional_pin_pad_position_x
            additional_pad_y = bottom_fab_plastic - additional_pin_pad_position_y
            fpt.append(
                Pad(
                    number=pkg.pins + 1,
                    type=Pad.TYPE_SMT,
                    shape=Pad.SHAPE_RECT,
                    at=[additional_pad_x, additional_pad_y],
                    size=pkg.additional_pin_pad_size,
                    drill=0,
                    layers=Pad.LAYERS_SMT,
                )
            )

        # create mounting hole
        if pkg.mounting_hole_drill > 0:
            fpt.append(
                Pad(
                    type=Pad.TYPE_NPTH,
                    shape=Pad.SHAPE_OVAL,
                    at=[x_mount_hole, y_mount_hole],
                    size=[pkg.mounting_hole_drill, pkg.mounting_hole_drill],
                    drill=pkg.mounting_hole_drill,
                    layers=Pad.LAYERS_THT,
                )
            )

        # create THT pads
        for p in range(len(pads)):
            if p == 0:
                pad_shape = Pad.SHAPE_RECT
            else:
                pad_shape = Pad.SHAPE_OVAL
            fpt.append(
                Pad(
                    number=p + 1,
                    type=Pad.TYPE_THT,
                    shape=pad_shape,
                    at=pads[p],
                    size=pkg.pad_dimensions,
                    drill=pkg.drill,
                    layers=Pad.LAYERS_THT,
                )
            )

        ###  FAB LAYER   ######################################################

        # Metal outline
        if height_fab_metal > 0:
            if len(pkg.plastic_angled) > 0:
                if len(pkg.metal_angled) > 0:
                    addRectAngledTopNoBottom(
                        fpt,
                        [
                            left_fab_metal,
                            top_fab_plastic + pkg.plastic_angled[1],
                        ],
                        [
                            right_fab_metal,
                            top_fab_metal,
                        ],
                        pkg.metal_angled,
                        "F.Fab",
                        c.fab_line_width,
                    )
                else:
                    fpt.append(
                        Rectangle(
                            start=[
                                left_fab_metal,
                                top_fab_metal,
                            ],
                            end=[
                                right_fab_metal,
                                top_fab_plastic - pkg.plastic_angled[1],
                            ],
                            layer="F.Fab",
                            width=c.fab_line_width,
                        )
                    )
            else:
                if len(pkg.metal_angled) > 0:
                    addRectAngledTop(
                        fpt,
                        [
                            left_fab_metal,
                            top_fab_plastic,
                        ],
                        [
                            right_fab_metal,
                            top_fab_metal,
                        ],
                        pkg.metal_angled,
                        "F.Fab",
                        c.fab_line_width,
                    )
                else:
                    fpt.append(
                        Rectangle(
                            start=[
                                left_fab_metal,
                                top_fab_metal,
                            ],
                            end=[
                                right_fab_metal,
                                top_fab_plastic,
                            ],
                            layer="F.Fab",
                            width=c.fab_line_width,
                        )
                    )

        # Plastic outline
        if len(pkg.plastic_angled) > 0:
            addRectAngledTop(
                fpt,
                [left_fab_plastic, bottom_fab_plastic],
                [
                    right_fab_plastic,
                    top_fab_plastic,
                ],
                pkg.plastic_angled,
                "F.Fab",
                c.fab_line_width,
            )
        else:
            fpt.append(
                Rectangle(
                    start=[left_fab_plastic, bottom_fab_plastic],
                    end=[
                        right_fab_plastic,
                        top_fab_plastic,
                    ],
                    layer="F.Fab",
                    width=c.fab_line_width,
                )
            )

        # Mounting hole
        if pkg.mounting_hole_diameter > 0:
            fpt.append(
                Circle(
                    center=[x_mount_hole, y_mount_hole],
                    radius=pkg.mounting_hole_diameter / 2,
                    layer="F.Fab",
                    width=c.fab_line_width,
                )
            )

        # Pins
        for p in range(len(pads)):
            fpt.append(
                Rectangle(
                    start=[
                        pads[p][0] - pkg.pin_width_height[0] / 2,
                        bottom_fab_plastic,
                    ],
                    end=[pads[p][0] + pkg.pin_width_height[0] / 2, pads[p][1]],
                    layer="F.Fab",
                    width=c.fab_line_width,
                )
            )

        ###  COURTYYRD  #######################################################

        cb = CourtyardBuilder.from_node(
            node=fpt, global_config=self.global_config, offset_fab=courtyard_offset
        )
        fpt += cb.node

        ###  SILKSCREEN LAYER   ###############################################

        keepouts = []
        for p in range(len(pads)):
            if p == 0:
                addKeepout = addKeepoutRect
            else:
                addKeepout = addKeepoutRound
            keepouts += addKeepout(
                pads[p][0],
                pads[p][1],
                pkg.pad_dimensions[0] + 2 * c.silk_pad_clearance + c.silk_line_width,
                pkg.pad_dimensions[1] + 2 * c.silk_pad_clearance + c.silk_line_width,
            )
        if len(pkg.additional_pin_pad_size) > 0:
            clearance = c.silk_pad_clearance + c.silk_line_width / 2
            keepouts += addKeepoutRect(
                additional_pad_x,
                additional_pad_y,
                pkg.additional_pin_pad_size[0] + 2 * clearance,
                pkg.additional_pin_pad_size[1] + 2 * clearance,
            )

        addHLineWithKeepout(
            fpt,
            left_silk_plastic,
            right_silk_plastic,
            bottom_silk_plastic,
            "F.SilkS",
            c.silk_line_width,
            keepouts,
        )
        if height_fab_metal:
            addHLineWithKeepout(
                fpt,
                left_silk_plastic,
                right_silk_plastic,
                top_silk_metal,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
            addVLineWithKeepout(
                fpt,
                left_silk_plastic,
                bottom_silk_plastic,
                top_silk_metal,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
            addVLineWithKeepout(
                fpt,
                right_silk_plastic,
                bottom_silk_plastic,
                top_silk_metal,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
        else:
            addHLineWithKeepout(
                fpt,
                left_silk_plastic,
                right_silk_plastic,
                top_silk_plastic,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
            addVLineWithKeepout(
                fpt,
                left_silk_plastic,
                bottom_silk_plastic,
                top_silk_plastic,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
            addVLineWithKeepout(
                fpt,
                right_silk_plastic,
                bottom_silk_plastic,
                top_silk_plastic,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )

        for p in range(len(pads)):
            addVLineWithKeepout(
                fpt,
                pads[p][0] - c.silk_fab_offset - pkg.pin_width_height[0] / 2,
                bottom_silk_plastic,
                pads[p][1],
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
            addVLineWithKeepout(
                fpt,
                pads[p][0] + c.silk_fab_offset + pkg.pin_width_height[0] / 2,
                bottom_silk_plastic,
                pads[p][1],
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )

        ### TEXT FIELDS  ######################################################

        addTextFields(
            fpt,
            configuration=self.global_config,
            body_edges=cb.bbox,
            courtyard=cb.bbox,
            fp_name=fp.name,
            text_y_inside_position="center",
            allow_rotation=True,
        )

        self.save_footprint(fp)

    def generate_rect_to_fp_horizontal_tab_up(
        self, pkg: RectangularToPackage, pkg_id: str
    ):
        if pkg.additional_pin_pad_size:
            logging.info(
                f"{pkg_id}: Cannot create 'horizontal tab up' version of a package with additional pin pad."
            )
            return

        fp = pkg.init_footprint("Horizontal", "TabUp", 0, self.configuration)
        c = self.global_config
        courtyard_offset = self.global_config.get_courtyard_offset(
            global_config.GlobalConfig.CourtyardType.DEFAULT
        )

        width_fab_plastic = pkg.plastic_dimensions[0]
        height_fab_plastic = pkg.plastic_dimensions[1]
        left_fab_plastic = -pkg.pin_offset_x
        right_fab_plastic = left_fab_plastic + width_fab_plastic
        top_fab_plastic = pkg.pin_min_length_before_90deg_bend
        bottom_fab_plastic = top_fab_plastic + height_fab_plastic

        width_fab_metal = pkg.metal_dimensions[0]
        height_fab_metal = pkg.metal_dimensions[1]
        bottom_fab_metal = top_fab_plastic + height_fab_metal
        left_fab_metal = left_fab_plastic + pkg.metal_offset_x
        right_fab_metal = left_fab_metal + width_fab_metal

        width_silk_plastic = width_fab_plastic + 2 * c.silk_fab_offset
        height_silk_plastic = height_fab_plastic + 2 * c.silk_fab_offset
        left_silk_plastic = left_fab_plastic - c.silk_fab_offset
        right_silk_plastic = left_silk_plastic + width_silk_plastic
        top_silk_plastic = top_fab_plastic - c.silk_fab_offset
        bottom_silk_plastic = top_silk_plastic + height_silk_plastic

        width_silk_metal = width_fab_metal + 2 * c.silk_fab_offset
        height_silk_metal = height_fab_metal + 2 * c.silk_fab_offset

        x_mount_hole = left_fab_plastic + pkg.mounting_hole_position[0]
        y_mount_hole = top_fab_plastic + pkg.mounting_hole_position[1]

        ###  PADS  ############################################################

        # create mounting hole
        if pkg.mounting_hole_drill > 0:
            fp.append(
                Pad(
                    type=Pad.TYPE_NPTH,
                    shape=Pad.SHAPE_OVAL,
                    at=[x_mount_hole, y_mount_hole],
                    size=[pkg.mounting_hole_drill, pkg.mounting_hole_drill],
                    drill=pkg.mounting_hole_drill,
                    layers=Pad.LAYERS_THT,
                )
            )

        # create pads
        x = 0
        for p in range(1, pkg.pins + 1):
            if p == 1:
                pad_shape = Pad.SHAPE_RECT
            else:
                pad_shape = Pad.SHAPE_OVAL
            fp.append(
                Pad(
                    number=p,
                    type=Pad.TYPE_THT,
                    shape=pad_shape,
                    at=[x, 0],
                    size=pkg.pad_dimensions,
                    drill=pkg.drill,
                    layers=Pad.LAYERS_THT,
                )
            )

            if len(pkg.pitch_list) > 0 and p <= len(pkg.pitch_list):
                x += pkg.pitch_list[p - 1]
            else:
                x += pkg.pitch

        ###  FAB LAYER   ######################################################

        # Metal outline
        if height_fab_metal > 0:
            if len(pkg.metal_angled) > 0:
                addRectAngledBottomNoTop(
                    fp,
                    [
                        left_fab_metal,
                        bottom_fab_plastic - pkg.plastic_angled[1],
                    ],
                    [
                        right_fab_metal,
                        bottom_fab_metal,
                    ],
                    pkg.metal_angled,
                    "F.Fab",
                    c.fab_line_width,
                )
            else:
                fp.append(
                    Rectangle(
                        start=[
                            left_fab_metal,
                            bottom_fab_plastic,
                        ],
                        end=[
                            right_fab_metal,
                            bottom_fab_metal,
                        ],
                        layer="F.Fab",
                        width=c.fab_line_width,
                    )
                )

        # Plastic outline
        if len(pkg.plastic_angled) > 0:
            addRectAngledBottom(
                fp,
                [left_fab_plastic, top_fab_plastic],
                [
                    right_fab_plastic,
                    bottom_fab_plastic,
                ],
                pkg.plastic_angled,
                "F.Fab",
                c.fab_line_width,
            )
        else:
            fp.append(
                Rectangle(
                    start=[left_fab_plastic, top_fab_plastic],
                    end=[
                        right_fab_plastic,
                        bottom_fab_plastic,
                    ],
                    layer="F.Fab",
                    width=c.fab_line_width,
                )
            )

        # Mounting hole
        if pkg.mounting_hole_diameter > 0:
            fp.append(
                Circle(
                    center=[x_mount_hole, y_mount_hole],
                    radius=pkg.mounting_hole_diameter / 2,
                    layer="F.Fab",
                    width=c.fab_line_width,
                )
            )
        x = 0

        # Pads
        for p in range(1, pkg.pins + 1):
            fp.append(
                Rectangle(
                    start=[x - pkg.pin_width_height[0] / 2, top_fab_plastic],
                    end=[x + pkg.pin_width_height[0] / 2, 0],
                    layer="F.Fab",
                    width=c.fab_line_width,
                )
            )
            if len(pkg.pitch_list) > 0 and p <= len(pkg.pitch_list):
                x = x + pkg.pitch_list[p - 1]
            else:
                x = x + pkg.pitch

        ###  COURTYYRD  #######################################################

        cb = CourtyardBuilder.from_node(
            node=fp, global_config=self.global_config, offset_fab=courtyard_offset
        )
        fp += cb.node

        ###  SILKCSCREEN LAYER   ##############################################

        keepouts = []
        x = 0
        for p in range(1, pkg.pins + 1):
            if p == 1:
                keepouts = keepouts + addKeepoutRect(
                    x,
                    0,
                    pkg.pad_dimensions[0]
                    + 2 * c.silk_pad_clearance
                    + c.silk_line_width,
                    pkg.pad_dimensions[1]
                    + 2 * c.silk_pad_clearance
                    + c.silk_line_width,
                )
            else:
                keepouts = keepouts + addKeepoutRound(
                    x,
                    0,
                    pkg.pad_dimensions[0]
                    + 2 * c.silk_pad_clearance
                    + c.silk_line_width,
                    pkg.pad_dimensions[1]
                    + 2 * c.silk_pad_clearance
                    + c.silk_line_width,
                )
            x = x + pkg.pitch

        addHLineWithKeepout(
            fp,
            left_silk_plastic,
            right_silk_plastic,
            top_silk_plastic,
            "F.SilkS",
            c.silk_line_width,
            keepouts,
        )
        addHLineWithKeepout(
            fp,
            left_silk_plastic,
            right_silk_plastic,
            bottom_silk_plastic,
            "F.SilkS",
            c.silk_line_width,
            keepouts,
        )
        addVLineWithKeepout(
            fp,
            left_silk_plastic,
            top_silk_plastic,
            bottom_silk_plastic,
            "F.SilkS",
            c.silk_line_width,
            keepouts,
        )
        addVLineWithKeepout(
            fp,
            right_silk_plastic,
            top_silk_plastic,
            bottom_silk_plastic,
            "F.SilkS",
            c.silk_line_width,
            keepouts,
        )
        if height_fab_metal > 0:
            addHDLineWithKeepout(
                fp,
                left_silk_plastic + pkg.metal_offset_x,
                left_silk_plastic + pkg.metal_offset_x + width_silk_metal,
                top_silk_plastic + height_silk_metal,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
            addVDLineWithKeepout(
                fp,
                left_silk_plastic + pkg.metal_offset_x,
                bottom_silk_plastic + c.silk_line_width * 2,
                top_silk_plastic + height_silk_metal,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
            addVDLineWithKeepout(
                fp,
                left_silk_plastic + pkg.metal_offset_x + width_silk_metal,
                bottom_silk_plastic + c.silk_line_width * 2,
                top_silk_plastic + height_silk_metal,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
        x = 0
        for p in range(1, pkg.pins + 1):
            addVLineWithKeepout(
                fp,
                x - c.silk_fab_offset - pkg.pin_width_height[0] / 2,
                top_silk_plastic,
                pkg.pad_dimensions[1] / 2
                + c.silk_pad_clearance
                + c.silk_line_width / 2,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
            addVLineWithKeepout(
                fp,
                x + c.silk_fab_offset + pkg.pin_width_height[0] / 2,
                top_silk_plastic,
                pkg.pad_dimensions[1] / 2
                + c.silk_pad_clearance
                + c.silk_line_width / 2,
                "F.SilkS",
                c.silk_line_width,
                keepouts,
            )
            if len(pkg.pitch_list) > 0 and p <= len(pkg.pitch_list):
                x += pkg.pitch_list[p - 1]
            else:
                x += pkg.pitch

        ### TEXT FIELDS  ######################################################

        addTextFields(
            fp,
            configuration=self.global_config,
            body_edges=cb.bbox,
            courtyard=cb.bbox,
            fp_name=fp.name,
            text_y_inside_position="center",
            allow_rotation=True,
        )

        self.save_footprint(fp)

    def add_outline(self, node: Node, pkg: RoundToPackage, layer: str):
        c = self.global_config
        match layer:
            case "F.Fab":
                mark_width = pkg.mark_width
                mark_length = pkg.mark_length
                diameter = pkg.diameter_outer
                line_width = c.fab_line_width
            case "F.SilkS":
                mark_width = pkg.mark_width + 2 * c.silk_fab_offset
                diameter = pkg.diameter_outer + 2 * c.silk_fab_offset
                line_width = c.silk_line_width
                u1 = math.cos(math.asin(pkg.mark_width / pkg.diameter_outer))
                u2 = math.cos(math.asin(mark_width / diameter))
                dr = pkg.diameter_outer * (u1 - u2) / 2
                mark_length = pkg.mark_length + dr
            case "F.CrtYd":
                courtyard_offset = c.get_courtyard_offset(
                    global_config.GlobalConfig.CourtyardType.DEFAULT
                )
                mark_width = pkg.mark_width + 2 * courtyard_offset
                diameter = pkg.diameter_outer + 2 * courtyard_offset
                line_width = c.courtyard_line_width
                u1 = math.cos(math.asin(pkg.mark_width / pkg.diameter_outer))
                u2 = math.cos(math.asin(mark_width / diameter))
                dr = pkg.diameter_outer * (u1 - u2) / 2
                mark_length = pkg.mark_length + dr

        if pkg.mark_width > 0 and pkg.mark_length > 0:
            a = math.radians(pkg.mark_angle)
            da = math.asin(mark_width / diameter)
            a1 = a + da
            a2 = a - da
            x1 = [
                (diameter / 2) * math.cos(a1),
                (diameter / 2) * math.sin(a1),
            ]
            x3 = [
                (diameter / 2) * math.cos(a2),
                (diameter / 2) * math.sin(a2),
            ]
            dx = mark_length * math.cos(a)
            dy = mark_length * math.sin(a)
            x2 = [x1[0] + dx, x1[1] + dy]
            x4 = [x3[0] + dx, x3[1] + dy]
            node.append(
                Arc(
                    center=[0, 0],
                    start=x1,
                    angle=(360 - 2 * math.degrees(da)),
                    layer=layer,
                    width=line_width,
                )
            )
            node.append(Line(start=x1, end=x2, layer=layer, width=line_width))
            node.append(Line(start=x2, end=x4, layer=layer, width=line_width))
            node.append(Line(start=x4, end=x3, layer=layer, width=line_width))
        else:
            node.append(
                Circle(
                    center=[0, 0],
                    radius=diameter / 2,
                    layer=layer,
                    width=line_width,
                )
            )

    def generate_round_to_fp(
        self, pkg: RoundToPackage, pkg_id: str, footprint_type: str
    ):
        fp = pkg.init_footprint(footprint_type)
        c = self.global_config
        text_offset = 1

        d_slk = pkg.diameter_outer + 2 * c.silk_fab_offset

        # calculate pad positions
        pads = []
        yshift = 0
        xshift = 0
        a = pkg.pin1_angle
        firstPin = True
        for p in range(1, pkg.pins + 1):
            x = pkg.pin_circle_diameter / 2 * math.cos(math.radians(a))
            y = pkg.pin_circle_diameter / 2 * math.sin(math.radians(a))
            a += pkg.angle_between_pins
            if p in pkg.deleted_pins:
                continue
            pads.append([x, y])
            if firstPin:
                xshift = -x
                yshift = -y
                firstPin = False

        txt_t = -d_slk / 2 - text_offset
        txt_b = d_slk / 2 + text_offset

        fpt = Translation(xshift, yshift)
        fp.append(fpt)

        # set general values
        fpt.append(
            Property(
                name=Property.REFERENCE, text="REF**", at=[0, txt_t], layer="F.SilkS"
            )
        )
        fpt.append(Text(text="${REFERENCE}", at=[0, txt_t], layer="F.Fab"))
        fpt.append(
            Property(name=Property.VALUE, text=fp.name, at=[0, txt_b], layer="F.Fab")
        )

        # create FAB layer
        self.add_outline(fpt, pkg, "F.Fab")

        fpt.append(
            Circle(
                center=[0, 0],
                radius=pkg.diameter_inner / 2,
                layer="F.Fab",
                width=c.fab_line_width,
            )
        )

        if footprint_type == "window" or footprint_type == "lens":
            addCircleLF(
                fpt,
                [0, 0],
                pkg.window_diameter / 2,
                "F.Fab",
                c.fab_line_width,
                4 * c.fab_line_width,
            )

        # create silkscreen layer
        self.add_outline(fpt, pkg, "F.SilkS")

        # Courtyard
        self.add_outline(fpt, pkg, "F.CrtYd")

        # create pads
        for p in range(len(pads)):
            if p == 0:
                fpt.append(
                    Pad(
                        number=p + 1,
                        type=Pad.TYPE_THT,
                        shape=Pad.SHAPE_OVAL,
                        at=pads[p],
                        size=[
                            round_to_grid_e(pkg.pad_dimensions[0] * 1.3, 0.1),
                            pkg.pad_dimensions[1],
                        ],
                        drill=pkg.drill,
                        layers=Pad.LAYERS_THT,
                    )
                )
            else:
                fpt.append(
                    Pad(
                        number=p + 1,
                        type=Pad.TYPE_THT,
                        shape=Pad.SHAPE_OVAL,
                        at=pads[p],
                        size=pkg.pad_dimensions,
                        drill=pkg.drill,
                        layers=Pad.LAYERS_THT,
                    )
                )

        self.save_footprint(fp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="use config .yaml files to create footprints."
    )

    parser.add_argument(
        "--naming_config",
        type=str,
        nargs="?",
        help="the config file defining footprint naming.",
        default="../package_config_KLCv3.yaml",
    )
    args = FootprintGenerator.add_standard_arguments(parser, file_autofind=True)

    with open(args.naming_config, "r") as config_stream:
        try:
            configuration = yaml.safe_load(config_stream)
        except yaml.YAMLError as exc:
            print(exc)

    FootprintGenerator.run_on_files(
        TOGenerator,
        args,
        file_autofind_dir="size_definitions",
        configuration=configuration,
    )
