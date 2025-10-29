#! /usr/bin/env python3

import argparse
import dataclasses
import enum
from typing import Any

import socket_strips

from scripts.tools.footprint_generator import FootprintGenerator


class Orientation(enum.Enum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


class MountType(enum.Enum):
    THT = "THT"
    SMD = "SMD"


@dataclasses.dataclass
class DParams:
    num_pins: int
    num_pin_rows: int
    pin_pitch: float
    pin_style: Orientation
    pin_length: float
    pin_width: float
    pin_thickness: float
    pin_drill: float
    pin1start_right: bool
    pad_width: float
    pad_length: float
    pads_lp_width: float
    pins_offset: float
    body_width: float
    body_height: float
    body_overlength: float
    body_offset: float
    datasheet: str


class PinSocketProperies:

    def __init__(self, spec: dict[str, Any]):
        match spec["orientation"]:
            case "vertical":
                self.orientation = Orientation.VERTICAL
            case "horizontal":
                self.orientation = Orientation.HORIZONTAL
            case _:
                raise ValueError(f"Invalid orientation: {spec['orientation']}")

        match spec["mount"]:
            case "THT":
                self.mount_type = MountType.THT
            case "SMD":
                self.mount_type = MountType.SMD
            case _:
                raise ValueError(f"Invalid mount type: {spec['mount']}")

        self.row_count = int(spec["row_count"])
        self.pin_pitch = float(spec["pin_pitch"])
        self.row_pitch = float(spec.get("row_pitch", self.pin_pitch))

        pos_range = spec["num_pos"]["range"]
        self.pin_counts = range(pos_range[0], pos_range[1] + 1)

        self.dparams = DParams(
            num_pins=0,  # will be filled in later
            num_pin_rows=self.row_count,
            pin_pitch=self.pin_pitch,
            pin_style=self.orientation,
            pin_length=spec["pins"]["length"],
            pin_width=spec["pins"]["width"],
            pin_thickness=spec["pins"]["thickness"],
            pin_drill=spec["pins"]["drill"],
            pin1start_right=spec.get("pin1start_right", False),
            pad_width=spec["pads"]["width"],
            pad_length=spec["pads"]["length"],
            pads_lp_width=spec["pads"].get("lp_width", spec["pads"]["width"]),
            pins_offset=spec["pins"].get("offset", 0.0),
            body_width=spec["body"]["width"],
            body_height=spec["body"]["height"],
            body_overlength=spec["body"].get("overlength", 0.0),
            body_offset=spec["body"].get("offset", 0.0),
            datasheet=spec.get("datasheet", ""),
        )


class PinSocketGenerator(FootprintGenerator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def generateFootprint(
        self, spec: dict[str, Any], pkg_id: str, header_info: dict[str, Any]
    ) -> None:
        fp_config = PinSocketProperies(spec)

        for pin_count in fp_config.pin_counts:
            fp_config.dparams.num_pins = pin_count

            if (
                fp_config.mount_type == MountType.THT
                and fp_config.orientation == Orientation.VERTICAL
            ):
                builder = socket_strips.pinSocketVerticalTHT(fp_config.dparams)
            elif (
                fp_config.mount_type == MountType.THT
                and fp_config.orientation == Orientation.HORIZONTAL
            ):
                builder = socket_strips.pinSocketHorizontalTHT(fp_config.dparams)
            elif (
                fp_config.mount_type == MountType.SMD
                and fp_config.orientation == Orientation.VERTICAL
            ):
                builder = socket_strips.pinSocketVerticalSMD(fp_config.dparams)
            # elif fp_config.mount == "SMD" and fp_config.orientation == Orientation.HORIZONTAL:
            #     builder = socket_strips.pinSocketHorizontalSMD(fp_config.dparams)
            else:
                raise ValueError(
                    f"Unsupported mount/orientation combination: {fp_config.mount_type}/{fp_config.orientation}"
                )

            builder.make()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="use config .yaml files to create socket strips."
    )
    parser.add_argument(
        "files",
        metavar="file",
        type=str,
        nargs="*",
        help="list of files holding information about what devices should be created.",
    )
    args = FootprintGenerator.add_standard_arguments(parser)

    FootprintGenerator.run_on_files(PinSocketGenerator, args)
