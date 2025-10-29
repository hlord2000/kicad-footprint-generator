#!/usr/bin/env python3

from KicadModTree import *  # NOQA

import argparse

from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.footprint_scripts_terminal_blocks import *
from scripts.tools.global_config_files.global_config import GlobalConfig


class FourUcon_TerminalBlock(FootprintGenerator):

    script_generated_note = "script-generated using https://gitlab.com/kicad/libraries/kicad-footprint-generator/-/tree/master/scripts/TerminalBlock_4Ucon"
    classname = "TerminalBlock_4Ucon"

    def generateFootprint(self, pins: int):
        raise NotImplementedError()


class FourUcon_H8_3_TerminalBlock(FourUcon_TerminalBlock):

    # Pins known to be available for this footprint type
    PINS = [2,3,4,5,6,7,8,9,10,11,12,13,14,15]

    def generateFootprint(self, pins: int):

        rm = 3.5
        package_height = 8.3
        leftbottom_offset = [2.25, package_height - 3.7]
        ddrill = 1.3
        pad = [2.6, 2.6]
        bevel_height = [3.5]
        opening = [2.8, 3.75]
        opening_yoffset = package_height - 0.7 - opening[1]
        secondHoleDiameter = 2
        secondHoleOffset = [0, -(3.7 - 2.1)]
        thirdHoleDiameter = 0
        thirdHoleOffset = [0, 0]
        fourthHoleDiameter = 0
        fourthHoleOffset = [0, 0]
        fabref_offset = [0, 3]
        nibbleSize = None
        nibblePos = None

        itemno = 10691 + pins

        webpage = f"http://www.4uconnector.com/online/object/4udrawing/{itemno}.pdf"
        classname_description = f"Terminal Block 4Ucon ItemNo. {itemno}"
        footprint_name = f"TerminalBlock_4Ucon_1x{pins:02}_P{rm:3.2f}mm_Vertical"

        kicad_mod = makeTerminalBlockVertical(
            footprint_name=footprint_name,
            pins=pins,
            rm=rm,
            package_height=package_height,
            leftbottom_offset=leftbottom_offset,
            ddrill=ddrill,
            pad=pad,
            opening=opening,
            opening_yoffset=opening_yoffset,
            bevel_height=bevel_height,
            secondHoleDiameter=secondHoleDiameter,
            secondHoleOffset=secondHoleOffset,
            thirdHoleDiameter=thirdHoleDiameter,
            thirdHoleOffset=thirdHoleOffset,
            fourthHoleDiameter=fourthHoleDiameter,
            fourthHoleOffset=fourthHoleOffset,
            nibbleSize=nibbleSize,
            nibblePos=nibblePos,
            fabref_offset=fabref_offset,
            tags_additional=[],
            lib_name=None,
            classname=self.classname,
            classname_description=classname_description,
            webpage=webpage,
            script_generated_note=self.script_generated_note,
        )

        self.add_standard_3d_model_to_footprint(kicad_mod, self.classname, footprint_name)
        self.write_footprint(kicad_mod, self.classname)


class FourUCon_H7_TerminalBlock(FourUcon_TerminalBlock):

    PINS = [2,3,4,5,6,7,8,9,10,11,12,13,14,15]
    ITEM_NOS=[19963,20193,20001,20223,19964,10684,19965,10686,10687,10688,10689,10690,10691,10692]

    def generateFootprint(self, pins: int):

        assert pins in self.PINS, f"Invalid number of pins: {pins}"
        index = self.PINS.index(pins)
        itemno = self.ITEM_NOS[index]

        rm=3.5
        package_height=7
        leftbottom_offset=[2.1, package_height-3.4]
        ddrill=1.2
        pad=[2.4,2.4]
        screw_diameter=2.75
        bevel_height=[1.5]
        slit_screw=False
        screw_pin_offset=[0,0]
        secondHoleDiameter=0
        secondHoleOffset=[0,0]
        thirdHoleDiameter=0
        thirdHoleOffset=[0,-4]
        fourthHoleDiameter=0
        fourthHoleOffset=[0,0]
        fabref_offset=[0,2.8]
        nibbleSize = None
        nibblePos = None

        webpage=f"http://www.4uconnector.com/online/object/4udrawing/{itemno}.pdf"
        classname_description=f"Terminal Block 4Ucon ItemNo. {itemno}"
        footprint_name=f"TerminalBlock_4Ucon_1x{pins:02}_P{rm:3.2f}mm_Horizontal"

        kicad_mod = makeTerminalBlockStd(
            footprint_name=footprint_name,
            pins=pins,
            rm=rm,
            package_height=package_height,
            leftbottom_offset=leftbottom_offset,
            ddrill=ddrill,
            pad=pad,
            screw_diameter=screw_diameter,
            bevel_height=bevel_height,
            slit_screw=slit_screw,
            screw_pin_offset=screw_pin_offset,
            secondHoleDiameter=secondHoleDiameter,
            secondHoleOffset=secondHoleOffset,
            thirdHoleDiameter=thirdHoleDiameter,
            thirdHoleOffset=thirdHoleOffset,
            fourthHoleDiameter=fourthHoleDiameter,
            fourthHoleOffset=fourthHoleOffset,
            nibbleSize=nibbleSize,
            nibblePos=nibblePos,
            fabref_offset=fabref_offset,
            tags_additional=[],
            lib_name=None,
            classname=self.classname,
            classname_description=classname_description,
            webpage=webpage,
            script_generated_note=self.script_generated_note,
        )

        self.add_standard_3d_model_to_footprint(kicad_mod, self.classname, footprint_name)
        self.write_footprint(kicad_mod, self.classname)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generate a 4Ucon Terminal Block Footprint')

    args = FootprintGenerator.add_standard_arguments(parser)

    g = FourUcon_H8_3_TerminalBlock(args.output_dir, args.global_config)

    for pins in g.PINS:
        g.generateFootprint(pins)

    g = FourUCon_H7_TerminalBlock(args.output_dir, args.global_config)

    for pins in g.PINS:
        g.generateFootprint(pins)
