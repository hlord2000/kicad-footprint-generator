#!/usr/bin/env python

from KicadModTree import *  # NOQA
from KicadModTree import KicadPrettyLibrary
from KicadModTree.nodes.base.Pad import Pad
from scripts.tools.global_config_files import global_config as GC

global_config = GC.DefaultGlobalConfig()

lib_name = "Buzzer_Beeper"

def buzzer_round_tht(args):
    # some variables
    buzzer_center = args['pad_spacing'] / 2.
    buzzer_radius = args['diameter'] / 2.

    # init kicad footprint
    kicad_mod = Footprint(args['name'], FootprintType.THT)
    kicad_mod.setDescription(args['datasheet'])
    kicad_mod.setTags("buzzer round tht")

    # set general values
    kicad_mod.append(Property(name=Property.REFERENCE, text='REF**', at=[buzzer_center, -buzzer_radius - 1], layer='F.SilkS'))
    kicad_mod.append(Text(text='${REFERENCE}', at=[buzzer_center, -buzzer_radius - 1], layer='F.Fab'))
    kicad_mod.append(Property(name=Property.VALUE, text=args['name'], at=[buzzer_center, buzzer_radius + 1], layer='F.Fab'))

    # create silkscreen
    kicad_mod.append(Circle(center=[buzzer_center, 0], radius=buzzer_radius + 0.1, layer='F.SilkS'))

    kicad_mod.append(Text(text='+', at=[0, -args['pad_size'] / 2 - 1], layer='F.SilkS'))
    kicad_mod.append(Text(text='+', at=[0, -args['pad_size']/2 - 1], layer='F.Fab'))

    # create fabrication layer
    kicad_mod.append(Circle(center=[buzzer_center, 0], radius=buzzer_radius, layer='F.Fab'))

    # create courtyard
    kicad_mod.append(Circle(center=[buzzer_center, 0], radius=buzzer_radius + args['courtyard'], layer='F.CrtYd'))

    # create pads
    kicad_mod.append(Pad(number=1, type=Pad.TYPE_THT, shape=Pad.SHAPE_RECT,
                         at=[0, 0], size=args['pad_size'], drill=args['hole_size'], layers=Pad.LAYERS_THT))
    kicad_mod.append(Pad(number=2, type=Pad.TYPE_THT, shape=Pad.SHAPE_CIRCLE,
                         at=[args['pad_spacing'], 0], size=args['pad_size'], drill=args['hole_size'], layers=Pad.LAYERS_THT))

    # add model
    kicad_mod.append(Model(
        filename="{prefix}{lib_name}.3dshapes/{fp_name}{suffix}".format(prefix = global_config.model_3d_prefix, suffix=global_config.model_3d_suffix, lib_name=lib_name, fp_name=args["name"]),
        at=[0, 0, 0], scale=[1, 1, 1], rotate=[0, 0, 0]))


    # write file
    lib = KicadPrettyLibrary(lib_name, args["output_dir"])
    lib.save(kicad_mod)


if __name__ == '__main__':
    parser = ModArgparser(buzzer_round_tht)
    parser.add_parameter("name", type=str, required=True)  # the root node of .yml files is parsed as name
    parser.add_parameter("datasheet", type=str, required=False)
    parser.add_parameter("courtyard", type=float, required=False, default=0.25)
    parser.add_parameter("diameter", type=float, required=True)
    parser.add_parameter("hole_size", type=float, required=True)
    parser.add_parameter("pad_size", type=float, required=True)
    parser.add_parameter("pad_spacing", type=float, required=True)

    parser.run()  # now run our script which handles the whole part of parsing the files
