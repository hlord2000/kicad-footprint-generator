#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This is derived from a cadquery script for generating PDIP models in X3D format
#
# from https://bitbucket.org/hyOzd/freecad-macros
# author hyOzd
# This is a
# Dimensions are from Microchips Packaging Specification document:
# DS00000049BY. Body drawing is the same as QFP generator#
#
## Requirements
## CadQuery 2.1 commit e00ac83f98354b9d55e6c57b9bb471cdf73d0e96 or newer
## https://github.com/CadQuery/cadquery
#
## To run the script just do: ./generator.py --output_dir [output_directory]
## e.g. ./generator.py --output_dir /tmp
#
# * These are cadquery tools to export                                       *
# * generated models in STEP & VRML format.                                  *
# *                                                                          *
# * cadquery script for generating QFP/SOIC/SSOP/TSSOP models in STEP AP214  *
# * Copyright (c) 2015                                                       *
# *     Maurice https://launchpad.net/~easyw                                 *
# * Copyright (c) 2022                                                       *
# *     Update 2022                                                          *
# *     jmwright (https://github.com/jmwright)                               *
# *     Work sponsored by KiCAD Services Corporation                         *
# *          (https://www.kipro-pcb.com/)                                    *
# *                                                                          *
# * All trademarks within this guide belong to their legitimate owners.      *
# *                                                                          *
# *   This program is free software; you can redistribute it and/or modify   *
# *   it under the terms of the GNU General Public License (GPL)             *
# *   as published by the Free Software Foundation; either version 2 of      *
# *   the License, or (at your option) any later version.                    *
# *   for detail see the LICENCE text file.                                  *
# *                                                                          *
# *   This program is distributed in the hope that it will be useful,        *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of         *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          *
# *   GNU Library General Public License for more details.                   *
# *                                                                          *
# *   You should have received a copy of the GNU Library General Public      *
# *   License along with this program; if not, write to the Free Software    *
# *   Foundation, Inc.,                                                      *
# *   51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA           *
# *                                                                          *
# ****************************************************************************

from math import atan, cos, degrees, radians, sin, tan
from typing import Any, cast

import cadquery as cq

from _tools.cq_helpers import union_all  # pyright: ignore

max_cc1 = 1
default_pin_slope = 10


def make_gw(
    params: dict[str, Any],
) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane | None, cq.Workplane | None]:
    c = cast(float, params["c"])
    the = cast(float, params["the"])
    the_p = cast(float | None, params.get("the_p"))
    tb_s = cast(float, params["tb_s"])
    ef = cast(float, params.get("ef", 0.0))
    cc1 = cast(float, params["cc1"])
    marker = cast(str, params.get("marker", "circle"))
    r1 = cast(float | None, params.get("R1"))
    r2 = cast(float, params["R2"])
    s = cast(float | None, params.get("S"))
    l = cast(float | None, params.get("L"))
    d1 = cast(float, params["D1"])
    e1 = cast(float, params["E1"])
    e = cast(float, params["E"])
    a1 = cast(float, params["A1"])
    a2 = cast(float, params["A2"])
    b = cast(float, params["b"])
    pitch = cast(float, params["e"])
    npx = cast(int, params["npx"])
    npy = cast(int, params["npy"])
    excluded_pins = params.get("excluded_pins", ())

    missingparam = [s, l, r1, the_p].count(None)
    if missingparam == 0:
        print(
            "Warning: All of S, L, R1, and the_p are provided. The system is "
            "overconstrained. Ignoring the value of S."
        )
        s = None

    elif missingparam > 2:
        raise Exception("At least two of S, L, R1, and the_p must be provided.")

    if the_p is None:
        if s is not None and l is not None and r1 is not None:
            the_p = degrees(
                atan(
                    (((e - e1) / 2) - (s + l + r1))
                    / (a1 + ((a2 - c) / 2) - (r1 + r2 + c))
                )
            )
            if the_p < 0:
                print(
                    "The provided values of S, L, and R1 will result in inward-"
                    "sloping pins. If this is not what you intended, confirm those "
                    "values and reduce one or more of them."
                )
        # if more than one param is missing, we can't calculate a pin angle, so just
        # set it to the default
        else:
            the_p = default_pin_slope

    tan_p = tan(radians(the_p))
    if l is None and r1 is not None and s is not None:
        l = (e - e1) / 2 - (s + r1) - (a1 + ((a2 - c) / 2) - (r1 + r2 + c)) * tan_p
        if the_p > 0 and l < (c + r2):
            raise Exception("the_p is too large.")
    elif s is None and r1 is not None and l is not None:
        s = (e - e1) / 2 - (r1 + l) - (a1 + ((a2 - c) / 2) - (r1 + r2 + c)) * tan_p
        if the_p > 0 and s < 0:
            raise Exception("the_p is too large.")
    elif r1 is None and s is not None and l is not None:
        r1 = (s - (e - e1) / 2 + l + (a1 + (a2 - c) / 2 - r2 - c) * tan_p) / (tan_p - 1)
        if the_p > 0 and r1 < 0:
            raise Exception("the_p is too large.")
    elif r1 is not None and s is not None and l is not None:
        pass
    else:
        raise NotImplementedError("This should not happen.")
    # uncomment to constrain pin angles to positive or vertical, i.e. no "Z" shaped
    # pins:
    # the_p = max(the_p, 0)

    if abs(the_p) >= 90.0:
        raise Exception("the_p must be between +/- 90 degrees")
    if (
        the_p < 0
        and ((a1 + ((a2 - c) / 2) - (r1 + r2 + c)) * abs(tan_p))
        - (r1 + r2 + c)
        + r2
        + c
        > s
    ):
        # doesn't account for bottom chamfer, that would be more trouble than it's
        # worth to check, better safe than sorry
        raise Exception(
            "the_p is too negative, the resulting pin will intersect with the"
            "component body."
        )
    if l < 0:
        raise Exception("L cannot be negative")
    if s < 0:
        raise Exception("S cannot be negative")
    if r1 < 0:
        raise Exception("R1 cannot be negative")
    if l < (c + r2):
        raise Exception("L must be greater than c + R2")

    # If tb_s is is zero, the solver cannot converge as we have anobject with zero
    # volume, so enforce a minimum size here:
    if tb_s == 0:
        tb_s = 0.001

    A = a1 + a2
    A2_t = (a2 - c) / 2  # body top part height
    A2_b = A2_t  # body bottom part height
    D1_b = d1 - 2 * tan(radians(the)) * A2_b  # bottom width
    E1_b = e1 - 2 * tan(radians(the)) * A2_b  # bottom length
    D1_t1 = d1 - tb_s  # top part bottom width
    E1_t1 = e1 - tb_s  # top part bottom length
    D1_t2 = D1_t1 - 2 * tan(radians(the)) * A2_t  # top part upper width
    E1_t2 = E1_t1 - 2 * tan(radians(the)) * A2_t  # top part upper length

    # calculate chamfers
    totpinwidthx = (npx - 1) * pitch + b  # total width of all pins on the X side
    totpinwidthy = (npy - 1) * pitch + b  # total width of all pins on the Y side

    if cc1 != 0:
        cc1 = abs(
            min((d1 - totpinwidthx) / 2.0, (e1 - totpinwidthy) / 2.0, cc1) - 0.5 * tb_s
        )
        cc1 = min(cc1, max_cc1)

    cc = cc1

    def crect(
        wp: cq.Workplane, rw: float, rh: float, cv1: float, cv: float
    ) -> cq.Workplane:
        """
        Creates a rectangle with chamfered corners.
        wp: workplane object
        rw: rectangle width
        rh: rectangle height
        cv1: chamfer value for 1st corner (lower left)
        cv: chamfer value for other corners
        """
        points = [
            #    (-rw/2., -rh/2.+cv1),
            (-rw / 2.0, rh / 2.0 - cv),
            (-rw / 2.0 + cv, rh / 2.0),
            (rw / 2.0 - cv, rh / 2.0),
            (rw / 2.0, rh / 2.0 - cv),
            (rw / 2.0, -rh / 2.0 + cv),
            (rw / 2.0 - cv, -rh / 2.0),
            (-rw / 2.0 + cv1, -rh / 2.0),
            (-rw / 2.0, -rh / 2.0 + cv1),
        ]
        # return wp.polyline(points)
        return wp.polyline(
            points, includeCurrent=True
        ).wire()  # , forConstruction=True)

    if cc1 != 0:
        case = (
            cq.Workplane("XY")
            .workplane(centerOption="CenterOfMass", offset=a1)
            .moveTo(-D1_b / 2.0, -E1_b / 2.0 + (cc1 - (d1 - D1_b) / 4.0))
        )
        case = crect(
            case, D1_b, E1_b, cc1 - (d1 - D1_b) / 4.0, cc - (d1 - D1_b) / 4.0
        )  # bottom edges
        # show(case)
        case = (
            case.pushPoints([(0, 0)])
            .workplane(centerOption="CenterOfMass", offset=A2_b)
            .moveTo(-d1 / 2, -e1 / 2 + cc1)
        )
        case = crect(case, d1, e1, cc1, cc)  # center (lower) outer edges
        # show(case)
        case = (
            case.pushPoints([(0, 0)])
            .workplane(centerOption="CenterOfMass", offset=c)
            .moveTo(-d1 / 2, -e1 / 2 + cc1)
        )
        case = crect(case, d1, e1, cc1, cc)  # center (upper) outer edges
        # show(case)
        # case=cq.Workplane(cq.Plane.XY()).workplane(offset=c).moveTo(-D1_t1/2,-E1_t1/2+cc1-(D1-D1_t1)/4.)
        case = (
            case.pushPoints([(0, 0)])
            .workplane(centerOption="CenterOfMass", offset=0)
            .moveTo(-D1_t1 / 2, -E1_t1 / 2 + cc1 - (d1 - D1_t1) / 4.0)
        )
        case = crect(
            case, D1_t1, E1_t1, cc1 - (d1 - D1_t1) / 4.0, cc - (d1 - D1_t1) / 4.0
        )  # center (upper) inner edges
        # show(case)
        # stop
        cc1_t = cc1 - (d1 - D1_t2) / 4.0  # this one is defined because we use it later
        case = (
            case.pushPoints([(0, 0)])
            .workplane(centerOption="CenterOfMass", offset=A2_t)
            .moveTo(-D1_t2 / 2, -E1_t2 / 2 + cc1_t)
        )
        # cc1_t = cc1-(D1-D1_t2)/4. # this one is defined because we use it later
        case = crect(case, D1_t2, E1_t2, cc1_t, cc - (d1 - D1_t2) / 4.0)  # top edges
        # show(case)
        case = case.loft(ruled=True)
        if ef != 0:
            try:
                case = case.faces(">Z").fillet(ef)
            except Exception as exeption:
                print("Case top face failed.\n")
                print("{:s}\n".format(exeption))

    else:
        case = (
            cq.Workplane("XY")
            .workplane(centerOption="CenterOfMass", offset=a1)
            .rect(D1_b, E1_b)
            .workplane(centerOption="CenterOfMass", offset=A2_b)
            .rect(d1, e1)
            .workplane(centerOption="CenterOfMass", offset=c)
            .rect(d1, e1)
            .rect(D1_t1, E1_t1)
            .workplane(centerOption="CenterOfMass", offset=A2_t)
            .rect(D1_t2, E1_t2)
            .loft(ruled=True)
        )
        if ef != 0:
            try:
                case = case.faces(">Z").fillet(ef)
            except Exception as exeption:
                print("Case top face failed.\n")
                print("{:s}\n".format(exeption))

        # fillet the corners
        if ef != 0:
            BS = cq.selectors.BoxSelector
            try:
                case = case.edges(
                    BS((D1_t2 / 2, E1_t2 / 2, 0), (d1 / 2 + 0.1, e1 / 2 + 0.1, a2))  # type: ignore[no-untyped-call]
                ).fillet(ef)
            except Exception as exeption:
                print("Case fillet 1 failed\n")
                print("{:s}\n".format(exeption))

            try:
                case = case.edges(
                    BS((-D1_t2 / 2, E1_t2 / 2, 0), (-d1 / 2 - 0.1, e1 / 2 + 0.1, a2))  # type: ignore[no-untyped-call]
                ).fillet(ef)
            except Exception as exeption:
                print("Case fillet 2 failed\n")
                print("{:s}\n".format(exeption))

            try:
                case = case.edges(
                    BS((-D1_t2 / 2, -E1_t2 / 2, 0), (-d1 / 2 - 0.1, -e1 / 2 - 0.1, a2))  # type: ignore[no-untyped-call]
                ).fillet(ef)
            except Exception as exeption:
                print("Case fillet 3 failed\n")
                print("{:s}\n".format(exeption))

            try:
                case = case.edges(
                    BS((D1_t2 / 2, -E1_t2 / 2, 0), (d1 / 2 + 0.1, -e1 / 2 - 0.1, a2))  # type: ignore[no-untyped-call]
                ).fillet(ef)
            except Exception as exeption:
                print("Case fillet 4 failed\n")
                print("{:s}\n".format(exeption))

    epad_rotation = 0.0
    epad_offset_x = 0.0
    epad_offset_y = 0.0

    epad_r = params.get("epad")
    if epad_r is not None:
        if not isinstance(epad_r, list):
            epad = cq.Workplane("XY").circle(epad_r).extrude(a1)
        else:
            epad_r = cast(list[float], epad_r)
            D2 = float(epad_r[0])
            E2 = float(epad_r[1])
            if len(epad_r) > 2:
                epad_rotation = epad_r[2]
            if len(epad_r) > 3:
                if isinstance(epad_r[3], str):
                    if epad_r[3] == "-topin":
                        epad_offset_x = (D1_b / 2 - D2 / 2) * -1
                    elif epad_r[3] == "+topin":
                        epad_offset_x = D1_b / 2 - D2 / 2
                else:
                    epad_offset_x = epad_r[3]
            if len(epad_r) > 4:
                if isinstance(epad_r[4], str):
                    if epad_r[4] == "-topin":
                        epad_offset_y = (E1_b / 2 - E2 / 2) * -1
                    elif epad_r[4] == "+topin":
                        epad_offset_y = E1_b / 2 - E2 / 2
                else:
                    epad_offset_y = epad_r[4]
            epad = (
                cq.Workplane("XY")
                .box(D2, E2, a1)
                .translate((epad_offset_x, epad_offset_y, a1 / 2))
                .rotate((0, 0, 0), (0, 0, 1), epad_rotation)
            )
        case = case.cut(epad)
    else:
        epad = None

    marker_diameter = max(D1_b, E1_b) / 10.0
    if min(D1_b, E1_b) < 5 * marker_diameter:
        marker_edge_clearance = marker_diameter / 4.0
    else:
        marker_edge_clearance = marker_diameter / 2.0
    if marker == "bar":
        pinmark = (
            cq.Workplane("XY")
            .workplane(centerOption="CenterOfMass", offset=A)
            .box(marker_diameter, E1_t2 - marker_edge_clearance, a2 / 4)
            .translate(
                (
                    -D1_t2 / 2 + marker_diameter / 2.0 + marker_edge_clearance / 2,
                    0.0,
                    -a2 / 8,
                )
            )
        )
        case = case.cut(pinmark)
    elif marker == "circle":
        pinmark = (
            cq.Workplane(
                "XZ",
                (
                    -D1_t2 / 2 + marker_edge_clearance + marker_diameter / 2.0,
                    -E1_t2 / 2 + marker_edge_clearance + marker_diameter / 2.0,
                    A,
                ),
            )
            .rect(marker_diameter / 2, -a2 / 4, False)
            .revolve()
        )
        case = case.cut(pinmark)
    else:  # if marker == "none"
        pinmark = None

    # calculated dimensions for pin
    R1_o = r1 + c  # pin upper corner, outer radius
    R2_o = r2 + c  # pin lower corner, outer radius

    # Create a pin object at the center of top side.
    bpin = (
        cq.Workplane("YZ")
        .moveTo(-tb_s, a1 + A2_b)
        .line(s + tb_s, 0)
        .radiusArc(
            (
                s + (r1 * cos(radians(the_p))),
                a1 + A2_b - r1 + (r1 * sin(radians(the_p))),
            ),
            r1,
        )
        .lineTo(
            ((e - e1) / 2) - l + R2_o - (R2_o * cos(radians(the_p))),
            r2 + c - (R2_o * sin(radians(the_p))),
        )
        .radiusArc((((e - e1) / 2) - l + R2_o, 0), -R2_o)
        .line(l - R2_o, 0)
        .line(0, c)
        .line(-l + R2_o, 0)
        .radiusArc(
            (
                ((e - e1) / 2) - l + R2_o - (r2 * cos(radians(the_p))),
                r2 + c - (r2 * sin(radians(the_p))),
            ),
            r2,
        )
        .lineTo(
            s + (R1_o * cos(radians(the_p))),
            a1 + A2_b - r1 + (R1_o * sin(radians(the_p))),
        )
        .radiusArc((s, a1 + A2_b + c), -R1_o)
        .line(-s - tb_s, 0)
        .close()
        .extrude(b)
        .translate((-b / 2, 0, 0))
    )

    # Define all pin locations and rotations first
    h_coords = [((npx - 1) * pitch / 2) - i * pitch for i in range(npx)]
    v_coords = [((npy - 1) * pitch / 2) - i * pitch for i in range(npy)]

    # Filter out excluded pins
    all_locs = (
        [
            cq.Location(cq.Vector(-x, -e1 / 2, 0), cq.Vector(0, 0, 1), 180)
            for x in h_coords
        ]  # Bottom (-> Left with -90°)
        + [
            cq.Location(cq.Vector(d1 / 2, -y, 0), cq.Vector(0, 0, 1), -90)
            for y in v_coords
        ]  # Right (-> Bottom with -90°)
        + [
            cq.Location(cq.Vector(x, e1 / 2, 0)) for x in h_coords
        ]  # Top (-> Right with -90°)
        + [
            cq.Location(cq.Vector(-d1 / 2, y, 0), cq.Vector(0, 0, 1), 90)
            for y in v_coords
        ]  # Left (-> Top with -90°)
    )

    valid_locs = [loc for i, loc in enumerate(all_locs, 1) if i not in excluded_pins]

    # Create all pins in a single, efficient operation
    pins = (
        cq.Workplane("XY")
        .pushPoints(valid_locs)
        .each(lambda loc: bpin.val().located(loc), combine="a")  # type: ignore
    )

    case = case.cut(pins)

    return (case, pins, epad, pinmark)
