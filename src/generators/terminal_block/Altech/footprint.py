#!/usr/bin/env python3

from scripts.tools.footprint_scripts_terminal_blocks import (
    makeTerminalBlock45Degree,
    makeTerminalBlockStd,
)

script_generated_note = "generated with kicad-footprint-generator TerminalBlock_Altech"
classname = "TerminalBlock_Altech"


def gen_ak100():

    pins = range(2, 24 + 1)
    rm = 5.0  # pitch
    package_height = 9  # overall extension in y-direction
    leftbottom_offset = [2.5, 4.0, 2.5]
    ddrill = 1.3
    pad = [3, 3]
    bevel_height = [2]  # estimatew
    screw_diameter = 4
    secondHoleDiameter = 2
    secondHoleOffset = [0, -3.2]  # estimated
    fabref_offset = [0, 3.6]
    for p in pins:
        name = "AK100"
        webpage = "https://www.altechcorp.com/PDFS/PCBMETRC.PDF#page=3"
        classname_description = "Terminal block Altech {0}".format(name)
        footprint_name = "Altech_{0}_1x{1:02}_P{2:3.2f}mm".format(name, p, rm)

        makeTerminalBlockStd(
            footprint_name=footprint_name,
            pins=p,
            rm=rm,
            package_height=package_height,
            leftbottom_offset=leftbottom_offset,
            ddrill=ddrill,
            pad=pad,
            bevel_height=bevel_height,
            screw_diameter=screw_diameter,
            secondHoleDiameter=secondHoleDiameter,
            secondHoleOffset=secondHoleOffset,
            fabref_offset=fabref_offset,
            tags_additional=[],
            lib_name=classname,
            classname=classname,
            classname_description=classname_description,
            webpage=webpage,
            script_generated_note=script_generated_note,
        )


def gen_ak300():

    pins = range(2, 24 + 1)
    rm = 5.0  # pitch
    package_height = 12.5  # overall extension in y-direction
    leftbottom_offset = [2.5, 6.5, 2.5]
    ddrill = 1.3
    pad = [3, 3]
    bevel_height = [6.5]  # estimated
    opening = [2.7, 5.5]  # y-size estimated
    opening_xoffset = 0
    opening_yoffset = 0.5  # estimated
    opening_elliptic = False
    second_ellipse_size = [3.5, 2.7]  # estimated from 3.5mm screw diameter
    second_ellipse_offset = [0, -4.5]  # estimated
    fabref_offset = [0, -1.2]
    for p in pins:
        name = "AK300".format(p)
        webpage = "https://www.altechcorp.com/PDFS/PCBMETRC.PDF#page=5"
        classname_description = "Terminal block Altech {0}".format(name)
        footprint_name = "Altech_{0}_1x{1:02}_P{2:3.2f}mm_45-Degree".format(name, p, rm)
        makeTerminalBlock45Degree(
            footprint_name=footprint_name,
            pins=p,
            rm=rm,
            package_height=package_height,
            leftbottom_offset=leftbottom_offset,
            ddrill=ddrill,
            pad=pad,
            opening=opening,
            opening_xoffset=opening_xoffset,
            opening_yoffset=opening_yoffset,
            opening_elliptic=opening_elliptic,
            secondEllipseSize=second_ellipse_size,
            secondEllipseOffset=second_ellipse_offset,
            bevel_height=bevel_height,
            fabref_offset=fabref_offset,
            tags_additional=[],
            lib_name=classname,
            classname=classname,
            classname_description=classname_description,
            webpage=webpage,
            script_generated_note=script_generated_note,
        )


if __name__ == "__main__":
    gen_ak100()
    gen_ak300()
