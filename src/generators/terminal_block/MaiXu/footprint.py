#!/usr/bin/env python

import argparse

from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.footprint_scripts_terminal_blocks import makeTerminalBlockStd

class MaiXu_MX126_Generator(FootprintGenerator):
    # Generic properties
    fplib_name = "TerminalBlock" # Name of the footprint library
    # Series datasheet: https://www.cnmaixu.com/Sites/maixu/static/upload/file/20240108/1704697250343193.pdf
    datasheet = "https://www.lcsc.com/datasheet/lcsc_datasheet_2309150913_MAX-MX126-5-0-03P-GN01-Cu-S-A_C5188435.pdf"
    script_generated_note = f"script-generated using https://gitlab.com/kicad/libraries/kicad-footprint-generator/-/tree/master/scripts/TerminalBlock_MaiXu";

    available_pincounts = range(2, 24+1)
    rm = 5.0 # Distance beteen any
    package_height = 7.8 # Y size of footprint, not height above PCB!
    leftbottom_offset=[
        3,
        package_height-4,
        2.5, # This makes the size asymmetric: 0.5mm less wide on the right
    ]
    ddrill=1.3
    pad=[2.8,2.8] # Guess, Based on MetzConnect Type011
    screw_diameter=3.2 # Guess, Based on MetzConnect Type011
    bevel_height=[2,package_height-4.5,package_height-3.5] # Guess, Based on MetzConnect Type011
    slit_screw = True # Draw "slit" in F.Fab rendering
    screw_pin_offset=[0,0] # ?
    secondHoleDiameter=0 # ?
    secondHoleOffset=[0,0] # ?
    thirdHoleDiameter=0 # ?
    thirdHoleOffset=[0,-4] # ?
    fourthHoleDiameter=0 # ?
    fourthHoleOffset=[0,0] # ?
    fabref_offset=[0,2.75]  # ?
    nibbleSize = None # ?
    nibblePos = None # ?

    def part_mpn(self, pincount):
        return f"MX126-{self.rm:.1f}-{pincount:02}P"

    def footprint_name(self, pincount: int):
        name = self.part_mpn(pincount)
        return f"TerminalBlock_MaiXu_{name}_1x{pincount:02}_P{self.rm:3.2f}mm"

    def classname_description(self, pincount: int):
        name = self.part_mpn(pincount)
        return f"terminal block MaiXu {name}"

    def generateFootprint(self, pincount: int):
        """Generate all footprints"""

        footprint_name = self.footprint_name(pincount)
        classname = self.fplib_name

        kicad_mod = makeTerminalBlockStd(
            footprint_name=footprint_name,
            pins=pincount,
            rm=self.rm,
            package_height=self.package_height,
            leftbottom_offset=self.leftbottom_offset,
            ddrill=self.ddrill,
            pad=self.pad,
            screw_diameter=self.screw_diameter,
            bevel_height=self.bevel_height,
            slit_screw=self.slit_screw,
            screw_pin_offset=self.screw_pin_offset,
            secondHoleDiameter=self.secondHoleDiameter,
            secondHoleOffset=self.secondHoleOffset,
            thirdHoleDiameter=self.thirdHoleDiameter,
            thirdHoleOffset=self.thirdHoleOffset,
            fourthHoleDiameter=self.fourthHoleDiameter,
            fourthHoleOffset=self.fourthHoleOffset,
            nibbleSize=self.nibbleSize,
            nibblePos=self.nibblePos,
            fabref_offset=self.fabref_offset,
            tags_additional=[],
            lib_name=None,
            classname=classname,
            classname_description=self.classname_description(pincount),
            webpage=self.datasheet,
            script_generated_note=self.script_generated_note
        )

        self.add_standard_3d_model_to_footprint(kicad_mod, classname, footprint_name)
        self.write_footprint(kicad_mod, classname)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generate a 4Ucon Terminal Block Footprint')

    args = FootprintGenerator.add_standard_arguments(parser)

    g = MaiXu_MX126_Generator(args.output_dir, args.global_config)

    for pins in g.available_pincounts:
        g.generateFootprint(pins)
