# generators is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# generators is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# generators. If not, see < http://www.gnu.org/licenses/ >.
#
# (C) The KiCad Librarian Team

from KicadModTree import Footprint, FootprintType, Line
from kilibs.geom import Direction, Vector2D
from kilibs.config.global_config import GLOBAL_CONFIG
from generators.tools.footprint.drawing_tools_silk import SilkArrowSize
from generators.tools.footprint.nodes.layouts.n_pad_box_layout import (
    make_layout_for_smd_two_pad_dimensions,
)
from generators.tools.footprint.nodes.layouts.footprint_layout import SilkStyle
from generators.tools.footprint.save_footprint import write_footprint

from .smd_inductor_properties import (
    InductorSeriesProperties,
    SmdInductorProperties,
    TwoPadInductorParameters,
)


def create_footprints(spec: InductorSeriesProperties, generator_name: str) -> int:
    # For each series block in the yaml file, process it
    for part_data in spec.parts:
        generate_footprint(spec, part_data, generator_name)
    return len(spec.parts)


def generate_footprint(
    series_data: InductorSeriesProperties, part_data: SmdInductorProperties, generator_name: str
) -> None:

    part_dimension = part_data.body.get_body_size()

    if part_data.datasheet is None:
        # If datasheet was not defined in YAML nor CSV, terminate
        raise RuntimeError(
            f"No datasheet defined for {part_data.part_number} - terminating."
        )

    footprint_name = f"L_{series_data.manufacturer}_{part_data.part_number}"

    # init kicad footprint
    kicad_mod = Footprint(footprint_name, FootprintType.SMD)

    desc = [
        f"Inductor",
        series_data.manufacturer,
        part_data.part_number,
    ]

    if series_data.series_description:
        desc.append(f"{series_data.series_description} series")

    if series_data.additional_description:
        desc.append(series_data.additional_description)

    desc += [
        f"{part_dimension.x}x{part_dimension.y}x{part_dimension.z}mm",
        f"({part_data.datasheet})",
        GLOBAL_CONFIG.get_generated_by_description("gen_inductor.py"),  # For zero-diff. Replace with generator_name later.
    ]

    kicad_mod.description = ", ".join(desc)
    kicad_mod.tags = series_data.tags

    xy_body_size = Vector2D.from_floats(part_dimension.x, part_dimension.y)

    # For now, all supported inductors are two-pad SMD inductors,
    # but this is where we would dispatch to different layouts
    if isinstance(part_data.body, TwoPadInductorParameters):
        if xy_body_size.min_val < 2:
            silk_arrow_size = SilkArrowSize.SMALL
        else:
            silk_arrow_size = SilkArrowSize.MEDIUM

        layout = make_layout_for_smd_two_pad_dimensions(
            global_config=GLOBAL_CONFIG,
            pad_dims=part_data.body.landing_dims,
            body_size=xy_body_size,
            silk_style=SilkStyle.RECTANGLE_KEEP_TOP_BOTTOM,
            is_polarized=series_data.has_orientation,
            footprint_name=kicad_mod.name,
            silk_arrow_direction_if_inside=Direction.SOUTH,
            silk_arrow_size=silk_arrow_size,
        )

        # We never want the arrow to point in from the left even if the pad
        # is entirely inside the body.
        layout.silk_arrow_direction_if_inside = Direction.SOUTH

        kicad_mod += layout

        # And add an extra fab orientation line if the inductor is polarized
        if series_data.has_orientation:
            # This will always produce a gap between the line and the body chamfer
            line_y = part_dimension.y * GLOBAL_CONFIG.fab_bevel_size_relative

            # 10% of the way into the device, but don't let it get too close to the edge
            line_x = min(
                part_dimension.x * 0.4,
                part_dimension.x / 2 - GLOBAL_CONFIG.fab_line_width * 2,
            )

            kicad_mod += Line(
                start=Vector2D.from_floats(-line_x, line_y),
                end=Vector2D.from_floats(-line_x, -line_y),
                width=GLOBAL_CONFIG.fab_line_width,
                layer="F.Fab",
            )
    else:
        raise RuntimeError(
            f"Unsupported inductor body type {type(part_data.body)} for {footprint_name}."
        )

    # No variants, so we can just use the footprint name
    kicad_mod.add_standard_3d_model_to_footprint(
        series_data.library_name, kicad_mod.name
    )

    write_footprint(kicad_mod, series_data.library_name, generator_name)
