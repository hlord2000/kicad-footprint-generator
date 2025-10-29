#!/usr/bin/env python3

from KicadModTree import *
from scripts.tools.global_config_files import global_config as GC

datasheet = "http://akizukidenshi.com/download/ds/switronic/ST-005-G.pdf"
footprint_name = "Jack_3.5mm_Switronic_ST-005-G_horizontal"
lib_name = "Connector_Audio"
global_config = GC.DefaultGlobalConfig()


baseWidth = 11.5
baseHeight = 6.5
outletHeight = 5.0
outletWidth = 2.5

padHoleSize = 1.2
mountingHoleSize = 1.0

frontPadOffset = 3.5
frontPadSpacing = 5.8
mountingHoleOffset = 7.0
mountingHoleSpacing = 5.0
backPadOffset = 11.0
backPadSpacing = 4.5


f = Footprint(footprint_name, FootprintType.THT)
f.setDescription("3.5mm horizontal headphones jack, "+datasheet)
f.setTags("Connector Audio Switronic ST-005-G")
f.append(Model(filename=f"{global_config.model_3d_prefix}{lib_name}.3dshapes/{footprint_name}{global_config.model_3d_suffix}",
               at=[0.0, 0.0, 0.0],
               scale=[1.0, 1.0, 1.0],
               rotate=[0.0, 0.0, 0.0]))

s = [1.0, 1.0]
sFabRef = [0.7, 0.7]

t1 = 0.1
t2 = 0.15

wCrtYd = 0.05
wFab = 0.1
wSilkS = 0.12
crtYdClearance = 0.5
silkClearance = 0.2

padSizeDiffFromHole = 0.7
padSize = [padHoleSize + padSizeDiffFromHole, padHoleSize + padSizeDiffFromHole]
padDrill = [padHoleSize, padHoleSize]

xCenter = 0.0
xFabBaseLeft = outletWidth - ((baseWidth + outletWidth) / 2)
xFrontPad = xFabBaseLeft + frontPadOffset
xMountingHole = xFabBaseLeft + mountingHoleOffset
xBackPad = xFabBaseLeft + backPadOffset
xFabRight = (outletWidth + baseWidth) / 2
xSilkRight = xFabRight + silkClearance
xSilkFrontPadRight = xFrontPad + padHoleSize
xRightCrtYd = xBackPad + padSize[0] / 2 + crtYdClearance

xFabLeft = -xFabRight
xLeftCrtYd = xFabLeft - crtYdClearance
xSilkBaseLeft = xFabBaseLeft - silkClearance
xSilkLeft = -xSilkRight
xSilkFrontPadLeft = xFrontPad - padHoleSize
xSilkBackPadLeft = xBackPad - padHoleSize

yCenter = 0.0
yFrontPadBottom = frontPadSpacing / 2
yMountingHoleBottom = mountingHoleSpacing / 2
yBackPadBottom = backPadSpacing / 2
yFabOutletBottom = outletHeight / 2
yFabBottom = baseHeight / 2
ySilkBottom = yFabBottom + silkClearance
ySilkOutletBottom = yFabOutletBottom + silkClearance
ySilkBackPadBottom = yBackPadBottom - padHoleSize
yBottomCrtYd = yFrontPadBottom + padSize[0] / 2 + crtYdClearance

yFrontPadTop = -yFrontPadBottom
yMountingHoleTop = -yMountingHoleBottom
yBackPadTop = -yBackPadBottom
yFabTop = -yFabBottom
yFabOutletTop = -yFabOutletBottom
ySilkTop = -ySilkBottom
ySilkOutletTop = -ySilkOutletBottom
ySilkBackPadTop = -ySilkBackPadBottom
yTopCrtYd = -yBottomCrtYd

yValue = yFabBottom + 1.25
yRef = yFabTop - 1.25

f.append(Property(name=Property.REFERENCE, text="REF**", at=[xCenter, yRef],
              layer="F.SilkS", size=s, thickness=t2))
f.append(Property(name=Property.VALUE, text=footprint_name, at=[xCenter, yValue],
              layer="F.Fab", size=s, thickness=t2))
f.append(Text(text='${REFERENCE}', at=[xCenter, yCenter],
              layer="F.Fab", size=sFabRef, thickness=t1))

f.append(RectLine(start=[xLeftCrtYd, yTopCrtYd],
                  end=[xRightCrtYd, yBottomCrtYd],
                  layer="F.CrtYd", width=wCrtYd))

f.append(Circle(center=[xBackPad, ySilkBackPadTop], radius=0.3, layer="F.Fab"))
f.append(PolygonLine(shape=[[xFabLeft, yFabOutletTop],
                               [xFabBaseLeft, yFabOutletTop],
                               [xFabBaseLeft, yFabTop],
                               [xFabRight, yFabTop],
                               [xFabRight, yFabBottom],
                               [xFabBaseLeft, yFabBottom],
                               [xFabBaseLeft, yFabOutletBottom],
                               [xFabLeft, yFabOutletBottom],
                               [xFabLeft, yFabOutletTop]],
                     layer="F.Fab", width=wFab))

f.append(PolygonLine(shape=[[xSilkFrontPadLeft, ySilkBottom],
                               [xSilkBaseLeft, ySilkBottom],
                               [xSilkBaseLeft, ySilkOutletBottom]],
                     layer="F.SilkS", width=wSilkS))
f.append(PolygonLine(shape=[[xSilkBaseLeft, ySilkOutletTop],
                               [xSilkBaseLeft, ySilkTop],
                               [xSilkFrontPadLeft, ySilkTop]],
                     layer="F.SilkS", width=wSilkS))
f.append(Line(start=[xSilkFrontPadRight, ySilkTop],
              end=[xSilkBackPadLeft, ySilkTop],
              layer="F.SilkS", width=wSilkS))
f.append(Line(start=[xSilkFrontPadRight, ySilkBottom],
              end=[xSilkRight, ySilkBottom],
              layer="F.SilkS", width=wSilkS))
f.append(Line(start=[xSilkRight, ySilkBackPadTop],
              end=[xSilkRight, ySilkBackPadBottom],
              layer="F.SilkS", width=wSilkS))

f.append(Pad(number="T", type=Pad.TYPE_THT, shape=Pad.SHAPE_CIRCLE,
             at=[xFrontPad, yFrontPadTop], size=padSize,
             drill=padDrill, layers=Pad.LAYERS_THT))
f.append(Pad(number="T", type=Pad.TYPE_THT, shape=Pad.SHAPE_CIRCLE,
             at=[xFrontPad, yFrontPadBottom], size=padSize,
             drill=padDrill, layers=Pad.LAYERS_THT))
f.append(Pad(number="R", type=Pad.TYPE_THT, shape=Pad.SHAPE_RECT,
             at=[xBackPad, yBackPadTop], size=padSize,
             drill=padDrill, layers=Pad.LAYERS_THT))
f.append(Pad(number="S", type=Pad.TYPE_THT, shape=Pad.SHAPE_CIRCLE,
             at=[xBackPad, yBackPadBottom], size=padSize,
             drill=padDrill, layers=Pad.LAYERS_THT))
f.append(Pad(type=Pad.TYPE_NPTH, shape=Pad.SHAPE_CIRCLE,
             at=[xMountingHole, yMountingHoleBottom], size=mountingHoleSize,
             drill=mountingHoleSize, layers=Pad.LAYERS_NPTH))
f.append(Pad(type=Pad.TYPE_NPTH, shape=Pad.SHAPE_CIRCLE,
             at=[xMountingHole, yMountingHoleTop], size=mountingHoleSize,
             drill=mountingHoleSize, layers=Pad.LAYERS_NPTH))

lib = KicadPrettyLibrary(lib_name, None)
lib.save(f)
