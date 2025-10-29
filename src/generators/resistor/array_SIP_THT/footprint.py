#!/usr/bin/env python3

from KicadModTree import *  # NOQA
from scripts.tools.drawing_tools import *
from scripts.tools.footprint_scripts_sip import *


if __name__ == '__main__':
    for R in range(3, 14):
        pins=R+1
        makeResistorSIP(pins, "R_Array_SIP%d" % (pins), "{0}-pin Resistor SIP pack".format(pins, R))
    #for R in range(3,6):
    #    pins=2*R
    #    makeResistorSIP(pins, "Resistor_ArrayParallel_SIP%d" % (R), "{0}-pin Resistor SIP pack, {1} parallel resistors".format(pins, R))
    #for R in range(3,6):
    #    pins=R+2
    #    makeResistorSIP(pins, "Resistor_ArrayDivider_SIP%d" % (R), "{0}-pin Resistor SIP pack, {1} voltage dividers = {2} resistors".format(pins, R, 2*R))
