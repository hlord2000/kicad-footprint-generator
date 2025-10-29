#!/usr/bin/env python3
#SPDX-License-Identifier: GPL-3.0-or-later
#Copyright (c) 2024, Lothar Felten <lothar.felten@gmail.com>
"""
m2_card 
M.2 card footprint generator script for KiCad
Supported dimensions: 2242, 2280, 22110, 3042, 3080, 30110
Supported notches: A, B, E and M
"""
import os
import argparse
import yaml

from KicadModTree import *
from scripts.tools.drawing_tools import round_to_grid
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.global_config_files import global_config as GC

global_config = GC.DefaultGlobalConfig()
lib_name = "Connector_PCBEdge"

notchTypes = ['A', 'B', 'E', 'M']
notchOffset = {'A':6.625, 'B':5.625, 'E':2.625, 'M':-6.125}
widthTypes = [22, 30]
heightTypes = [30, 42, 60, 80, 110]
description = "M.2 card edge connector"
datasheet = "https://web.archive.org/web/20210118201723/http://read.pudn.com/downloads794/doc/project/3133918/PCIe_M.2_Electromechanical_Spec_Rev1.0_Final_11012013_RS_Clean.pdf"

def generate_footprint(widthType, heightType, notchType, configuration):
    footprint_name = "M.2_" + str(widthType) + str(heightType) + "-xx-" + str(notchType)
    f = Footprint(footprint_name, FootprintType.UNSPECIFIED)
    f.setDescription(description + ", " + datasheet)
    f.setTags("Connector PCBEdge "+footprint_name)
    f.excludeFromBOM = True
    f.excludeFromPositionFiles = True
    f.append(Property(name=Property.REFERENCE, text='REF**', at=[0, -3], layer='F.SilkS'))
    f.append(Property(name=Property.VALUE, text=footprint_name, at=[1.5, 3], layer='F.Fab'))

    #settings
    padCount = 75
    padToPad = 0.5
    padHeightTop = 1.5
    padHeightBottom = 2.0
    padChamfer = 0.5
    padWidth = 0.35
    padShape = Pad.SHAPE_ROUNDRECT
    radius_handler = RoundRadiusHandler(
        radius_ratio=0.2,
    )
    padRadiusRatio = 0.2
    notchWidth = 1.2
    notch = notchOffset.get(notchType)
    cutWidth = 0.2
    conWidth = 19.85
    conHeight = 4
    conRadius = 0.5
    holeWidth = 3.5
    holeCopperWidth = 1.5
    layers_top = ['F.Cu', 'F.Mask']
    layers_bottom = ['B.Cu', 'B.Mask']
    yPad = conHeight - padHeightTop/2 - padChamfer
    xPadRight = ((padCount-1)/2 * padToPad)/2
    triangleWidth = 0.8
    courtyardWidth = 0.1
    courtyardBorder = 0.1
    courtyardRadius = 3
    t1 = 0.1
    t2 = 0.15
    refSize = [0.7, 0.7]
    textsize = [1.0, 1.0]
    chamferLength = 0.30
    chamferText = "Chamfer 20 degree " + str(chamferLength) + " mm"
    chamferOffset = 5.5
    thicknessText = "PCB thickness 0.8 mm"
    thicknessOffset = 7
    valueTextOffset = -1.5
    referenceTextOffset = (-conWidth/2)+4
   
    # connector cutout
    f.append(PolygonLine(shape=[[(-holeWidth/2), -(heightType-conHeight)],
        [(-widthType/2), -(heightType-conHeight)],
        [(-widthType/2), 0],
        [(-conRadius-conWidth/2), 0]],
        layer="Edge.Cuts", width=cutWidth))
    f.append(Arc(center=[-(conWidth/2)-conRadius, conRadius],
        start=[-(conWidth/2)-conRadius, 0],
        angle=90.0, layer="Edge.Cuts", width=cutWidth))
    f.append(PolygonLine(shape=[[(-conWidth/2), conRadius],
        [(-conWidth/2), conHeight],
        [(notch-(notchWidth/2)), conHeight],
        [(notch-(notchWidth/2)), conRadius]],
        layer="Edge.Cuts", width=cutWidth))
    f.append(Arc(center=[notch, conRadius],
        start=[(notch-(notchWidth/2)), conRadius],
        angle=180.0, layer="Edge.Cuts", width=cutWidth))
    f.append(PolygonLine(shape=[[(notch+(notchWidth/2)), conRadius],
        [(notch+(notchWidth/2)), conHeight],
        [(conWidth/2), conHeight],
        [(conWidth/2), conRadius]],
        layer="Edge.Cuts", width=cutWidth))
    f.append(Arc(center=[(conWidth/2)+conRadius, conRadius],
        start=[(conWidth/2)+conRadius, 0],
        angle=-90.0, layer="Edge.Cuts", width=cutWidth))
    f.append(PolygonLine(shape=[[(conRadius+conWidth/2), 0],
        [(widthType/2), 0],
        [(widthType/2), -(heightType-conHeight)],
        [(holeWidth/2), -(heightType-conHeight)]],
        layer="Edge.Cuts", width=cutWidth))
    f.append(Arc(center=[0, -(heightType-conHeight)],
        start=[(holeWidth/2), -(heightType-conHeight)],
        angle=180.0, layer="Edge.Cuts", width=cutWidth))
        
    # mounting hole copper - TODO: this overlaps with the cutout on the edges of the arc
    #f.append(Arc(center=[0, -(heightType-conHeight)],
    #    start=[(holeWidth/2)+(holeCopperWidth/2), -(heightType-conHeight)],
    #    angle=180.0, layer="F.Cu", width=holeCopperWidth))
        
    # courtyard
    f.append(RectLine(start=[-((widthType+courtyardBorder)/2), 0-courtyardBorder],
        end=[((widthType+courtyardBorder)/2), conHeight+courtyardBorder],
        layer="F.CrtYd"))
    f.append(PolygonLine(shape=[[-(courtyardRadius), -(heightType-conHeight)],
        [(courtyardRadius), -(heightType-conHeight)]],
        layer="F.CrtYd"))
    f.append(Arc(center=[0, -(heightType-conHeight)],
        start=[-(courtyardRadius), -(heightType-conHeight)],
        angle=-180.0, layer="F.CrtYd"))        
    f.append(PolygonLine(shape=[[-(courtyardRadius), -(heightType-conHeight)],
        [(courtyardRadius), -(heightType-conHeight)]],
        layer="B.CrtYd"))
    f.append(Arc(center=[0, -(heightType-conHeight)],
        start=[-(courtyardRadius), -(heightType-conHeight)],
        angle=-180.0, layer="B.CrtYd"))   
        
    # chamfer
    f.append(PolygonLine(shape=[[-(conWidth/2), conHeight - chamferLength],
        [(notch-(notchWidth/2)), conHeight - chamferLength]],
        layer="Dwgs.User", width=cutWidth))
    f.append(PolygonLine(shape=[[+(conWidth/2), conHeight - chamferLength],
        [(notch+(notchWidth/2)), conHeight - chamferLength]],
        layer="Dwgs.User", width=cutWidth))
    f.append(Text(text=chamferText, at=[0, chamferOffset],
        layer="Cmts.User", size=refSize, thickness=t2))
    f.append(Text(text=thicknessText, at=[0, thicknessOffset],
        layer="Cmts.User", size=refSize, thickness=t2))
        
    # silkscreen: triangle and key type
    f.append(PolygonLine(shape=[[xPadRight-(triangleWidth/2),0],
        [xPadRight+(triangleWidth/2), 0],
        [xPadRight, (triangleWidth)],
        [xPadRight-(triangleWidth/2), 0]],
        layer="F.SilkS"))
    f.append(Text(text=str(notchType), at=[notch+notchWidth, 0],
        layer="F.SilkS", size=textsize, thickness=t1))

    # pads
    for i in range(0, padCount):
        x = xPadRight - (padToPad/2 * i)
        if i%2 == 0:
            layer=layers_top
            y = yPad
            padSize = [padWidth, padHeightTop]
        else:
            layer=layers_bottom
            y = yPad-0.25
            padSize = [padWidth, padHeightBottom]
        if abs(notch - x) > 1:
            f.append(Pad(number=i+1, type=Pad.TYPE_CONNECT, shape=padShape,
                     at=[x, y], size=padSize, layers=layer,
                     round_radius_handler=radius_handler))
    #text
    body_edge={'left':-(widthType/2), 'right':(widthType/2), 'top':-(heightType-conHeight), 'bottom':0}
    courtyard={'top':-(heightType-conHeight), 'bottom':0}
    addTextFields(kicad_mod=f, configuration=configuration, body_edges=body_edge,
    courtyard=courtyard, fp_name=footprint_name, text_y_inside_position='center', allow_rotation=True)

    lib = KicadPrettyLibrary(lib_name, None)
    lib.save(f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='use config .yaml files to create footprints.')
    parser.add_argument('--global_config', type=str, nargs='?', help='the config file defining how the footprint will look like. (KLC)', default='../../tools/global_config_files/config_KLCv3.0.yaml')
    parser.add_argument('--series_config', type=str, nargs='?', help='the config file defining series parameters.', default='../conn_config_KLCv3.yaml')
    args = parser.parse_args()

    with open(args.global_config, 'r') as config_stream:
        try:
            configuration = yaml.safe_load(config_stream)
            global_config = GC.GlobalConfig(configuration)
        except yaml.YAMLError as exc:
            print(exc)

    with open(args.series_config, 'r') as config_stream:
        try:
            configuration.update(yaml.safe_load(config_stream))
        except yaml.YAMLError as exc:
            print(exc)
    generate_footprint(30,30,'A',configuration)
    generate_footprint(30,30,'E',configuration)
    generate_footprint(30,42,'B',configuration)
    generate_footprint(22,30,'A',configuration)
    generate_footprint(22,30,'E',configuration)
    generate_footprint(22,30,'B',configuration)
    generate_footprint(22,30,'M',configuration)
    generate_footprint(22,42,'B',configuration)
    generate_footprint(22,42,'M',configuration)
    generate_footprint(22,60,'B',configuration)
    generate_footprint(22,60,'M',configuration)
    generate_footprint(22,80,'B',configuration)
    generate_footprint(22,80,'M',configuration)
    generate_footprint(22,110,'B',configuration)
    generate_footprint(22,110,'M',configuration)

