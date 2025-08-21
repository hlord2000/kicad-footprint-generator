#!/usr/bin/env python3

from KicadModTree import *  # NOQA
from scripts.tools.global_config_files import global_config as GC
# from scripts.tools.footprint_scripts_pin_headers import *  # NOQA
from def_makePinHeadStraight_old import makePinHeadStraight
from def_makePinHeadAngled_old import makePinHeadAngled
from def_makePinHeadStraightSMD_old import makePinHeadStraightSMD


if __name__ == "__main__":
    global_config = GC.DefaultGlobalConfig()
    class_name = "PinHeader"
    class_description = "pin header"

    # common settings
    # from http://katalog.we-online.de/em/datasheet/6130xx11121.pdf
    # and  http://katalog.we-online.de/em/datasheet/6130xx21121.pdf
    # and  http://katalog.we-online.de/em/datasheet/6130xx11021.pdf
    # and  http://katalog.we-online.de/em/datasheet/6130xx21021.pdf
    # and  https://cdn.harwin.com/pdfs/M20-877.pdf
    # and  https://cdn.harwin.com/pdfs/M20-876.pdf

    pin_pitch = 2.54
    pins_drill = 1
    pad = [1.7, 1.7]
    body_width_1row = 2.54
    body_overlength = 0
    # (right) angled:
    body_width_ra = 2.54
    body_offset_ra = 1.5
    pin_length_ra = 6
    pin_width = 0.64
    pad_offset = [1.655, 2.525]
    pin_length = [2.54, 3.6]
    pin_width = 0.64
    single_pad_smd = [2.51, 1.0]
    dual_pad_smd = [3.15, 1.0]

    lib_name = f"Connector_PinHeader_{pin_pitch:.2f}mm"

    for row_count in [1, 2]:
        for num_pos in range(1, 41):
            makePinHeadStraight(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, row_count * body_width_1row,
                body_overlength, pins_drill, pad, 
				[], lib_name, class_name, class_description,
            )
            makePinHeadAngled(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, body_width_ra, body_offset_ra, 
                pin_length_ra, pin_width, pins_drill, pad,
                [], lib_name, class_name, class_description,
            )
            if row_count == 2:
                makePinHeadStraightSMD(global_config,
                    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1], 
                    pin_length[row_count-1], pin_width, row_count * body_width_1row,
                    body_overlength, dual_pad_smd, True,
                    [], lib_name, class_name, class_description,
                )
            elif num_pos != 1:
                makePinHeadStraightSMD(global_config,
                    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
                    pin_length[row_count-1], pin_width,
                    row_count * body_width_1row,
                    body_overlength, single_pad_smd, True,
                    [], lib_name, class_name, class_description,
                )
                makePinHeadStraightSMD(global_config,
                    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
                    pin_length[row_count-1], pin_width,
                    row_count * body_width_1row,
                    body_overlength, single_pad_smd, False,
                    [], lib_name, class_name, class_description,
                )

    pin_pitch = 2.00
    pins_drill = 0.8
    pad = [1.35, 1.35]
    body_width_1row = 2.0
    body_overlength = 0
    # (right) angled:
    body_width_ra = 1.5
    body_offset_ra = 3 - 1.5
    pin_length_ra = 4.2
    pin_width = 0.5
    pad_offset = [1.175, 2.085]
    pin_length = [2.1, 2.875]
    pin_width = 0.5
    single_pad_smd = [2.35, 0.85]
    dual_pad_smd = [2.58, 1.0]

    lib_name = f"Connector_PinHeader_{pin_pitch:.2f}mm"

    for row_count in [1, 2]:
        for num_pos in range(1, 41):
            makePinHeadStraight(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, row_count * body_width_1row,
                body_overlength, pins_drill, pad, 
				[], lib_name, class_name, class_description,
            )
            makePinHeadAngled(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, body_width_ra, body_offset_ra,
                pin_length_ra, pin_width, pins_drill, pad,
                [], lib_name, class_name, class_description,
            )
            if row_count == 2:
                makePinHeadStraightSMD(global_config,
				    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
				    pin_length[row_count-1], pin_width, row_count * body_width_1row,
				    body_overlength, dual_pad_smd, True,
				    [], lib_name, class_name, class_description,
                )
            elif num_pos != 1:
                makePinHeadStraightSMD(global_config,
				    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
                    pin_length[row_count-1], pin_width, row_count * body_width_1row,
                    body_overlength, single_pad_smd, True,
                    [], lib_name, class_name, class_description,
                )
                makePinHeadStraightSMD(global_config,
				    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
                    pin_length[row_count-1], pin_width, row_count * body_width_1row,
                    body_overlength, single_pad_smd, False,
                    [], lib_name, class_name, class_description,
                )

    # From https://cdn.harwin.com/pdfs/M50-393.pdf
    # https://cdn.harwin.com/pdfs/M50-363.pdf
    # https://cdn.harwin.com/pdfs/M50-353.pdf
    # https://cdn.harwin.com/pdfs/M50-360.pdf
    # and http://www.mouser.com/ds/2/181/M50-360R-1064294.pdfs
    pin_pitch = 1.27
    pins_drill = 0.65
    pad = [1.0, 1.0]
    body_width = [2.1, 3.41]
    body_width_1row = 1.27
    body_overlength = 0
    # (right) angled:
    body_width_ra = 1.0
    body_offset_ra = 0.5
    pin_length_ra = 4.0
    pin_width = 0.4
    pad_offset = [1.5, 1.95]
    pin_length = [2.5, 2.75]
    pin_width = 0.4
    single_pad_smd = [3.0, 0.65]
    dual_pad_smd = [2.4, 0.74]

    lib_name = f"Connector_PinHeader_{pin_pitch:.2f}mm"

    for row_count in [1, 2]:
        for num_pos in range(1, 41):
            makePinHeadStraight(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, body_width[row_count-1],
                body_overlength, pins_drill, pad, 
                [], lib_name, class_name, class_description,
            )
            makePinHeadAngled(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, body_width_ra, body_offset_ra,
                pin_length_ra, pin_width, pins_drill, pad,
                [], lib_name, class_name, class_description,
            )
            if row_count == 2:
                makePinHeadStraightSMD(global_config,
				    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
				    pin_length[row_count-1], pin_width, body_width[row_count-1],
                    body_overlength, dual_pad_smd, True,
				    [], lib_name, class_name, class_description,
                )
            elif num_pos != 1:
                makePinHeadStraightSMD(global_config,
				    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
                    pin_length[row_count-1], pin_width, body_width[row_count-1],
				    body_overlength, single_pad_smd, True,
                    [], lib_name, class_name, class_description,
                )
                makePinHeadStraightSMD(global_config,
				    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
                    pin_length[row_count-1], pin_width, body_width[row_count-1],
				    body_overlength, single_pad_smd, False,
                    [], lib_name, class_name, class_description,
                )

    # single row THT Straight headers https://gct.co/pdfjs/web/viewer.html?file=/Files/Drawings/BC020.pdf&t=1502019369628
    # dual row THT Straight headers https://gct.co/files/drawings/bc035.pdf
    # single row THT Angled headers https://gct.co/pdfjs/web/viewer.html?file=/Files/Drawings/BC030.pdf&t=1502031327147
    # dual row THT Angled headers https://gct.co/files/drawings/bc045.pdf
    # single row SMD Straight headers http://www.farnell.com/datasheets/1912818.pdf?_ga=2.101918145.1303212991.1501602361-984110936.1498471838
    # dual row SMD Straight headers https://gct.co/files/drawings/bc050.pdf
    pin_pitch = 1.0
    pins_drill = 0.5
    pad = [0.85, 0.85]
    body_width = [1.27, 2.3]
    body_width_1row = 1.00
    body_overlength = 0
    # (right) angled:
    body_width_ra = [1.0, 1.2]
    body_offset_ra = [0.25, 0.9]
    pin_length_ra = 2.0
    pad_offset = [0.875, 1.65]
    pin_length = [1.25, 2.4]
    pin_width = 0.3
    single_pad_smd = [1.75, 0.6]
    dual_pad_smd = [2.0, 0.5]

    lib_name = f"Connector_PinHeader_{pin_pitch:.2f}mm"

    for row_count in [1, 2]:
        for num_pos in range(1, 41):
            makePinHeadStraight(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, body_width[row_count-1],
                body_overlength, pins_drill, pad,
                [], lib_name, class_name, class_description,
            )
            makePinHeadAngled(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, body_width_ra[row_count-1], body_offset_ra[row_count-1], 
                pin_length_ra, pin_width, pins_drill, pad,
                [], lib_name, class_name, class_description,
            )
            if row_count == 2:
                makePinHeadStraightSMD(global_config,
                    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
                    pin_length[row_count-1], pin_width, body_width[row_count-1],
                    body_overlength, dual_pad_smd, True,
					[], lib_name, class_name, class_description,
                )
            elif num_pos != 1:
                makePinHeadStraightSMD(global_config,
                    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
                    pin_length[row_count-1], pin_width, body_width[row_count-1],
                    body_overlength, single_pad_smd, True,
                    [], lib_name, class_name, class_description,
                )
                makePinHeadStraightSMD(global_config,
                    num_pos, row_count, pin_pitch, pin_pitch, pad_offset[row_count-1],
                    pin_length[row_count-1], pin_width, body_width[row_count-1],
                    body_overlength, single_pad_smd, False,
                    [], lib_name, class_name, class_description,
                )

    # Samtec HPM series:
    #   datasheet: https://suddendocs.samtec.com/catalog_english/hpm.pdf
    #   recommended footprint: https://suddendocs.samtec.com/prints/hpm-xx-xx-xx-x-xx-x-footprint.pdf
    #   detailed drawing: https://suddendocs.samtec.com/prints/hpm-xx-xx-xx-x-xx-x-mkt.pdf
    pin_pitch = 5.08
    pins_drill = 1.75
    pad = [2.8, 2.8]
    body_width_1row = 6.35
    body_overlength = 0
    # (right) angled:
    body_width_ra = [6.35]
    body_offset_ra = [1.5]
    pin_length_ra = 8.08  # 8.08 for -02 lead style, 13.82 for -04 lead style
    pad_offset = [0]  # Not used for TH
    pin_length = [0]  # Not used for TH
    pin_width = 1.14
    single_pad_smd = [0, 0]  # Not used for TH
    dual_pad_smd = [0, 0]  # Not used for TH

    lib_name = f"Connector_Samtec_HPM_THT"

    for row_count in [1, 1]:
        for num_pos in range(1, 20):
            class_name = "Samtec_HPM"

            # For some reason, these parts have a very old format, but the 3D model exist, so this is hard to change now
            format_01 = "{class_name}-{pos_count:02}-01-x-S_Straight_{row_count}x{pos_count:02}_Pitch{pitch:03.2f}mm"
            format_05 = "{class_name}-{pos_count:02}-05-x-S_Straight_{row_count}x{pos_count:02}_Pitch{pitch:03.2f}mm"

            makePinHeadStraight(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, row_count * body_width_1row,
                body_overlength, pins_drill, pad, 
                [], lib_name, class_name, "Samtec HPM power header series 11.94mm post length",
                name_format=format_01,
            )
            makePinHeadStraight(global_config,
                num_pos, row_count, pin_pitch, pin_pitch, row_count * body_width_1row,
                body_overlength, pins_drill, pad, 
                [], lib_name, class_name, "Samtec HPM power header series 3.81mm post length",
                name_format=format_05,
            )
