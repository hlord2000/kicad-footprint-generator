#!/usr/bin/env python3

from KicadModTree import *
from scripts.tools.drawing_tools import *
from scripts.tools.global_config_files import global_config as GC
global_config = GC.DefaultGlobalConfig()


def ptc_fuse_tht(args):
    footprint_name = args["name"]
    datasheet = args["datasheet"]
    ihold = args["ihold"]
    itrip = args["itrip"]
    drill = args["drill"]
    w = args["width"]
    h = args["height"]
    pitch = args["pitch"]
    offset = args["offset"]
    lib_name = "Fuse"

    f = Footprint(footprint_name, FootprintType.THT)
    f.setDescription("PTC Resettable Fuse, Ihold = " + ihold +
                     ", Itrip=" + itrip + ", " + datasheet)
    f.setTags("ptc resettable fuse polyfuse THT")
    f.append(Model(filename=global_config.model_3d_prefix + lib_name + ".3dshapes/" +
                   footprint_name + global_config.model_3d_suffix,
                   at=[0.0, 0.0, 0.0],
                   scale=[1.0, 1.0, 1.0],
                   rotate=[0.0, 0.0, 0.0]))

    d = [drill, drill]
    p = [drill + 1.0, drill + 1.0]

    s = [1.0, 1.0]
    t = 0.15

    wCrtYd = 0.05
    wFab = 0.1
    wSilkS = 0.12

    silk = 0.1
    crtYd = 0.25

    clearance = 0.3

    xPin1 = 0.0
    xPin2 = pitch
    xCenter = pitch / 2
    xLeft = xCenter - w / 2
    xRight = xCenter + w / 2
    xLeftSilk = xLeft - silk
    xRightSilk = xRight + silk
    xLeftCrtYd = xLeft - crtYd
    xRightCrtYd = xRight + crtYd

    yPin1 = 0.0
    yPin2 = offset
    yCenter = offset / 2
    yTop = yCenter - h / 2
    yBottom = yCenter + h / 2
    yRef = yTop - 1.0
    yValue = yBottom + 1.0
    yTopSilk = yTop - silk
    yBottomSilk = yBottom + silk
    yTopCrtYd = yTop - crtYd
    yBottomCrtYd = yBottom + crtYd

    keepouts: list[GeomShapeClosed] = []
    ko_diameter = p[0] + 2 * clearance

    # Pads
    pin = 1
    for coord in [[xPin1, yPin1], [xPin2, yPin2]]:
        f.append(Pad(number=str(pin), type=Pad.TYPE_THT, shape=Pad.SHAPE_CIRCLE,
                 at=coord, size=p, layers=Pad.LAYERS_THT, drill=d))
        keepouts += addKeepoutRound(
            coord[0], coord[1], ko_diameter, ko_diameter
        )
        pin = pin + 1

    # Text
    f.append(Property(name=Property.REFERENCE, text="REF**", at=[xCenter, yRef],
                  layer="F.SilkS", size=s, thickness=t))
    f.append(Property(name=Property.VALUE, text=footprint_name, at=[xCenter, yValue],
                  layer="F.Fab", size=s, thickness=t))
    f.append(Text(text='${REFERENCE}', at=[xCenter, yCenter],
                  layer="F.Fab", size=s, thickness=t))

    # Fab outline
    f.append(RectLine(start=[xLeft, yTop],
                      end=[xRight, yBottom],
                      layer="F.Fab", width=wFab))

    # Silk outline
    addRectWithKeepout(f, xLeftSilk, yTopSilk,
                       xRightSilk - xLeftSilk, yBottomSilk - yTopSilk,
                       "F.SilkS", wSilkS, keepouts)

    # Courtyard
    f.append(RectLine(start=[xLeftCrtYd, yTopCrtYd],
                      end=[xRightCrtYd, yBottomCrtYd],
                      layer="F.CrtYd", width=wCrtYd))

    lib = KicadPrettyLibrary(lib_name, None)
    lib.save(f)


if __name__ == '__main__':
    parser = ModArgparser(ptc_fuse_tht)
    # the root node of .yml files is parsed as name
    parser.add_parameter("name", type=str, required=True)
    parser.add_parameter("datasheet", type=str, required=False,
                         default="http://www.bourns.com/docs/Product-Datasheets/mfrg.pdf")
    parser.add_parameter("ihold", type=str, required=True)
    parser.add_parameter("itrip", type=str, required=True)
    parser.add_parameter("drill", type=float, required=False, default=1.01)
    parser.add_parameter("pitch", type=float, required=False, default=5.1)
    parser.add_parameter("height", type=float, required=False, default=3.0)
    parser.add_parameter("width", type=float, required=True)
    parser.add_parameter("offset", type=float, required=False, default=1.2)

    # now run our script which handles the whole part of parsing the files
    parser.run()
