import pytest

from KicadModTree import Line, RectLine
from KicadModTree.tests.test_utils import custom_assertions as CA
from kilibs.geom import GeomLine, Vector2D


@pytest.mark.parametrize(
    "start, end, layer, width",
    [
        ((0, 0), (1, 1), "F.SilkS", 0.1),
    ],
)
def test_Rect(start, end, layer, width):

    s = Vector2D(start)
    e = Vector2D(end)

    r = RectLine(start=s, end=e, layer=layer, width=width)

    # Check that the properties are set correctly
    assert r.start == s
    assert r.end == e
    assert r.layer == layer
    assert r.width == width

    # Flatten the object and check the output
    #
    # Rectangle is a base object, so it should flatten to itself
    nodes = r.leaves

    lines = CA.assert_contains_n_of_type(nodes, 4, Line)

    exp_line_pts = [
        ((s.x, s.y), (e.x, s.y)),
        ((e.x, s.y), (e.x, e.y)),
        ((e.x, e.y), (s.x, e.y)),
        ((s.x, e.y), (s.x, s.y)),
    ]
    exp_lines = [
        GeomLine(start=Vector2D(p1), end=Vector2D(p2)) for p1, p2 in exp_line_pts
    ]

    actual_line_pts = []
    for line in lines:
        actual_line_pts.append(GeomLine(start=line.start, end=line.end))

    CA.assert_contains_lines(actual_line_pts, exp_lines)
