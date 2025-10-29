#!/usr/bin/env python

import argparse
from pathlib import Path

from KicadModTree import *  # NOQA
from scripts.tools.footprint_scripts_DIP import makeDIP


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Use .yaml files to create DIP footprints.')
    parser.add_argument('-o', '--output-dir', type=Path,
                        help='Sets the directory to which to write the generated footprints')
    args = parser.parse_args()

    output_dir = args.output_dir

    # common settings
    overlen_top=1.27
    overlen_bottom=1.27
    rm=2.54
    ddrill=0.8
    pad=[1.6,1.6]
    pad_large=[2.4,1.6]
    pad_smdsocket=[3.1,1.6]
    pad_smdsocket_small=[1.6,1.6]

    # narrow 7.62 DIPs
    pins=[4,6,8,10,12,14,16,18,20,22,24,28]
    pinrow_distance=7.62
    package_width=6.35
    socket_width=pinrow_distance+2.54
    for p in pins:
        makeDIP(p,rm,pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad,False,0,0,0, outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, 0,0,0, [], ["LongPads"], outdir=output_dir)
        socket_height = (p / 2 - 1) * rm + 2.54
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad, False, socket_width,socket_height,0, ["Socket"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, socket_width,socket_height,0,  ["Socket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket, True, socket_width,socket_height,1.27, ["SMDSocket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket_small, True,socket_width, socket_height, 0, ["SMDSocket"], ["SmallPads"], outdir=output_dir)

    # narrow 7.62 DIPs
    pins=[4,6,8,10,12,14,16,]
    pinrow_distance=10.16
    package_width=6.35
    socket_width=pinrow_distance+2.54
    for p in pins:
        makeDIP(p,rm,pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad,False,0,0,0, outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, 0,0,0, [], ["LongPads"], outdir=output_dir)

    # mid 10.16 DIPs
    pins=[22,24]
    pinrow_distance=10.16
    package_width=9.14
    socket_width=pinrow_distance+2.54
    for p in pins:
        makeDIP(p,rm,pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad,False,0,0,0, outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, 0,0,0, [], ["LongPads"], outdir=output_dir)
        socket_height = (p / 2 - 1) * rm + 2.54
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad, False, socket_width,socket_height,0, ["Socket"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, socket_width,socket_height,0,  ["Socket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket, True,
            socket_width, socket_height, 1.27, ["SMDSocket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket_small, True,
            socket_width, socket_height, 0, ["SMDSocket"], ["SmallPads"], outdir=output_dir)

    # mid 15.24 DIPs
    pins=[24,26,28,32,40,42,48,64]
    pinrow_distance=15.24
    package_width=14.73
    socket_width=pinrow_distance+2.54
    for p in pins:
        makeDIP(p,rm,pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad,False,0,0,0, outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, 0,0,0, [], ["LongPads"], outdir=output_dir)
        socket_height = (p / 2 - 1) * rm + 2.54
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad, False, socket_width,socket_height,0, ["Socket"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, socket_width,socket_height,0,  ["Socket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket, True,
            socket_width, socket_height, 1.27, ["SMDSocket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket_small, True,
            socket_width, socket_height, 0, ["SMDSocket"], ["SmallPads"], outdir=output_dir)

    # large 22.86 DIPs
    pins=[64]
    pinrow_distance=22.86
    package_width=22.35
    socket_width=pinrow_distance+2.54
    for p in pins:
        makeDIP(p,rm,pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad,False,0,0,0, outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, 0,0,0, [], ["LongPads"], outdir=output_dir)
        socket_height = (p / 2 - 1) * rm + 2.54
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad, False, socket_width,socket_height,0, ["Socket"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, socket_width,socket_height,0,  ["Socket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket, True,
            socket_width, socket_height, 1.27, ["SMDSocket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket_small, True,
            socket_width, socket_height, 0, ["SMDSocket"], ["SmallPads"], outdir=output_dir)

    # large 25.4 DIPs
    pins=[40,64]
    pinrow_distance=25.4
    package_width=24.89
    socket_width=pinrow_distance+2.54
    for p in pins:
        makeDIP(p,rm,pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad,False,0,0,0, outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, 0,0,0, [], ["LongPads"], outdir=output_dir)
        socket_height = (p / 2 - 1) * rm + 2.54
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad, False, socket_width,socket_height,0, ["Socket"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, socket_width,socket_height,0,  ["Socket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket, True,
            socket_width, socket_height, 1.27, ["SMDSocket"], ["LongPads"], outdir=output_dir)
        makeDIP(p, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_smdsocket_small, True,
            socket_width, socket_height, 0, ["SMDSocket"], ["SmallPads"], outdir=output_dir)

    # special SMD footprints
    smd_pins=[4,6,8,10,12,14,16,18,20,22,24,32]
    pad_smd = [2, 1.78]
    smd_pinrow_distances=[7.62, 9.53, 11.48]
    package_width=6.35
    for p in smd_pins:
        for prd in smd_pinrow_distances:
            makeDIP(p, rm, prd, package_width, overlen_top, overlen_bottom, ddrill, pad_smd, True,  0,0,0, [], [], "Package_DIP", [0, 0, 0], [1, 1, 1], [0, 0, 0], 'SMDIP', 'surface-mounted (SMD) DIP', 'SMD DIP DIL PDIP SMDIP', outdir=output_dir)
    smd_pins=[4,6,8,10,12,14,16,18,20,22]
    pad_smd = [1.5, 1.78]
    smd_pinrow_distances=[9.53]
    package_width=6.35
    for p in smd_pins:
        for prd in smd_pinrow_distances:
            makeDIP(p, rm, prd, package_width, overlen_top, overlen_bottom, ddrill, pad_smd, True,  0,0,0, ['Clearance8mm'], [], "Package_DIP", [0, 0, 0], [1, 1, 1], [0, 0, 0], 'SMDIP', 'surface-mounted (SMD) DIP', 'SMD DIP DIL PDIP SMDIP', outdir=output_dir)

    smd_pins=[24,28,32,40,42,48,64]
    pad_smd = [2, 1.78]
    smd_pinrow_distances=[15.24]
    package_width=14.73
    for p in smd_pins:
        for prd in smd_pinrow_distances:
            makeDIP(p, rm, prd, package_width, overlen_top, overlen_bottom, ddrill, pad_smd, True,  0,0,0, [], [],"Package_DIP", [0, 0, 0], [1, 1, 1], [0, 0, 0], 'SMDIP', 'surface-mounted (SMD) DIP', 'SMD DIP DIL PDIP SMDIP', outdir=output_dir)
    smd_pins=[40]
    pad_smd = [2, 1.78]
    smd_pinrow_distances=[25.24]
    package_width=24.89
    for p in smd_pins:
        for prd in smd_pinrow_distances:
            makeDIP(p, rm, prd, package_width, overlen_top, overlen_bottom, ddrill, pad_smd, True,  0,0,0, [], [], "Package_DIP", [0, 0, 0], [1, 1, 1], [0, 0, 0], 'SMDIP', 'surface-mounted (SMD) DIP', 'SMD DIP DIL PDIP SMDIP', outdir=output_dir)

    # Special DIP
    #
    # http://www.experimentalistsanonymous.com/diy/Datasheets/MN3005.pdf
    #
    # common settings
    overlen_top=1.27
    overlen_bottom=1.27
    rm=2.54
    ddrill=0.8
    pad=[1.6,1.6]
    pad_large=[2.4,1.6]
    pad_smdsocket=[3.1,1.6]
    pad_smdsocket_small=[1.6,1.6]

    # narrow 7.62 DIPs
    pins=[8]
    sizes_for_pins=20
    pinrow_distance=7.62
    package_width=6.35
    socket_width=pinrow_distance+2.54
    makeDIP(16, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad,       False, 0, 0, 0, prefix_name = '8', skip_pin = [3, 4, 5, 6, 11, 12, 13, 14], skip_count = True, right_cnt_start = 5, outdir=output_dir)
    socket_height = (sizes_for_pins / 2 - 1) * rm + 2.54
    makeDIP(16, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad,       False, socket_width, socket_height,0, ["Socket"],            prefix_name = '8', skip_pin = [3, 4, 5, 6, 11, 12, 13, 14], skip_count = True, right_cnt_start = 5, outdir=output_dir)
    makeDIP(16, rm, pinrow_distance, package_width, overlen_top, overlen_bottom, ddrill, pad_large, False, socket_width, socket_height,0, ["Socket"], ["LongPads"], prefix_name = '8', skip_pin = [3, 4, 5, 6, 11, 12, 13, 14], skip_count = True, right_cnt_start = 5, outdir=output_dir)
