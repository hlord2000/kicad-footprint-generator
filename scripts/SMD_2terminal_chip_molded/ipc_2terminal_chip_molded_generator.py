#!/usr/bin/env python3

import argparse

import yaml

from kilibs.ipc_tools import ipc_rules
from kilibs.util.toleranced_size import TolerancedSize
from KicadModTree import *  # NOQA
from KicadModTree.nodes.base.Pad import Pad  # NOQA
from scripts.tools.drawing_tools import (
    nearestSilkPointOnOrthogonalLineSmallClerance,
    round_to_grid_up,
)
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files import global_config as GC
from scripts.tools.ipc_pad_size_calculators import ipc_body_edge_inside


size_definition_path = "size_definitions/"


def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


class TwoTerminalSMD:

    def __init__(
        self,
        global_config: GC.GlobalConfig,
        ipc_defs: ipc_rules.IpcRules,
        command_file,
        configuration,
    ):
        self.global_config = global_config
        self.configuration = configuration
        with open(command_file, "r") as command_stream:
            try:
                self.footprint_group_definitions = yaml.safe_load(command_stream)
            except yaml.YAMLError as exc:
                print(exc)

        self.ipc_definitions = ipc_defs

    def calcPadDetails(
        self,
        device_dimensions,
        ipc_offsets: ipc_rules.Offsets,
        ipc_round_base: ipc_rules.Offsets,
        footprint_group_data,
    ):
        # Zmax = Lmin + 2JT + √(CL^2 + F^2 + P^2)
        # Gmin = Smax − 2JH − √(CS^2 + F^2 + P^2)
        # Xmax = Wmin + 2JS + √(CW^2 + F^2 + P^2)

        # Some manufacturers do not list the terminal spacing (S) in their datasheet but list the terminal length (T)
        # Then one can calculate
        # Stol(RMS) = √(Ltol^2 + 2*^2)
        # Smin = Lmin - 2*Tmax
        # Smax(RMS) = Smin + Stol(RMS)

        manf_tol = ipc_rules.ManufacturingTolerance(
            manufacturing_tolerance=self.configuration.get(
                "manufacturing_tolerance", 0.1
            ),
            placement_tolerance=self.configuration.get("placement_tolerance", 0.05),
        )

        if "terminal_width" in device_dimensions:
            lead_width = device_dimensions["terminal_width"]
        else:
            lead_width = device_dimensions["body_width"]

        Gmin, Zmax, Xmax = ipc_body_edge_inside(
            ipc_offsets,
            ipc_round_base,
            manf_tol,
            device_dimensions["body_length"],
            lead_width,
            lead_len=device_dimensions.get("terminal_length"),
            lead_inside=device_dimensions.get("terminator_spacing"),
        )

        Zmax += footprint_group_data.get("pad_length_addition", 0)
        Pad = {"at": [-(Zmax + Gmin) / 4, 0], "size": [(Zmax - Gmin) / 2, Xmax]}
        Paste = None

        if "paste_pad" in footprint_group_data:
            rel_reduction_factor = footprint_group_data["paste_pad"].get(
                "all_sides_rel", 0.9
            )
            x_abs_reduction = (1 - rel_reduction_factor) * Pad["size"][0]
            Zmax -= 2 * x_abs_reduction
            Gmin += 2 * x_abs_reduction - 2 * footprint_group_data["paste_pad"].get(
                "heel_abs", 0
            )
            Xmax *= rel_reduction_factor
            Paste = {"at": [-(Zmax + Gmin) / 4, 0], "size": [(Zmax - Gmin) / 2, Xmax]}

        return Pad, Paste

    @staticmethod
    def deviceDimensions(device_size_data):
        dimensions = {
            "body_length": TolerancedSize.fromYaml(
                device_size_data, base_name="body_length"
            ),
            "body_width": TolerancedSize.fromYaml(
                device_size_data, base_name="body_width"
            ),
        }
        if (
            "terminator_spacing_max" in device_size_data
            and "terminator_spacing_min" in device_size_data
            or "terminator_spacing" in device_size_data
        ):
            dimensions["terminator_spacing"] = TolerancedSize.fromYaml(
                device_size_data, base_name="terminator_spacing"
            )
        elif (
            "terminal_length_max" in device_size_data
            and "terminal_length_min" in device_size_data
            or "terminal_length" in device_size_data
        ):
            dimensions["terminal_length"] = TolerancedSize.fromYaml(
                device_size_data, base_name="terminal_length"
            )
        else:
            raise KeyError(
                "Either terminator spacing or terminal length must be included in the size definition."
            )

        if (
            "terminal_width_min" in device_size_data
            and "terminal_width_max" in device_size_data
            or "terminal_width" in device_size_data
        ):
            dimensions["terminal_width"] = TolerancedSize.fromYaml(
                device_size_data, base_name="terminal_width"
            )

        return dimensions

    def generateFootprints(self):
        for group_name in self.footprint_group_definitions:
            # print(device_group)
            footprint_group_data = self.footprint_group_definitions[group_name]

            device_size_docs = footprint_group_data["size_definitions"]
            package_size_defintions = {}
            for device_size_doc in device_size_docs:
                with open(size_definition_path + device_size_doc, "r") as size_stream:
                    try:
                        package_size_defintions.update(yaml.safe_load(size_stream))
                    except yaml.YAMLError as exc:
                        print(exc)

            for size_name in package_size_defintions:
                print(group_name + ": " + size_name)
                device_size_data = package_size_defintions[size_name]
                try:
                    self.generateFootprint(device_size_data, footprint_group_data)
                except Exception as exc:
                    print(
                        "Failed to generate {size_name} (group: {group_name}):".format(
                            size_name=size_name, group_name=group_name
                        )
                    )
                    raise (exc)

    def generateFootprint(self, device_size_data, footprint_group_data):
        device_dimensions = TwoTerminalSMD.deviceDimensions(device_size_data)

        if "ipc_reference" in device_size_data:
            ipc_reference = device_size_data["ipc_reference"]
        else:
            ipc_reference = footprint_group_data["ipc_reference"]
        ipc_density = self.configuration.get("ipc_density")[0]
        density_suffix = self.configuration.get("ipc_density")[1]

        used_density = ipc_rules.IpcDensity(self.configuration.get('ipc_density', ipc_density)[0])
        ipc_offsets = self.ipc_definitions.get_class(ipc_reference).get_offsets(used_density)
        ipc_round_base = self.ipc_definitions.get_class(ipc_reference).roundoff

        if "ipc_string" in device_size_data:
            ipc_string = device_size_data["ipc_string"]
        elif "ipc_string" in footprint_group_data:
            ipc_string = footprint_group_data["ipc_string"]
        else:
            ipc_string = "IPC-7351"

        pad_details, paste_details = self.calcPadDetails(
            device_dimensions, ipc_offsets, ipc_round_base, footprint_group_data
        )
        # print(calc_pad_details())
        # print("generate {name}.kicad_mod".format(name=footprint))

        suffix = footprint_group_data.get("suffix", "").format(
            pad_x=pad_details["size"][0], pad_y=pad_details["size"][1]
        )
        prefix = footprint_group_data["prefix"]

        model3d_path_prefix = self.configuration.get(
            "3d_model_prefix", global_config.model_3d_prefix
        )
        model3d_path_suffix = self.configuration.get(
            "3d_model_suffix", global_config.model_3d_suffix
        )
        suffix_3d = (
            suffix
            if footprint_group_data.get("include_suffix_in_3dpath", "True") == "True"
            else ""
        )

        if (
            density_suffix != ""
            and "handsolder" not in footprint_group_data["keywords"]
        ):
            density_description = f", {ipc_string} {ipc_density}"
            suffix = suffix + density_suffix
            suffix_3d = suffix_3d + density_suffix
        else:
            density_description = f", {ipc_string} nominal"

        code_metric = device_size_data.get("code_metric")
        code_letter = device_size_data.get("code_letter")
        code_imperial = device_size_data.get("code_imperial")

        if "code_letter" in device_size_data:
            name_format = self.configuration["fp_name_tantal_format_string"]
        else:
            if "code_metric" in device_size_data:
                name_format = self.configuration["fp_name_format_string"]
            else:
                name_format = self.configuration["fp_name_non_metric_format_string"]

        if "custom_name" in device_size_data:
            fp_name = device_size_data["custom_name"]
            fp_name_2 = device_size_data["custom_name"]
        else:
            fp_name = name_format.format(
                prefix=prefix,
                code_imperial=code_imperial,
                code_metric=code_metric,
                code_letter=code_letter,
                suffix=suffix,
            )
            fp_name_2 = name_format.format(
                prefix=prefix,
                code_imperial=code_imperial,
                code_letter=code_letter,
                code_metric=code_metric,
                suffix=suffix_3d,
            )

        model_name = f"{model3d_path_prefix}{footprint_group_data['fp_lib_name']}.3dshapes/{fp_name_2}{model3d_path_suffix}"

        kicad_mod = Footprint(fp_name, FootprintType.SMD)

        # init kicad footprint
        if "custom_name" in device_size_data:
            kicad_mod.setDescription(device_size_data["description"])
        else:
            kicad_mod.setDescription(
                footprint_group_data["description"].format(
                    code_imperial=code_imperial,
                    code_metric=code_metric,
                    code_letter=code_letter,
                    density=density_description,
                    size_info=device_size_data.get("size_info"),
                )
            )
        kicad_mod.setTags(footprint_group_data["keywords"])

        pad_shape_details = {}
        pad_shape_details["shape"] = Pad.SHAPE_ROUNDRECT
        pad_shape_details["round_radius_handler"] = (
            self.global_config.roundrect_radius_handler
        )

        if paste_details is not None:
            layers_main = ["F.Cu", "F.Mask"]

            kicad_mod.append(
                Pad(
                    number="",
                    type=Pad.TYPE_SMT,
                    layers=["F.Paste"],
                    **merge_dicts(paste_details, pad_shape_details),
                )
            )
            paste_details["at"][0] *= -1
            kicad_mod.append(
                Pad(
                    number="",
                    type=Pad.TYPE_SMT,
                    layers=["F.Paste"],
                    **merge_dicts(paste_details, pad_shape_details),
                )
            )
        else:
            layers_main = Pad.LAYERS_SMT

        P1 = Pad(
            number=1,
            type=Pad.TYPE_SMT,
            layers=layers_main,
            **merge_dicts(pad_details, pad_shape_details),
        )
        pad_radius = P1.get_round_radius()

        kicad_mod.append(P1)
        pad_details["at"][0] *= -1
        kicad_mod.append(
            Pad(
                number=2,
                type=Pad.TYPE_SMT,
                layers=layers_main,
                **merge_dicts(pad_details, pad_shape_details),
            )
        )

        fab_outline = self.configuration.get("fab_outline", "typical")
        if fab_outline == "max":
            outline_size = [
                device_dimensions["body_length"].maximum,
                device_dimensions["body_width"].maximum,
            ]
        elif fab_outline == "min":
            outline_size = [
                device_dimensions["body_length"].minimum,
                device_dimensions["body_width"].minimum,
            ]
        else:
            outline_size = [
                device_dimensions["body_length"].nominal,
                device_dimensions["body_width"].nominal,
            ]

        if footprint_group_data.get("polarization_mark", "False") == "True":
            polararity_marker_size = self.configuration.get("fab_polarity_factor", 0.25)
            polararity_marker_size *= (
                outline_size[1]
                if outline_size[1] < outline_size[0]
                else outline_size[0]
            )

            polarity_marker_thick_line = False

            polarity_max_size = self.configuration.get("fab_polarity_max_size", 1)
            if polararity_marker_size > polarity_max_size:
                polararity_marker_size = polarity_max_size
            polarity_min_size = self.configuration.get("fab_polarity_min_size", 0.25)
            if polararity_marker_size < polarity_min_size:
                if polararity_marker_size < polarity_min_size * 0.6:
                    polarity_marker_thick_line = True
                polararity_marker_size = polarity_min_size

            silk_x_left = (
                -abs(pad_details["at"][0])
                - pad_details["size"][0] / 2
                - global_config.silk_pad_offset
            )

            silk_y_bottom = max(
                global_config.silk_pad_offset + pad_details["size"][1] / 2,
                outline_size[1] / 2 + global_config.silk_fab_offset,
            )

            if polarity_marker_thick_line:
                kicad_mod.append(
                    RectLine(
                        start=[-outline_size[0] / 2, outline_size[1] / 2],
                        end=[outline_size[0] / 2, -outline_size[1] / 2],
                        layer="F.Fab",
                        width=global_config.fab_line_width,
                    )
                )
                x = -outline_size[0] / 2 + global_config.fab_line_width
                kicad_mod.append(
                    Line(
                        start=[x, outline_size[1] / 2],
                        end=[x, -outline_size[1] / 2],
                        layer="F.Fab",
                        width=global_config.fab_line_width,
                    )
                )
                x += global_config.fab_line_width
                if x < -global_config.fab_line_width / 2:
                    kicad_mod.append(
                        Line(
                            start=[x, outline_size[1] / 2],
                            end=[x, -outline_size[1] / 2],
                            layer="F.Fab",
                            width=global_config.fab_line_width,
                        )
                    )

                kicad_mod.append(
                    Circle(
                        center=[silk_x_left - 0.05, 0],
                        radius=0.05,
                        layer="F.SilkS",
                        width=0.1,
                    )
                )
            else:
                poly_fab = [
                    {"x": outline_size[0] / 2, "y": -outline_size[1] / 2},
                    {
                        "x": polararity_marker_size - outline_size[0] / 2,
                        "y": -outline_size[1] / 2,
                    },
                    {
                        "x": -outline_size[0] / 2,
                        "y": polararity_marker_size - outline_size[1] / 2,
                    },
                    {"x": -outline_size[0] / 2, "y": outline_size[1] / 2},
                    {"x": outline_size[0] / 2, "y": outline_size[1] / 2},
                    {"x": outline_size[0] / 2, "y": -outline_size[1] / 2},
                ]
                kicad_mod.append(
                    PolygonLine(
                        shape=poly_fab,
                        layer="F.Fab",
                        width=global_config.fab_line_width,
                    )
                )

                poly_silk = [
                    {"x": outline_size[0] / 2, "y": -silk_y_bottom},
                    {"x": silk_x_left, "y": -silk_y_bottom},
                    {"x": silk_x_left, "y": silk_y_bottom},
                    {"x": outline_size[0] / 2, "y": silk_y_bottom},
                ]
                kicad_mod.append(
                    PolygonLine(
                        shape=poly_silk,
                        layer="F.SilkS",
                        width=global_config.silk_line_width,
                    )
                )
        else:
            kicad_mod.append(
                RectLine(
                    start=[-outline_size[0] / 2, outline_size[1] / 2],
                    end=[outline_size[0] / 2, -outline_size[1] / 2],
                    layer="F.Fab",
                    width=global_config.fab_line_width,
                )
            )

            silk_outline_y = outline_size[1] / 2 + global_config.silk_fab_offset
            default_clearance = global_config.silk_pad_clearance
            silk_point_top_right = nearestSilkPointOnOrthogonalLineSmallClerance(
                pad_size=pad_details["size"],
                pad_position=pad_details["at"],
                pad_radius=pad_radius,
                fixed_point=Vector2D(0, silk_outline_y),
                moving_point=Vector2D(outline_size[0] / 2, silk_outline_y),
                silk_pad_offset_default=(
                    global_config.silk_line_width / 2 + default_clearance
                ),
                silk_pad_offset_reduced=(
                    global_config.silk_line_width / 2
                    + self.configuration.get(
                        "silk_clearance_small_parts", default_clearance
                    )
                ),
                min_length=configuration.get("silk_line_length_min", 0) / 2,
            )

            if silk_point_top_right:
                kicad_mod.append(
                    Line(
                        start=[-silk_point_top_right.x, -silk_point_top_right.y],
                        end=[silk_point_top_right.x, -silk_point_top_right.y],
                        layer="F.SilkS",
                        width=global_config.silk_line_width,
                    )
                )
                kicad_mod.append(
                    Line(
                        start=[-silk_point_top_right.x, silk_point_top_right.y],
                        end=silk_point_top_right,
                        layer="F.SilkS",
                        width=global_config.silk_line_width,
                    )
                )

        CrtYd_rect = [None, None]
        # Half width of the courtyard
        CrtYd_rect[0] = round_to_grid_up(
            abs(pad_details["at"][0])
            + pad_details["size"][0] / 2
            + ipc_offsets.courtyard,
            global_config.courtyard_grid,
            1e-7,
        )
        # Half height of the courtyard
        CrtYd_rect[1] = round_to_grid_up(
            max(pad_details["size"][1], outline_size[1]) / 2
            + ipc_offsets.courtyard,
            global_config.courtyard_grid,
            1e-7,
        )
        kicad_mod.append(
            RectLine(
                start=[-CrtYd_rect[0], CrtYd_rect[1]],
                end=[CrtYd_rect[0], -CrtYd_rect[1]],
                layer="F.CrtYd",
                width=global_config.courtyard_line_width,
            )
        )

        ######################### Text Fields ###############################

        addTextFields(
            kicad_mod=kicad_mod,
            configuration=configuration,
            body_edges={
                "left": -outline_size[0] / 2,
                "right": outline_size[0] / 2,
                "top": -outline_size[1] / 2,
                "bottom": outline_size[1] / 2,
            },
            courtyard={"top": -CrtYd_rect[1], "bottom": CrtYd_rect[1]},
            fp_name=fp_name,
            text_y_inside_position="center",
        )

        kicad_mod.append(Model(filename=model_name))

        lib = KicadPrettyLibrary(footprint_group_data["fp_lib_name"], None)
        lib.save(kicad_mod)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="use config .yaml files to create footprints."
    )
    parser.add_argument(
        "files",
        metavar="file",
        type=str,
        nargs="+",
        help="list of files holding information about what devices should be created.",
    )
    parser.add_argument(
        "--global_config",
        type=str,
        nargs="?",
        help="the config file defining how the footprint will look like. (KLC)",
        default="../tools/global_config_files/config_KLCv3.0.yaml",
    )
    parser.add_argument(
        "--series_config",
        type=str,
        nargs="?",
        help="the config file defining series parameters.",
        default="package_config_KLCv3.0.yaml",
    )
    parser.add_argument(
        "--ipc_definition",
        type=str,
        nargs="?",
        help="the ipc definition file",
        default="ipc7351B_2terminal",
    )
    parser.add_argument(
        "--ipc_density", type=str, nargs="?", help="IPC density level (L,N,M)"
    )
    args = parser.parse_args()

    # if the user requests an IPC density, put that and footprint suffix in a list
    # nominal density with no suffix if no argument is provided
    if args.ipc_density is None:
        ipc_density = ["nominal", ""]
    elif args.ipc_density.upper() == "L":
        ipc_density = ["least", "_L"]
    elif args.ipc_density.upper() == "N":
        ipc_density = ["nominal", "_N"]
    elif args.ipc_density.upper() == "M":
        ipc_density = ["most", "_M"]
    else:
        raise ValueError("If IPC density is specified, it must be 'L', 'N', or 'M.'")
        sys.exit()

    with open(args.global_config, "r") as config_stream:
        try:
            configuration = yaml.safe_load(config_stream)
            global_config = GC.GlobalConfig(configuration)
        except yaml.YAMLError as exc:
            print(exc)

    with open(args.series_config, "r") as config_stream:
        try:
            configuration.update(yaml.safe_load(config_stream))
        except yaml.YAMLError as exc:
            print(exc)
    args = parser.parse_args()

    ipc_defs = ipc_rules.IpcRules.from_file(args.ipc_definition)

    configuration["ipc_density"] = ipc_density

    for filepath in args.files:
        two_terminal_smd = TwoTerminalSMD(
            global_config, ipc_defs, filepath, configuration
        )
        two_terminal_smd.generateFootprints()
