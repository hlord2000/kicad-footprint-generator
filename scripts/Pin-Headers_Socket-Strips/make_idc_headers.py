#!/usr/bin/env python3

from KicadModTree import *  # NOQA
from scripts.tools.global_config_files import global_config as GC
from scripts.tools.footprint_scripts_pin_headers import *  # NOQAA


if __name__ == "__main__":
    global_config = GC.DefaultGlobalConfig()
    class_name = "IDC-Header"
    class_description = "IDC header"
    lib_name = "Connector_IDC"

    # from http://multimedia.3m.com/mws/media/22448O/3m-four-wall-header-3000-series-100-x-100-ts-0772.pdf
    # and  http://www.selecom.it/pdf/06din416.pdf
    # and  https://www.reboul.fr/storage/00003af6.pdf
    # and  http://www.oupiin.com/product_iii.html?c1=10&c2=54
    # and  http://www.assmann-wsw.com/fileadmin/catalogue/04_Multiflex_rev4-0.pdf
    # and  https://docs.google.com/spreadsheets/d/16SsEcesNF15N3Lb4niX7dcUr-NY5_MFPQhobNuNppn4/edit#gid=0

    tags_additional = []
    extra_description = "https://docs.google.com/spreadsheets/d/16SsEcesNF15N3Lb4niX7dcUr-NY5_MFPQhobNuNppn4/edit#gid=0"

    pin_pitch = 2.54
    row_count = 2
    pins_drill = 1
    pad = [1.7, 1.7]

    orientation = "Vertical"
    latching = True
    body_width = 8.8
    body_overlength = 9.70
    body_offset = 0
    mating_overlen = 3.92
    wall_thickness = 1.2
    notch_width = 4.1
    latch_lengths = [0, 6.5, 9.5, 12] # roughly represent referenced parts with latch open
    latch_width = 4.4  # large enough to handle all referenced parts and measured empirically
    mhole_pad = [8, 8] # 3M 3000 datasheet: 5/16" (~8mm) screw head, existing FP is 5.46mm
    mhole_drill = 2.69
    mhole_overlength = 8.94  # existing KiCad footprint is 8.89
    mhole_offset = 1.02  # existing KiCad footprint is 1.02
    mhole_nr = global_config.get_pad_name(GC.PadName.MECHANICAL)

    for num_pos in [5, 6, 7, 8, 10, 12, 13, 15, 17, 20, 25, 30, 32]:
        for latch_len in latch_lengths:
            for mhole_drill, mhole_pad, mhole_overlength in zip([0, mhole_drill], [[0,0], mhole_pad], [0, mhole_overlength]):
            #for mhole_drill, mhole_pad, mhole_overlength in zip([0], [[0,0]], [0]):
                makeIdcHeader(global_config,
                    num_pos, row_count, pin_pitch, pin_pitch, body_width,
                    body_overlength, body_offset,
                    pins_drill, pad,
                    mating_overlen, wall_thickness, notch_width,
                    orientation, latching, latch_len, latch_width,
                    mhole_drill, mhole_pad, mhole_overlength, mhole_offset, mhole_nr,
                    tags_additional, extra_description, lib_name, class_name, class_description,
				)

    # the above datasheets cover both horizontal and vertical
    # latches are assumed to hang off the PCB so they aren't included here
    # for this footprint the body outline is hard-coded into the script
    orientation = "Horizontal"
    latching = True
    body_width = 1.24 + 15.53  # # existing KiCad footprint is 1.27+15.88
    body_overlength = 9.70
    body_offset = -1.24  # existing KiCad footprint is -1.27
    latch_len = 0
    mhole_drill = 2.69  # not sure why this needs to be here when it's above...
    mhole_pad = [8, 8]  # existing KiCad footprint is 3.05mm
    mhole_overlength = 5.905  # existing KiCad footprint is 5.84
    mhole_offset = 1.8  # existing KiCad footprint is 1.78

    for num_pos in [5, 6, 7, 8, 10, 12, 13, 15, 17, 20, 25, 30, 32]:
        for mhole_drill, mhole_pad, mhole_overlength in zip(
            [0, mhole_drill], [[0, 0], mhole_pad], [0, mhole_overlength]
        ):
            makeIdcHeader(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, body_width,
                body_overlength, body_offset,
                pins_drill, pad,
                mating_overlen, wall_thickness, notch_width,
                orientation, latching, latch_len, latch_width,
                mhole_drill, mhole_pad, mhole_overlength, mhole_offset, mhole_nr,
                tags_additional, extra_description, lib_name, class_name, class_description,
            )

    # from http://multimedia.3m.com/mws/media/330367O/3m-four-wall-header-2500-series-ts-0770.pdf
    # and  https://www.te.com/commerce/DocumentDelivery/DDEController?Action=srchrtrv&DocNm=1761681&DocType=Customer+Drawing&DocLang=English
    # and  https://cdn.amphenol-icc.com/media/wysiwyg/files/drawing/75869.pdf
    # and  https://katalog.we-online.de/em/datasheet/6120xx21621.pdf
    # and  https://docs.google.com/spreadsheets/d/16SsEcesNF15N3Lb4niX7dcUr-NY5_MFPQhobNuNppn4/edit#gid=0

    orientation = "Vertical"
    latching = False
    body_width = 8.9
    body_overlength = 3.83
    body_offset = 0
    mating_overlen = 3.91

    for num_pos in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17, 20, 22, 25, 30, 32]:
        makeIdcHeader(global_config,
            num_pos, row_count, pin_pitch, pin_pitch, body_width,
            body_overlength, body_offset,
            pins_drill, pad,
            mating_overlen, wall_thickness, notch_width,
            orientation, latching, 0, 0,
            0, [0,0], 0, 0, 0,
            tags_additional, extra_description, lib_name, class_name, "IDC box header",
        )

    # from http://multimedia.3m.com/mws/media/22504O/3mtm-100-in-loprof-hdr-100x-100strt-ra-4-wall-ts0818.pdf
    # and  https://b2b.harting.com/files/download/PRD/PDF_TS/09185XXX323_100154466DRW007A.pdf
    # and  http://suddendocs.samtec.com/prints/tst-1xx-xx-xx-x-xx-xx-mkt.pdf
    # and  https://katalog.we-online.de/em/datasheet/6120xx21721.pdf
    # and  https://cdn.amphenol-icc.com/media/wysiwyg/files/drawing/75867.pdf
    # and  https://docs.google.com/spreadsheets/d/16SsEcesNF15N3Lb4niX7dcUr-NY5_MFPQhobNuNppn4/edit#gid=0

    body_offset = 4.38 # distance from pin 1 row to the closest edge of the plastic body
    orientation = "Horizontal"
    body_overlength = 3.83

    for num_pos in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17, 20, 22, 25, 30, 32]:
        makeIdcHeader(global_config,
            num_pos, row_count, pin_pitch, pin_pitch, body_width,
            body_overlength, body_offset,
            pins_drill, pad,
            mating_overlen, wall_thickness, notch_width,
            orientation, latching, 0, 0,
            0, [0,0], 0, 0, 0,
            tags_additional, extra_description, lib_name, class_name, "IDC box header",
        )

    # from https://www.tme.eu/Document/4baa0e952ce73e37bc68cf730b541507/T821M114A1S100CEU-B.pdf

    pin_pitch = 2.54
    row_count = 2
    pins_drill = 0
    pad = [5.0, 1.02]

    orientation = "Vertical"
    latching = False
    body_width = 8.95
    body_overlength = 3.81
    body_offset = 0
    mating_overlen = 2.72
    wall_thickness = 1.2
    latch_lengths = []
    latch_width = 0
    mhole_drill = 0
    mhole_pad = []
    mhole_overlength = 0
    mhole_offset = 0
    mhole_nr = ""
    extra_description = "https://www.tme.eu/Document/4baa0e952ce73e37bc68cf730b541507/T821M114A1S100CEU-B.pdf"

    for num_pos in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 20, 22, 25, 30]:
        makeIdcHeader(global_config,
            num_pos, row_count, pin_pitch, 7.60, body_width,
            body_overlength, body_offset,
            pins_drill, pad,
            mating_overlen, wall_thickness, notch_width,
            orientation, latching, 0, 0,
            0, [0,0], 0, 0, 0,
            tags_additional, extra_description, lib_name, class_name, "IDC box header",
        )
