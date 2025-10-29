from kilibs.geom import GeomRectangle
from KicadModTree import Circle, Node, Stadium
from scripts.tools.global_config_files import global_config as GC


def make_round_or_stadium_courtyard(
    global_config: GC.GlobalConfig, bounding_rectangle: GeomRectangle
) -> list[Node]:
    """
    Create a courtyard that fits within the given rectangle, using a stadium
    if the rectangle isn't square, or a circle if it is.

    This will do the necessary grid rounding per GC settings.
    """

    courtyard_rect = bounding_rectangle.copy().round_to_grid(grid=global_config.courtyard_grid, outwards=True)

    layer = "F.CrtYd"
    width = global_config.courtyard_line_width

    # Could make this parameterised, but do we need that?
    tolerance = global_config.courtyard_grid

    # create courtyard
    if abs(courtyard_rect.size.x - courtyard_rect.size.y) > tolerance:
        courtyard = Stadium(
                shape=courtyard_rect,
                layer=layer,
                width=width,
            )
    else:
        courtyard = Circle(
            center=courtyard_rect.center,
            radius=courtyard_rect.max_dimension / 2,
            layer=layer,
            width=width,
        )
    return [courtyard]
