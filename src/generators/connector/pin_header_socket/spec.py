# generators is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# generators is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# generators. If not, see < http://www.gnu.org/licenses/ >.
#
# (C) The KiCad Librarian Team

from typing import Any
from dataclasses import dataclass, fields, asdict
import enum
from math import sqrt, isclose

from KicadModTree import (
    Footprint,
    FootprintType,
    Line,
    Model,
    Pad,
    PadArray,
    PolygonLine,
    Property,
    Rectangle,
    Rectangle,
    Text,
    Translation,
)
from kilibs.geom import Vec2DCompatible, Vector2D
import generators.tools.footprint.misc_tools as MT
from kilibs.config import global_config as GC
from generators.tools.footprint.drawing_tools import roundCrt
from kilibs.config import global_config as GC
from generators.tools.spec.base_spec import BaseSpec
from generators.tools.spec.spec_registry import register_spec
from generators.tools.footprint.save_footprint import write_footprint
from pathlib import Path

txt_offset = 1

class Orientation(enum.Enum):
    VERTICAL = "Vertical"
    HORIZONTAL = "Horizontal"

class MountType(enum.Enum):
    THT = "THT"
    SMD = "SMD"
    Edge = "Edge"

class ClassName(enum.Enum):
    PH = "PinHeader"
    PS = "PinSocket"
    IDC = "IDC-Header"

@register_spec
@dataclass
class FPconfiguration(BaseSpec):

    type: str = ""
    lib_format: str = ""
    class_name: str = "" # checked against class ClassName(enum.Enum)
    class_descr: str = ""
    footpr_format: str = ""
    descr_format: str = ""
    tags_base: str = ""
    orientation: str = "" # checked against class Orientation(enum.Enum)
    mount_type: str = "" # checked against class MountType(enum.Enum)
    mount_text: str = ""
    footpr_type: FootprintType = FootprintType.THT # filled by init
    datasheet: str | None = None
    # should be filled by builder function:
    lib_name: str = ""
    footpr_name: str = ""

    pin_pitch: float = 0.0
    row_range: range = range(0, 0) # yaml optional input for generator
    row_count: int = 0
    row_pitch: float | None = None
    pos_range: range = range(0, 0) # yaml input for generator
    pos_count: int = 0  # filled by generator.
    pin_count: int | None = None  # filled by init: row_count * pos_count
    pin1_left: bool = True

    body_width: float = 0.0 # X plane
    body_height: float = 0.0 # Z plane usually
    body_overlength: float = 0.0 # Y plane: extra lenght from top/bottom pins -/+ pin_pitch/2.
    body_offset: float = 0.0
    body_wall_thick: float = 0.0 # IDC only?
    body_notch_width: float = 0.0 # IDC only? length?

    pins_length: float = 0.0 # The Vertical or horizontal pin part of pinheader
    pins_width: float = 0.0
    #pins_thick: float = 0.0 # for flat pins on the underside of sockets
    pins_drill: float = 0.0
    pins_offset: float = 0.0
    pins_smd_length: float = 0.0 # The curved smd part of the pinheader/pinsocket.

    pads_width: float = 0.0
    pads_length: float = 0.0
    pads_offset: float = 0.0
    #pads_lp_width: float = 0.0

    # IDC specific: mounting pad/hole, latches
    mhole_drill: float = 0.0
    mhole_length: float = 0.0
    mhole_width: float = 0.0
    mhole_overlength: float = 0.0
    mhole_offset: float = 0.0
    latch_enable: bool = False
    # latch length & width should be switched after refactor since overlength and other params are referring to Y plane
    latch_length: float = 0.0
    latch_length_range = None # builder function should fill latch_length
    latch_width: float = 0.0
    mating_overlen: float = 0.0

    # these text fields have different value depending on destination. See updateTexts()
    row_text: str = ""
    pin1_text: str = ""
    mhole_text: str = ""
    latch_text: str = ""

    def isSubLevelAndParsed(self, key, value):
        if not isinstance(value, dict):
            return False

        for sub_key, sub_value in value.items():
            if sub_key == "range" or sub_key == "list":
                if hasattr(self, f'{key}_range'):
                    match sub_key:
                        case "range": setattr(self, f'{key}_range', range(value["range"][0], value["range"][1] + 1))
                        case "list":  setattr(self, f'{key}_range', list(value["list"]))
                elif hasattr(self, key):
                    match sub_key:
                        case "range": setattr(self, key, range(value["range"][0], value["range"][1] + 1))
                        case "list":  setattr(self, key, list(value["list"]))
                else:
                    raise ValueError(f'Property {key}.{sub_key} could not be mapped to FPconfiguration ({key} or {key}_range): {sub_key}')

            elif self.isSubLevelAndParsed(f'{key}_{sub_key}', sub_value): #dict in a dict?
                pass
            elif  not hasattr(self, f'{key}_{sub_key}'):
                raise ValueError(f'Property {key}.{sub_key} could not be mapped to FPconfiguration: {value}')
            else:
                setattr(self, f'{key}_{sub_key}', sub_value)
        return True


    def __init__(
        self,
        id: str = "",
        spec: dict[str, Any] = {},
        file_name: str = "",
    ) -> None:
        """Create an instance of `BaseSpec`.

        Args:
            id: The name/identifier of the spec. Typically, this is the name of the key
                of the spec (in the YAML file) or the name of the component.
            spec: The dictionary containing the specification of the component.
            file_name: The name of the YAML file that holds this spec definition.
        """
        super().__init__(id, spec, file_name)
        if Path(file_name).stem.startswith("pin_headers"):
            self.type = "pin_headers"
        elif Path(file_name).stem.startswith("idc_headers"):
            self.type = "idc_headers"
        else:
            self.type = "pin_sockets"

        for key, value in spec.items():
            if key == "class_name":
                if value not in [member.value for member in ClassName]:
                    raise ValueError(f"Invalid class_name: {spec['class_name']}")
                else:
                    self.class_name = value
            elif key == "orientation":
                if value not in [member.value for member in Orientation]:
                    raise ValueError(f"Invalid orientation: {spec['orientation']}")
                else:
                    self.orientation = value
            elif key == "mount_type":
                match value:
                    case "THT":
                        self.footpr_type = FootprintType.THT
                    case "SMD" | "Edge":
                        self.footpr_type = FootprintType.SMD
                    case _:
                        raise ValueError(f"Invalid mount type: {spec['mount']}")
                self.mount_type = value
            elif self.isSubLevelAndParsed(key, value):
                pass
            elif  not hasattr(self, key):
                raise ValueError(f'Property {key} could not be mapped to FPconfiguration: {value}')
            else:
                setattr(self, key, value)
        # end of parameter parsing

        # setting defaults for optional parameters:
        if self.row_pitch == None:
            self.row_pitch = self.pin_pitch
        if self.pin_count == None:
            self.pin_count = self.row_count * self.pos_count

        self.updateTexts("Description")


    def updateTexts(self, dest, include_prefixes=True):
        valid_dests = ["FootprintName", "Description", "Tags"]
        if dest not in valid_dests:
            raise ValueError(f"updateTexts: invalid destination: {dest} not in {valid_dests}")
        if include_prefixes:
            pre_fpr = '_'
            pre_dsc = ', '
            pre_tag = ' '
        else:
            pre_fpr = ''
            pre_dsc = ''
            pre_tag = ''

        match self.row_count:
            case 1: 
                if dest == "Description":   self.row_text = pre_dsc + "single row"
                elif dest == "Tags":        self.row_text = pre_tag + "single row"
            case 2:
                if dest == "Description":   self.row_text = pre_dsc + "double rows"
                elif dest == "Tags":        self.row_text = pre_tag + "double row"
            case 3:
                if dest == "Description":   self.row_text = pre_dsc + "triple rows"
                elif dest == "Tags":        self.row_text = pre_tag + "triple row"
            case 4:
                if dest == "Description":   self.row_text = pre_dsc + "quadruple rows"
                elif dest == "Tags":        self.row_text = pre_tag + "quadruple row"
            case _: 
                raise ValueError(f"Invalid row_count: {spec['row_count']}")

        if self.pin1_left:
            if dest == "FootprintName": self.pin1_text = pre_fpr + "Pin1Left"
            elif dest == "Description": self.pin1_text = pre_dsc + "style 1 (pin 1 left)"
            elif dest == "Tags":        self.pin1_text = pre_tag + "style1 pin1 left"
        else:
            if dest == "FootprintName": self.pin1_text = pre_fpr + "Pin1Right"
            elif dest == "Description": self.pin1_text = pre_dsc + "style 2 (pin 1 right)"
            elif dest == "Tags":        self.pin1_text = pre_tag + "style2 pin1 right"

        if self.mhole_drill > 0:
            if dest == "FootprintName": self.mhole_text = "-1MP"
            elif dest == "Description": self.mhole_text = pre_dsc + "mounting holes"
            elif dest == "Tags":        self.mhole_text = pre_tag + "MountHole"

        if self.latch_enable and isclose(self.latch_length, 0, rel_tol=1e-05):
            if dest == "FootprintName": self.latch_text = pre_fpr + "Latch"
            elif dest == "Description": self.latch_text = " " + "latches"
            elif dest == "Tags":        self.latch_text = pre_tag + "latching"
        elif self.latch_enable:
            if dest == "FootprintName": self.latch_text = f"{pre_fpr}Latch{self.latch_length:03.1f}mm"
            elif dest == "Description": self.latch_text = f"{pre_dsc}{self.latch_length:03.1f}mm latches"
            elif dest == "Tags":        self.latch_text = f"{pre_tag}latch{self.latch_length:03.1f}mm"
        else:
            self.latch_text = ""

    def formatString(self, s: str) -> str:
        return MT.formatString(self, s)
        # return s.format(**asdict(self))

    def getLibraryName(self) -> str:
        return self.formatString(self.lib_format)
        # same as return self.lib_format.format(**asdict(self))

    def getFootprintName(self) -> str:
        self.updateTexts("FootprintName")
        return self.formatString(self.footpr_format)
        # same as return self.footpr_format.format(**asdict(self))

    def getDescription(self) -> str:
        self.updateTexts("Description")
        return self.formatString(self.descr_format)
        # same as return self.descr_format.format(**asdict(self))

    def getBaseTags(self) -> str:
        self.updateTexts("Tags")
        return self.formatString(self.tags_base)
        # same as return self.tags_base.format(**asdict(self))



# THT Straight (Vertical) Pinheader:
#####################################
# <--------------> body_width
#    <--------> row_pitch
# +--------------+
# | OOO      OOO |     ^
# | OOO ==== OOO |  ^  pin_width
# | OOO      OOO |  |  v
# +--------------+  pin_pitch
# | OOO      OOO |  |
# | OOO ==== OOO |  v
# | OOO      OOO |
# +--------------+
#
def makePinHeadStraight(
    generator_name,
    global_config: GC.GlobalConfig,
    pos_count: int,
    row_count: int,
    pin_pitch: float,
    row_pitch: float,
    body_width: float,
    body_overlength: float,
    pins_drill: float,
    pad: Vec2DCompatible,
    tags_additional: list[str] = [],
    lib_name: str = "Pin_Headers",
    class_name: str = "PinHeader",
    class_description: str = "pin header",
    isSocket: bool = False,
    name_format: str | None = None,
):
    gc = global_config
    overlen_top = pin_pitch/2 + body_overlength
    overlen_bot = pin_pitch/2 + body_overlength

    pad = Vector2D(pad)

    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    # This is set a bit further out than normal, not quite clear why.
    # silk_pad_offset = gc.silk_pad_offset
    silk_pad_offset = gc.silk_pad_clearance + gc.silk_fab_offset

    silk_line_width = gc.silk_line_width

    h_fab = (pos_count - 1) * pin_pitch + overlen_top + overlen_bot
    w_fab = body_width
    l_fab = (row_pitch * (row_count - 1) - w_fab) / 2
    t_fab = -overlen_top

    h_slk = h_fab + 2 * gc.silk_fab_offset
    w_slk = max(
        w_fab + 2 * gc.silk_fab_offset,
        row_pitch * (row_count - 1) - pad.x - 4 * gc.silk_fab_offset,
    )
    l_slk = (row_pitch * (row_count - 1) - w_slk) / 2
    t_slk = -overlen_top - gc.silk_fab_offset

    w_crt = max(body_width, row_pitch * (row_count - 1) + pad.x) + 2 * crtyd_offset
    h_crt = max(h_fab, (pos_count - 1) * pin_pitch + pad.y) + 2 * crtyd_offset
    l_crt = row_pitch * (row_count - 1) / 2 - w_crt / 2
    t_crt = (pos_count - 1) * pin_pitch / 2 - h_crt / 2

    fab_text_props = gc.get_text_properties_for_layer("F.Fab")
    fabref_text_size, fabref_text_thickness = fab_text_props.clamp_size(w_fab * 0.6)
    # That causes diffs, use the old unrounded calc for now
    fabref_text_thickness = fabref_text_size.y * 0.15

    # Samtec HPM have a different name format for...reasons
    # This is the default
    if name_format is None:
        name_format = "{class_name}_{row_count}x{pos_count:02}_P{pitch:03.2f}mm_Vertical"

    footprint_name = name_format.format(class_name=class_name, row_count=row_count, pos_count=pos_count, pitch=pin_pitch)

    description = "Through hole straight {3}, {0}x{1:02}, {2:03.2f}mm pitch".format(row_count, pos_count, pin_pitch, class_description)
    tags = "Through hole {3} THT {0}x{1:02} {2:03.2f}mm".format(row_count, pos_count, pin_pitch, class_description)
    if (row_count == 1):
        description = description + ", single row"
        tags = tags + " single row"
    elif row_count == 2:
        description = description + ", double rows"
        tags = tags + " double row"
    elif row_count == 3:
        description = description + ", triple rows"
        tags = tags + " triple row"
    elif row_count == 4:
        description = description + ", quadruple rows"
        tags = tags + " quadruple row"

    if len(tags_additional) > 0:
        for t in tags_additional:
            footprint_name = footprint_name + "_" + t
            description = description + ", " + t
            tags = tags + " " + t

    # init kicad footprint
    kicad_mod = Footprint(footprint_name, FootprintType.THT)
    kicad_mod.description = description
    kicad_mod.tags = tags

    # anchor for SMD-symbols is in the center, for THT-sybols at pin1
    offset = Vector2D(0, 0)
    if isSocket and row_count > 1:
        offset.x = -row_pitch
    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    # set general values
    kicad_modg.append(
        Property(name=Property.REFERENCE, text='REF**', at=[row_pitch * (row_count - 1) / 2, t_slk - txt_offset], layer='F.SilkS'))
    kicad_modg.append(
        Text(text='${REFERENCE}', at=[pin_pitch/2*(row_count-1), t_crt + offset.x + (h_crt/2)], rotation=90, layer='F.Fab', size=fabref_text_size, thickness=fabref_text_thickness))
    kicad_modg.append(
        Property(name=Property.VALUE, text=footprint_name, at=[row_pitch * (row_count - 1) / 2, t_slk + h_slk + txt_offset], layer='F.Fab'))

    # create FAB-layer
    chamfer = w_fab/4
    kicad_modg.append(Line(start=[l_fab + chamfer, t_fab], end=[l_fab + w_fab, t_fab], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fab + w_fab, t_fab], end=[l_fab + w_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fab + w_fab, t_fab+h_fab], end=[l_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fab, t_fab+h_fab], end=[l_fab, t_fab+chamfer], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fab, t_fab+chamfer], end=[l_fab + chamfer, t_fab], layer='F.Fab', width=gc.fab_line_width))

    # create SILKSCREEN-layer + pin1 marker

    # Silkscreen body
    body_min_x_square = pad.x / 2 + silk_pad_offset
    body_min_y_square = pad.y / 2 + silk_pad_offset
    # drawin bottom line

    if (pos_count-1)*pin_pitch + body_min_y_square < t_slk + h_slk:
        kicad_modg.append(Line(start=[l_slk, t_slk + h_slk], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
    else:
        if pos_count == 1:
            kicad_modg.append(Line(start=[l_slk, body_min_y_square], end=[l_slk + w_slk, body_min_y_square], layer='F.SilkS', width=silk_line_width))
        else:
            body_min_x_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (overlen_bot + gc.silk_fab_offset) * (overlen_bot + gc.silk_fab_offset)))
            kicad_modg.append(Line(start=[l_slk, t_slk + h_slk], end=[-body_min_x_round, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
            kicad_modg.append(Line(start=[(row_count-1)*row_pitch+body_min_x_round, t_slk + h_slk], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
            for x in range(0, (row_count-1)):
                kicad_modg.append(Line(start=[x*row_pitch+body_min_x_round, t_slk + h_slk], end=[(x+1)*row_pitch-body_min_x_round, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
    # drawin sidelines
    # calculate top Y position
    if pin_pitch < body_min_y_square * 2:
        shoulder_y_pos = body_min_y_square
        shoulder_y_lines = 2
    else:
        shoulder_y_pos = pin_pitch / 2
        shoulder_y_lines = 1
    if row_pitch < body_min_x_square * 2:
        top_x_pos = body_min_x_square
        top_x_lines = 2
    else:
        top_x_pos = row_pitch / 2
        top_x_lines = 1
    if l_slk + w_slk  > body_min_x_square+(row_count-1)*row_pitch:
        kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[l_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
        if row_count == 1:
            kicad_modg.append(Line(start=[l_slk + w_slk, shoulder_y_pos], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
        else:
            kicad_modg.append(Line(start=[l_slk + w_slk, t_slk], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
    elif pos_count != 1:
        body_min_y_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - l_slk * l_slk))
        kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[l_slk, pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
        kicad_modg.append(Line(start=[l_slk, (pos_count-1)*pin_pitch+body_min_y_round], end=[l_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
        if row_count == 1:
            kicad_modg.append(Line(start=[l_slk + w_slk, shoulder_y_pos], end=[l_slk + w_slk, pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
        else:
            kicad_modg.append(Line(start=[l_slk + w_slk, body_min_y_square], end=[l_slk + w_slk, pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
        kicad_modg.append(Line(start=[l_slk + w_slk, (pos_count-1)*pin_pitch+body_min_y_round], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=silk_line_width))
        for x in range(1, (pos_count-1)):
            kicad_modg.append(Line(start=[l_slk, x*pin_pitch+body_min_y_round], end=[l_slk, (x+1)*pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
            kicad_modg.append(Line(start=[l_slk + w_slk, x*pin_pitch+body_min_y_round], end=[l_slk + w_slk, (x+1)*pin_pitch-body_min_y_round], layer='F.SilkS', width=silk_line_width))
    # drawin top

    if row_count == 1:
        if shoulder_y_lines == 1:
            kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[l_slk + w_slk, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
        elif shoulder_y_lines == 2:
            top_x_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (shoulder_y_pos-pin_pitch) * (shoulder_y_pos-pin_pitch)))
            kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[l_slk + w_slk/2-top_x_round, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
            kicad_modg.append(Line(start=[l_slk + w_slk/2 + top_x_round, shoulder_y_pos], end=[l_slk + w_slk, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
    else:
        if shoulder_y_lines == 1:
            kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[top_x_pos, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
        elif shoulder_y_lines == 2:
            top_x_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (shoulder_y_pos-pin_pitch) * (shoulder_y_pos-pin_pitch)))
            if top_x_pos > row_pitch-top_x_round:
                top_x_end = row_pitch-top_x_round
            else:
                top_x_end = top_x_pos
            kicad_modg.append(Line(start=[l_slk, shoulder_y_pos], end=[-top_x_round, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
            if top_x_round*2 + gc.silk_line_width*2 < pad.x:
                kicad_modg.append(Line(start=[top_x_round, shoulder_y_pos], end=[top_x_end, shoulder_y_pos], layer='F.SilkS', width=silk_line_width))
        if top_x_lines == 1:
            kicad_modg.append(Line(start=[top_x_pos, shoulder_y_pos], end=[top_x_pos, t_slk], layer='F.SilkS', width=silk_line_width))
        elif top_x_lines == 2:
            shoulder_y_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (row_pitch-top_x_pos) * (row_pitch-top_x_pos)))
            if shoulder_y_pos > pin_pitch-shoulder_y_round:
                shoulder_y_pos = pin_pitch-shoulder_y_round
            if shoulder_y_round*2 + silk_line_width*2 < pad.y:
                kicad_modg.append(Line(start=[top_x_pos, shoulder_y_pos], end=[top_x_pos, shoulder_y_round], layer='F.SilkS', width=silk_line_width))
                kicad_modg.append(Line(start=[top_x_pos, -shoulder_y_round], end=[top_x_pos, t_slk], layer='F.SilkS', width=silk_line_width))
        # highest horizontal line
        if abs(t_slk) > body_min_y_square:
            kicad_modg.append(Line(start=[top_x_pos, t_slk], end=[l_slk + w_slk, t_slk], layer='F.SilkS', width=silk_line_width))
        else:
            top_x_round = sqrt(((pad.x/2 + silk_pad_offset) * (pad.x/2 + silk_pad_offset) - (abs(t_slk)) * (abs(t_slk))))
            if top_x_pos > row_pitch-top_x_round + 2*silk_line_width:
                kicad_modg.append(Line(start=[top_x_pos, t_slk], end=[row_pitch-top_x_round, t_slk], layer='F.SilkS', width=silk_line_width))
            kicad_modg.append(Line(start=[row_pitch+top_x_round, t_slk], end=[l_slk + w_slk, t_slk], layer='F.SilkS', width=silk_line_width))

    """
    if row_count == 1:
        kicad_modg.append(
            Rectangle(start=[l_slk, 0.5 * pin_pitch], end=[l_slk + w_slk, t_slk + h_slk], layer='F.SilkS', width=gc.silk_line_width))
    else:
        if isSocket and row_count>1:
            kicad_modg.append(PolygonLine(
                shape=[[l_slk+w_slk, 0.5 * pin_pitch], [l_slk+w_slk, t_slk + h_slk], [l_slk , t_slk + h_slk], [l_slk , t_slk],
                          [l_slk+w_slk/2, t_slk], [l_slk+w_slk/2, 0.5 * pin_pitch], [l_slk+w_slk, 0.5 * pin_pitch]], layer='F.SilkS', width=lw_slk))
        else:
            kicad_modg.append(PolygonLine(
                shape=[[l_slk, 0.5 * pin_pitch], [l_slk, t_slk + h_slk], [l_slk + w_slk, t_slk + h_slk], [l_slk + w_slk, t_slk],
                          [0.5 * pin_pitch, t_slk], [0.5 * pin_pitch, 0.5 * pin_pitch], [l_slk, 0.5 * pin_pitch]], layer='F.SilkS', width=lw_slk))
    """
    # pin 1 marker
    pin1_min = -(pad.x / 2 + silk_pad_offset)
    if pin1_min < l_slk:
        pin1_x = pin1_min
    else:
        pin1_x = l_slk
    if pin1_min < t_slk:
        pin1_y = pin1_min
    else:
        pin1_y = t_slk
    if isSocket and row_count>1:
        kicad_modg.append(PolygonLine(shape=[[pin1_x + w_slk, 0], [pin1_x + w_slk, pin1_y], [pin1_x + w_slk - pin_pitch / 2, pin1_y]], layer='F.SilkS', width=silk_line_width))
    else:
        kicad_modg.append(PolygonLine(shape=[[pin1_x, 0], [pin1_x, pin1_y], [0, pin1_y]], layer='F.SilkS', width=silk_line_width))

    # create courtyard
    crt_rect = Rectangle(
        start=Vector2D(l_crt, t_crt),
        size=Vector2D(w_crt, h_crt),
    ).round_to_grid(outwards=True, grid=gc.courtyard_grid)

    kicad_modg.append(
        Rectangle(
            start=crt_rect.top_left,
            end=crt_rect.bottom_right,
            layer="F.CrtYd",
            width=gc.courtyard_line_width,
        )
    )

    # create pads
    x1 = 0
    y1 = 0

    pad_type = Pad.TYPE_THT
    pad_shape1 = Pad.SHAPE_RECT
    pad_shapeother = Pad.SHAPE_OVAL
    pad_layers = Pad.LAYERS_THT

    p = 1

    for r in range(1, pos_count + 1):  # type: ignore

        if isSocket and row_count > 1:
            x1 = row_pitch
        else:
            x1 = 0
        for c in range(1, row_count + 1):  # type: ignore
            if p == 1:
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[x1, y1], size=pad, drill=pins_drill,
                                      layers=pad_layers))
            else:
                kicad_modg.append(
                    Pad(number=p, type=pad_type, shape=pad_shapeother, at=[x1, y1], size=pad, drill=pins_drill,
                        layers=pad_layers))

            p = p + 1
            if isSocket and row_count > 1:
                x1 = x1 - row_pitch
            else:
                x1 = x1 + row_pitch

        y1 = y1 + pin_pitch

    # add model
    kicad_modg.append(
        Model(
            filename=gc.model_3d_prefix
            + lib_name
            + ".3dshapes/"
            + footprint_name
            + global_config.model_3d_suffix
        )
    )

    # write file
    write_footprint(kicad_mod, lib_name, generator_name)


def makeIdcHeader(
    generator_name,
    global_config: GC.GlobalConfig,
    pos_count: int,
    row_count: int,
    pin_pitch: float,
    row_pitch: float,
    body_width: float,
    body_overlength: float,
    body_offset: float,
    pins_drill: float,
    pad: Vec2DCompatible,
    mating_overlen: float,
    wall_thickness: float,
    notch_width: float,
    orientation: str,
    latching: float,
    latch_length: float,
    latch_width: float,
    mhole_drill: float,
    mhole_pad: Vec2DCompatible,
    mhole_overlength: float,
    mhole_offset: float,
    mhole_nr: str,
    tags_additional: list[str],
    extra_description: str,
    lib_name: str,
    classname: str,
    class_description: str,
):
    # If pins_drill is zero, then create a SMD footprint:
    gc = global_config
    overlen_top = pin_pitch/2 + body_overlength
    overlen_bot = pin_pitch/2 + body_overlength
    pad = Vector2D(pad)

    mhole_pad = Vector2D(mhole_pad)
    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    pin_size = 0.64  # square pin side length; this appears to be the same for all connectors so use a fixed internal value

    mh_present = True if mhole_drill > 0 and mhole_pad.x > 0 and mhole_pad.y > 0 and mhole_overlength > 0 else False
    mh_y = Vector2D(-mhole_overlength, (pos_count - 1) * pin_pitch + mhole_overlength)

    h_fab = (pos_count - 1) * pin_pitch + overlen_top + overlen_bot
    w_fab = body_width
    if pins_drill == 0:
        # Body should be centered for SMT footprints
        l_fab = -w_fab / 2 if body_offset == 0 else body_offset
        t_fab = -overlen_top - (pos_count - 1) * pin_pitch / 2
    else:
        l_fab = (row_pitch * (row_count - 1) - w_fab) / 2 if body_offset == 0 else body_offset
        t_fab = -overlen_top

    # these calculations are so tight that new body styles will probably break them
    h_crt = max(max(h_fab, (pos_count - 1) * pin_pitch + pad.y) + 2 * latch_length, (pos_count - 1) * pin_pitch + 2 * mhole_overlength + mhole_pad.y) + 2 * crtyd_offset
    w_crt = max(body_width, row_pitch * (row_count - 1) + pad.x) + 2 * crtyd_offset if body_offset <= 0 else pad.x / 2 + body_offset + body_width + 2 * crtyd_offset
    if pins_drill == 0:
        # Courtyard should be centered for SMT footprints
        l_crt =  -pad.x / 2 - row_pitch/2- crtyd_offset
        t_crt = min(t_fab - latch_length, -mhole_overlength - mhole_pad.y / 2) - crtyd_offset
    else:
        l_crt = l_fab - crtyd_offset if body_offset <= 0 else -pad.x / 2 - crtyd_offset
        t_crt = min(t_fab - latch_length, -mhole_overlength - mhole_pad.y / 2) - crtyd_offset
    # if orientation == 'Horizontal' and latching and mhole_drill > 0:
    if mh_present and (mhole_offset - mhole_pad.x / 2 < l_fab):
        # horizontal latching with mounting holes is a special case
        l_crt = mhole_offset - mhole_pad.x / 2 - crtyd_offset
        w_crt = -l_crt + body_width + body_offset + crtyd_offset

    if pins_drill == 0:
        # center is [0, 0] for SMD footprints
        center_fab = Vector2D(0, 0)
        center_fp = Vector2D(0, 0)
    else:
        # center of the body (horizontal: middle pin or the center of the middle pins for vertical)
        center_fab = Vector2D(row_pitch * (row_count - 1) / 2 if orientation == 'Vertical' else body_offset + body_width / 2, t_fab + h_fab / 2)
        center_fp = Vector2D(l_crt + w_crt / 2, center_fab.y)

    fab_text_props = gc.get_text_properties_for_layer("F.Fab")
    text_size, text_thickness = fab_text_props.clamp_size(w_fab * 0.6)

    footprint_name = "{3}_{0}x{1:02}{7}_P{2:03.2f}mm{4}{5}_{6}{8}".format(row_count, pos_count, pin_pitch, classname, "_Latch" if latching else "", "{0:03.1f}mm".format(latch_length) if latch_length > 0 else "", orientation, "-1MP" if mh_present else "", "_SMD"if pins_drill==0 else "")
    # footprint_name = footprint_name_base + "_MountHole" if mh_present else footprint_name_base

    if row_count == 1:
        description_rows = "single row"
        tags_rows = "single row"
    elif row_count == 2:
        description_rows = "double rows"
        tags_rows = "double row"
    elif row_count == 3:
        description_rows = "triple rows"
        tags_rows = "triple row"
    elif row_count == 4:
        description_rows = "quadruple rows"
        tags_rows = "quadruple row"
    else:
        raise ValueError("Unsupported number of rows: {0}".format(row_count))

    if pins_drill == 0:
        description = "SMD"
        tags = "SMD"
        mounting_type = ""
    else:
        description = "Through hole"
        tags = "Through hole"
        mounting_type = "THT"

    description = description + " {3}, {0}x{1:02}, {2:03.2f}mm pitch, DIN 41651 / IEC 60603-13, {4}{5}{6}{7}".format(row_count, pos_count, pin_pitch, class_description, description_rows, ", {0:03.1f}mm".format(latch_length) if latch_length > 0 else "", " latches" if latching else "", ", mounting holes" if mh_present else "", orientation.lower())
    tags = tags + " {5} {3} {6} {0}x{1:02} {2:03.2f}mm {4}".format(row_count, pos_count, pin_pitch, class_description, tags_rows, orientation.lower(), mounting_type)

    if len(tags_additional) > 0:
        for t in tags_additional:
            footprint_name = footprint_name + "_" + t
            description = description + ", " + t
            tags = tags + " " + t

    if extra_description:
        description = description + ", " + extra_description

    footprint_type = FootprintType.SMD if pins_drill == 0 else FootprintType.THT

    # init kicad footprint
    kicad_mod = Footprint(footprint_name, footprint_type)
    kicad_mod.description = description
    kicad_mod.tags = tags

    # instantiate footprint (SMD origin at center, THT at pin 1)
    offset = Vector2D(0, 0)
    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    # set general values
    kicad_modg.append(Property(name=Property.REFERENCE, text='REF**', at=[center_fp.x, t_crt - text_size.y / 2], layer='F.SilkS'))
    kicad_modg.append(Text(text='${REFERENCE}', at=[center_fab.x, center_fab.y], rotation=90, layer='F.Fab', size=text_size, thickness=text_thickness))
    kicad_modg.append(Property(name=Property.VALUE, text=footprint_name, at=[center_fp.x, t_crt + h_crt + text_size.y / 2], layer='F.Fab'))

    # for shrouded headers, fab and silk layers have very similar geometry
    # can use the same code to build lines on both layers with slight changes in values between layers
    # zip together lists with fab and then silk layer settings as the list elements so the same code can draw both layers
    for layer, line_width, lyr_offset, chamfer in zip(['F.Fab', 'F.SilkS'], [gc.fab_line_width, gc.silk_line_width], [0, gc.silk_fab_offset], [min(1, w_fab / 4), 0]):
        # body outline
        if orientation == "Horizontal" and latching:
            # body outline taken from existing KiCad footprint
            body_polygon = [
                (body_offset - lyr_offset, t_fab - lyr_offset), (l_fab + 6.98 + lyr_offset, t_fab - lyr_offset),
                (l_fab + w_fab + lyr_offset, t_fab + 3.17 - lyr_offset), (l_fab + w_fab + lyr_offset, t_fab + 6.99 + lyr_offset),
                (l_fab + 12.7 + lyr_offset, t_fab + 9.14 + lyr_offset), (l_fab + 12.7 + lyr_offset, t_fab + h_fab - 9.14 - lyr_offset),
                (l_fab + w_fab + lyr_offset, t_fab + h_fab - 6.99 - lyr_offset), (l_fab + w_fab + lyr_offset, t_fab + h_fab - 3.17 + lyr_offset),
                (l_fab + 6.98 + lyr_offset, t_fab + h_fab + lyr_offset), (body_offset - lyr_offset, t_fab + h_fab + lyr_offset)
            ]
            # body outline taken from simplified 3M 3000 model (also modify arguments: body_offset=-1.24 and body_width=1.24+15.53)
            # https://www.3m.com/3M/en_US/company-us/all-3m-products/~/3M-Four-Wall-Header-3000-Series/?N=5002385+3290316872&preselect=8709318+8710652+8733900+8734573&rt=rud
            body_polygon = [
                (body_offset - lyr_offset, t_fab - lyr_offset), (l_fab + 7.11 + lyr_offset, t_fab - lyr_offset),
                (l_fab + 16.77 + lyr_offset, t_fab + 3.47 - lyr_offset), (l_fab + 16.77 + lyr_offset, t_fab + 7.44 + lyr_offset),
                (l_fab + 13.21 + lyr_offset, t_fab + 8.07 + lyr_offset), (l_fab + 13.21 + lyr_offset, t_fab + h_fab - 8.07 - lyr_offset),
                (l_fab + 16.77 + lyr_offset, t_fab + h_fab - 7.44 - lyr_offset), (l_fab + 16.77 + lyr_offset, t_fab + h_fab - 3.47 + lyr_offset),
                (l_fab + 7.11 + lyr_offset, t_fab + h_fab + lyr_offset), (body_offset - lyr_offset, t_fab + h_fab + lyr_offset)
            ]
            kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
            # now draw the left side vertical line, which may be broken on the silk layer around mounting holes
            if layer == 'F.SilkS' and mh_present and mhole_pad.x/2 - mhole_offset > -body_offset + gc.silk_fab_offset * 1.5:
                body_polygon = [(body_offset - lyr_offset, t_fab - lyr_offset), (body_offset - lyr_offset, mh_y.x - mhole_pad.x/2)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                body_polygon = [(body_offset - lyr_offset, mh_y.x + mhole_pad.x/2), (body_offset - lyr_offset, mh_y.y - mhole_pad.x/2)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                body_polygon = [(body_offset - lyr_offset, mh_y.y + mhole_pad.x/2), (body_offset - lyr_offset, t_fab + h_fab + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
            else:
                body_polygon = [(body_offset - lyr_offset, t_fab + h_fab + lyr_offset), (body_offset - lyr_offset, t_fab - lyr_offset)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
        else:
            # body outline silk lines need to clear the mounting hole on vertical headers
            if mh_present and layer == 'F.SilkS':
                body_polygon = [(mhole_offset + mhole_pad.x/2 - lyr_offset, t_fab - lyr_offset), (l_fab + w_fab + lyr_offset, t_fab - lyr_offset),
                    (l_fab + w_fab + lyr_offset, t_fab + h_fab + lyr_offset), (mhole_offset + mhole_pad.x/2 - lyr_offset, t_fab + h_fab + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                body_polygon = [(mhole_offset - mhole_pad.x/2 + lyr_offset, t_fab - lyr_offset), (l_fab - lyr_offset, t_fab - lyr_offset),
                    (l_fab - lyr_offset, t_fab + h_fab + lyr_offset), (mhole_offset - mhole_pad.x/2 + lyr_offset, t_fab + h_fab + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
            else:
                if layer == "F.SilkS" and pins_drill == 0:
                    # Break silkscreen for SMD pads
                    body_polygon = [(l_fab - lyr_offset, -((pos_count-1)*pin_pitch/2)-pad.y/2-0.5), (l_fab - lyr_offset, t_fab - lyr_offset),
                        (l_fab + w_fab + lyr_offset, t_fab - lyr_offset), (l_fab +w_fab + lyr_offset, -((pos_count-1)*pin_pitch/2)-pad.y/2-0.5)]
                    kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                    body_polygon = [(l_fab - lyr_offset, ((pos_count-1)*pin_pitch/2)+pad.y/2+0.5), (l_fab - lyr_offset, t_fab + h_fab + lyr_offset),
                        (l_fab + w_fab + lyr_offset, t_fab +h_fab + lyr_offset), (l_fab +w_fab + lyr_offset, ((pos_count-1)*pin_pitch/2)+pad.y/2+0.5)]
                    kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
                else:
                    body_polygon = [(l_fab + chamfer - lyr_offset, t_fab - lyr_offset), (l_fab + w_fab + lyr_offset, t_fab - lyr_offset),
                        (l_fab + w_fab + lyr_offset, t_fab + h_fab + lyr_offset), (l_fab - lyr_offset, t_fab + h_fab + lyr_offset),
                        (l_fab - lyr_offset, t_fab + chamfer - lyr_offset)]
                    kicad_mod.append(PolygonLine(shape=body_polygon, layer=layer, width=line_width))
        if chamfer > 0 and not (orientation == 'Horizontal' and latching):
            kicad_modg.append(Line(start=[l_fab, t_fab + chamfer], end=[l_fab + chamfer, t_fab], layer=layer, width=line_width))

        # vertical mating connector outline (this is the same for both layers)
        if orientation == "Vertical":
            if pins_drill == 0:
                mating_conn_polygon = [(l_fab - lyr_offset, center_fab.y - notch_width/2), (l_fab + wall_thickness, center_fab.y - notch_width/2),
                    (l_fab + wall_thickness, t_fab+wall_thickness), (l_fab + w_fab - wall_thickness, t_fab+wall_thickness),
                    (l_fab + w_fab - wall_thickness, t_fab+h_fab-wall_thickness), (l_fab + wall_thickness, t_fab+h_fab-wall_thickness),
                    (l_fab + wall_thickness, center_fab.y + notch_width/2), (l_fab + wall_thickness, center_fab.y + notch_width/2),
                    (l_fab - lyr_offset, center_fab.y + notch_width/2)]
                if layer == "F.Fab":
                    # Only append mating connector outline in F.Fab for SMD footprints (silkscreen would be on top of pads)
                    kicad_mod.append(PolygonLine(shape=mating_conn_polygon, layer=layer, width=line_width))
            else:
                mating_conn_polygon = [(l_fab - lyr_offset, center_fab.y - notch_width/2), (l_fab + wall_thickness, center_fab.y - notch_width/2),
                    (l_fab + wall_thickness, -mating_overlen), (l_fab + w_fab - wall_thickness, -mating_overlen),
                    (l_fab + w_fab - wall_thickness, (pos_count - 1) * pin_pitch + mating_overlen), (l_fab + wall_thickness, (pos_count - 1) * pin_pitch + mating_overlen),
                    (l_fab + wall_thickness, center_fab.y + notch_width/2), (l_fab + wall_thickness, center_fab.y + notch_width/2),
                    (l_fab - lyr_offset, center_fab.y + notch_width/2)]
                kicad_mod.append(PolygonLine(shape=mating_conn_polygon, layer=layer, width=line_width))

        # horizontal mating connector 'notch' lines
        if orientation == 'Horizontal' and not latching:
            kicad_modg.append(Line(start=[body_offset - lyr_offset, center_fab.y - notch_width / 2], end=[l_fab + w_fab + lyr_offset, center_fab.y - notch_width / 2], layer=layer, width=line_width))
            kicad_modg.append(Line(start=[body_offset - lyr_offset, center_fab.y + notch_width / 2], end=[l_fab + w_fab + lyr_offset, center_fab.y + notch_width / 2], layer=layer, width=line_width))

        # vertical latches (horizontal latches are off the PCB and not shown)
        if orientation == "Vertical" and latching and latch_length > 0:
            # body outline silk lines need to clear the mounting hole on vertical headers
            if mh_present and layer == "F.SilkS":
                # top latch
                latch_top_polygon = [(center_fab.x - latch_width/2 - lyr_offset, mh_y.x - mhole_pad.y/2 + lyr_offset), (center_fab.x - latch_width/2 - lyr_offset, t_fab - latch_length - lyr_offset),
                    (center_fab.x + latch_width/2 + lyr_offset, t_fab - latch_length - lyr_offset), (center_fab.x + latch_width/2 + lyr_offset, mh_y.x - mhole_pad.y/2 + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=latch_top_polygon, layer=layer, width=line_width))
                # bottom latch
                latch_bottom_polygon = [(center_fab.x - latch_width/2 - lyr_offset, mh_y.y + mhole_pad.y/2 - lyr_offset), (center_fab.x - latch_width/2 - lyr_offset, t_fab + h_fab + latch_length + lyr_offset),
                    (center_fab.x + latch_width/2 + lyr_offset, t_fab + h_fab + latch_length + lyr_offset), (center_fab.x + latch_width/2 + lyr_offset, mh_y.y + mhole_pad.y/2 - lyr_offset)]
                kicad_mod.append(PolygonLine(shape=latch_bottom_polygon, layer=layer, width=line_width))
            else:
                # top latch
                latch_top_polygon = [(center_fab.x - latch_width/2 - lyr_offset, t_fab - lyr_offset), (center_fab.x - latch_width/2 - lyr_offset, t_fab - latch_length - lyr_offset),
                    (center_fab.x + latch_width/2 + lyr_offset, t_fab - latch_length - lyr_offset), (center_fab.x + latch_width/2 + lyr_offset, t_fab - lyr_offset)]
                kicad_mod.append(PolygonLine(shape=latch_top_polygon, layer=layer, width=line_width))
                # bottom latch
                latch_bottom_polygon = [(center_fab.x - latch_width/2 - lyr_offset, t_fab + h_fab + lyr_offset), (center_fab.x - latch_width/2 - lyr_offset, t_fab + h_fab + latch_length + lyr_offset),
                    (center_fab.x + latch_width/2 + lyr_offset, t_fab + h_fab + latch_length + lyr_offset), (center_fab.x + latch_width/2 + lyr_offset, t_fab + h_fab + lyr_offset)]
                kicad_mod.append(PolygonLine(shape=latch_bottom_polygon, layer=layer, width=line_width))

    # horizontal pin outlines (only applies if the body is right of the leftmost pin row)
    # if orientation == 'Horizontal' and not latching:
    if body_offset > 0:
        for row in range(pos_count):
            horiz_pin_polygon = [(body_offset, pin_pitch * row - pin_size / 2), (-pin_size / 2, pin_pitch * row - pin_size / 2),
                (-pin_size / 2, pin_pitch * row + pin_size / 2), (body_offset, pin_pitch * row + pin_size / 2)]
            kicad_modg.append(PolygonLine(shape=horiz_pin_polygon, layer='F.Fab', width=gc.fab_line_width))

    # silk pin 1 mark (triangle to the left of pin 1)
    slk_mark_height = 1
    slk_mark_width = 1
    if pins_drill == 0:
        slk_polygon = [(l_fab - gc.silk_fab_offset, -((pos_count-1)*pin_pitch/2)-pad.y/2-0.5), (l_fab - gc.silk_fab_offset-1.5, -((pos_count-1)*pin_pitch/2)-pad.y/2-0.5)]
    else:
        slk_mark_tip = min(l_fab, -pad.x / 2) - 0.5 # offset 0.5mm from pin 1 or the body
        slk_polygon = [(slk_mark_tip, 0), (slk_mark_tip - slk_mark_width, -slk_mark_height / 2),
            (slk_mark_tip - slk_mark_width, slk_mark_height / 2), (slk_mark_tip, 0)]
    kicad_mod.append(PolygonLine(shape=slk_polygon, layer='F.SilkS', width=gc.silk_line_width))

    # create courtyard
    if pins_drill == 0 and orientation == "Vertical" and not latching:
        #         l_crt =  -pad.x / 2 - row_pitch/2- crt_offset
        crt_polygon = [
            (roundCrt(l_fab - crtyd_offset), roundCrt(t_crt)),
            (roundCrt(l_fab - crtyd_offset), roundCrt(-((pos_count-1)*pin_pitch/2)-pad.y/2 - crtyd_offset)),
            (roundCrt(l_crt), roundCrt(-((pos_count-1)*pin_pitch/2)-pad.y/2 - crtyd_offset)),
            (roundCrt(l_crt), roundCrt(((pos_count-1)*pin_pitch/2)+pad.y/2 + crtyd_offset)),
            (roundCrt(l_fab - crtyd_offset), roundCrt(((pos_count-1)*pin_pitch/2)+pad.y/2 + crtyd_offset)),
            (roundCrt(l_fab - crtyd_offset), roundCrt(-t_crt)),
            (roundCrt(-l_fab + crtyd_offset), roundCrt(-t_crt)),
            (roundCrt(-l_fab + crtyd_offset), roundCrt(((pos_count-1)*pin_pitch/2)+pad.y/2 + crtyd_offset)),
            (roundCrt(-l_crt), roundCrt(((pos_count-1)*pin_pitch/2)+pad.y/2 + crtyd_offset)),
            (roundCrt(-l_crt), roundCrt(-((pos_count-1)*pin_pitch/2)-pad.y/2 - crtyd_offset)),
            (roundCrt(-l_fab + crtyd_offset), roundCrt(-((pos_count-1)*pin_pitch/2)-pad.y/2 - crtyd_offset)),
            (roundCrt(-l_fab + crtyd_offset), roundCrt(t_crt)),
            (roundCrt(l_fab - crtyd_offset), roundCrt(t_crt))
        ]
        kicad_mod.append(PolygonLine(shape=crt_polygon, layer='F.CrtYd', width=gc.courtyard_line_width))
    else:
        kicad_mod.append(Rectangle(start=[roundCrt(l_crt), roundCrt(t_crt)], end=[roundCrt(l_crt + w_crt),
                    roundCrt(t_crt + h_crt)], layer='F.CrtYd', width=gc.courtyard_line_width))

    # create pads (first the left row then the right row)
    if pins_drill == 0:
        pad_type = Pad.TYPE_SMT
        pad_shape = Pad.SHAPE_ROUNDRECT
        pad_layers = Pad.LAYERS_SMT
    else:
        pad_type = Pad.TYPE_THT
        pad_shape = Pad.SHAPE_OVAL
        pad_layers = Pad.LAYERS_THT

    if pins_drill == 0:
        # For SMD footprints, pad 1 location is not (0,0)
        for start_pos, initial in zip([-row_pitch/2, row_pitch/2], range(1, row_count + 1)):
            kicad_modg.append(PadArray(pincount=pos_count, spacing=[0,pin_pitch], start=[start_pos,-(pos_count-1)*pin_pitch/2], initial=initial, increment=row_count,
                type=pad_type, shape=pad_shape, size=pad, drill=pins_drill, layers=pad_layers,
                round_radius_handler=global_config.roundrect_radius_handler))
    else:
        for start_pos, initial in zip([0, row_pitch], range(1, row_count + 1)):
            kicad_modg.append(PadArray(pincount=pos_count, spacing=[0,pin_pitch], start=[start_pos,0], initial=initial, increment=row_count,
                type=pad_type, shape=pad_shape, size=pad, drill=pins_drill, layers=pad_layers,
                round_radius_handler=global_config.roundrect_radius_handler))

    # create mounting hole pads
    if mh_present:
        for mh_y_offset in mh_y:
            kicad_modg.append(Pad(number=mhole_nr, type=Pad.TYPE_THT, shape=Pad.SHAPE_OVAL, at=[mhole_offset, mh_y_offset], size=mhole_pad,
                drill=mhole_drill, layers=Pad.LAYERS_THT))

    # add model (even if there are mounting holes on the footprint do not include that in the 3D model)
    kicad_modg.append(
        Model(
            filename=global_config.model_3d_prefix
            + lib_name
            + ".3dshapes/"
            + footprint_name
            + global_config.model_3d_suffix
        )
    )

    write_footprint(kicad_mod, lib_name, generator_name)

# THT Angled (Horizontal) Pinheader:
#####################################
#             <--> body_offset
#                 <-------> body_width
#                          <------------------------------> pin_length
#    <--------> row_pitch
# +---            +-------+
# | OOO      OOO  |       +-------------------------------+            ^
# | OOO ==== OOO  |       |                               +    ^       pin_width
#   OOO      OOO  |       +-------------------------------+    |       v
#                 +-------+                                    pin_pitch
#   OOO      OOO  |       +-------------------------------+    |
#   OOO ==== OOO  |       |                               +    v
#   OOO      OOO  |       +-------------------------------+
#                 +-------+
#
def makePinHeadAngled(
    generator_name,
    global_config: GC.GlobalConfig,
    pos_count: int,
    row_count: int,
    pin_pitch: float,
    row_pitch: float,
    body_width: float,
    body_offset: float,
    pin_length: float,
    pin_width: float,
    pins_drill: float,
    pad: Vec2DCompatible,
    tags_additional: list[str] = [],
    lib_name: str = "Pin_Headers",
    classname: str = "Pin_Header",
    class_description: str = "pin header",
):
    gc = global_config
    pad = Vector2D(pad)
    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    # This is set a bit further out than normal, not quite clear why.
    # silk_pad_offset = gc.silk_pad_offset
    silk_pad_offset = gc.silk_pad_clearance + gc.silk_fab_offset

    h_fabb = (pos_count - 1) * pin_pitch + pin_pitch / 2 + pin_pitch / 2
    w_fabb = body_width
    l_fabb = row_pitch * (row_count - 1) + body_offset
    t_fabb = -pin_pitch / 2
    l_fabp = l_fabb + w_fabb
    t_fabp = -pin_width / 2

    fab_text_props = gc.get_text_properties_for_layer("F.Fab")
    fabref_text_size, fabref_text_thickness = fab_text_props.clamp_size(w_fabb * 0.6)
    # That causes diffs, use the old unrounded calc for now
    fabref_text_thickness = fabref_text_size.y * 0.15

    w_slkb = w_fabb + 2 * gc.silk_fab_offset
    l_slkb = l_fabb - gc.silk_fab_offset
    t_slkb = t_fabb - gc.silk_fab_offset
    l_slkp = l_slkb + w_slkb
    l_slk = -pin_pitch / 2
    t_slk = -pin_pitch / 2
    body_lines_y = False

    w_crt = pin_pitch / 2 + (row_count - 1) * row_pitch + body_offset + body_width + pin_length + 2 * crtyd_offset
    h_crt = h_fabb + 2 * crtyd_offset
    l_crt = -pin_pitch / 2 - crtyd_offset
    t_crt = -pin_pitch / 2 - crtyd_offset

    # if pin_pitch == 2.54:
    #    footprint_name = "Pin_Header_Angled_{0}x{1:02}".format(row_count, pos_count)
    # else:
    footprint_name = "{3}_{0}x{1:02}_P{2:03.2f}mm_Horizontal".format(row_count, pos_count, pin_pitch, classname)

    description = "Through hole angled {4}, {0}x{1:02}, {2:03.2f}mm pitch, {3}mm pin length".format(row_count, pos_count,
                                                                                                    pin_pitch,
                                                                                                    pin_length,
                                                                                                    class_description)
    tags = "Through hole angled {3} THT {0}x{1:02} {2:03.2f}mm".format(row_count, pos_count, pin_pitch, class_description)
    if row_count == 1:
        description = description + ", single row"
        tags = tags + " single row"
    elif row_count == 2:
        description = description + ", double rows"
        tags = tags + " double row"
    elif row_count == 3:
        description = description + ", triple rows"
        tags = tags + " triple row"

    if len(tags_additional) > 0:
        for t in tags_additional:
            footprint_name = footprint_name + "_" + t
            description = description + ", " + t
            tags = tags + " " + t

    # init kicad footprint
    kicad_mod = Footprint(footprint_name, FootprintType.THT)
    kicad_mod.description = description
    kicad_mod.tags = tags

    # anchor for SMD-symbols is in the center, for THT-sybols at pin1
    offset = Vector2D(0, 0)
    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    # set general values
    kicad_modg.append(
        Property(name=Property.REFERENCE, text='REF**', at=[l_crt + w_crt / 2, t_crt + crtyd_offset - txt_offset], layer='F.SilkS'))
    kicad_modg.append(
        Text(text='${REFERENCE}', at=[l_fabb + (w_fabb/2), t_crt + offset.y + (h_crt/2)], rotation=90, layer='F.Fab', size=fabref_text_size, thickness=fabref_text_thickness))
    kicad_modg.append(
        Property(name=Property.VALUE, text=footprint_name, at=[l_crt + w_crt / 2, t_crt + h_crt - crtyd_offset + txt_offset],
             layer='F.Fab'))

    # create FAB-layer
    chamfer = w_fabb/4
    kicad_modg.append(Line(start=[l_fabb + chamfer, t_fabb], end=[l_fabb + w_fabb, t_fabb], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fabb + w_fabb, t_fabb], end=[l_fabb + w_fabb, t_fabb+pin_pitch*pos_count], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fabb + w_fabb, t_fabb+pin_pitch*pos_count], end=[l_fabb, t_fabb+pin_pitch*pos_count], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fabb, t_fabb+pin_pitch*pos_count], end=[l_fabb, t_fabb+chamfer], layer='F.Fab', width=gc.fab_line_width))
    kicad_modg.append(Line(start=[l_fabb, t_fabb+chamfer], end=[l_fabb + chamfer, t_fabb], layer='F.Fab', width=gc.fab_line_width))
    y1 = t_fabb
    yp = t_fabp
    for r in range(1, pos_count + 1):
        kicad_modg.append(Line(start=[-pin_width/2, yp], end=[l_fabb, yp], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[-pin_width/2, yp], end=[-pin_width/2, yp + pin_width], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[-pin_width/2, yp + pin_width], end=[l_fabb, yp + pin_width], layer='F.Fab', width=gc.fab_line_width))

        kicad_modg.append(Line(start=[l_fabb + w_fabb, yp], end=[l_fabp + pin_length, yp], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fabp + pin_length, yp], end=[l_fabp + pin_length, yp + pin_width], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fabb + w_fabb, yp + pin_width], end=[l_fabp + pin_length, yp + pin_width], layer='F.Fab', width=gc.fab_line_width))

        y1 = y1 + pin_pitch
        yp = yp + pin_pitch

    # create SILKSCREEN-layer + pin1 marker

    # calculate point to avoid collision with pad clearance
    pin_line_x = sqrt(((pad.x/2+ silk_pad_offset) * (pad.x/2+ silk_pad_offset) - (pin_width/2+gc.silk_fab_offset) * (pin_width/2+gc.silk_fab_offset)))
    # Silkscreen body
    body_min_x_square = pad.x/2+ silk_pad_offset
    body_min_y_square = pad.y/2+ silk_pad_offset

    if pin_pitch/2 < body_min_y_square:
        body_min_x_round = sqrt((((pad.x/2+ silk_pad_offset) * (pad.x/2+ silk_pad_offset)) - (pin_pitch/2 * pin_pitch/2)))
        if l_slkb > body_min_x_round + (row_count-1)*row_pitch and l_slkb < body_min_x_square +(row_count-1)*row_pitch:
            body_lines_y = sqrt((((pad.x/2+ silk_pad_offset) * (pad.x/2+ silk_pad_offset)) - ((l_slkb-(row_count-1)*row_pitch) * (l_slkb-(row_count-1)*row_pitch))))
    else:
        body_min_x_round  = 0
    if pin_pitch/2+gc.silk_fab_offset < body_min_y_square:
        bodyend_min_x_round = sqrt((((pad.x/2+ silk_pad_offset) * (pad.x/2+ silk_pad_offset)) - ((pin_pitch/2+gc.silk_fab_offset) * (pin_pitch/2+gc.silk_fab_offset))))
    else:
        bodyend_min_x_round = 0
    # if body is starting outside the pads
    if l_slkb-gc.silk_fab_offset > pad.x/2 + gc.silk_pad_clearance + (row_count-1)*row_pitch:
        kicad_modg.append(Rectangle(start=[l_slkb, t_slkb], end=[l_slkp, t_slkb+pin_pitch*pos_count+gc.silk_fab_offset*2], layer='F.SilkS', width=gc.silk_line_width))
    else:
        if l_slkb < body_min_x_square + (row_count-1)*row_pitch and t_slkb-gc.silk_fab_offset > -(body_min_y_square + (row_count-1)*row_pitch):
            if row_count == 1:
                upper_body_x = body_min_x_square
            else:
                upper_body_x = bodyend_min_x_round + (row_count-1)*row_pitch
        else:
            upper_body_x = l_slkb
        if pos_count == 1 and row_count == 1:
            lower_body_x = body_min_x_square  + (row_count-1)*row_pitch
        elif l_slkb < bodyend_min_x_round + (row_count-1)*row_pitch and t_slkb-gc.silk_fab_offset > -(body_min_y_square + (row_count-1)*row_pitch):
            lower_body_x = bodyend_min_x_round + (row_count-1)*row_pitch
        else:
            lower_body_x = l_slkb
        if body_lines_y != False:
            if row_count == 1:
                kicad_modg.append(PolygonLine(shape=[[upper_body_x, t_slkb], [l_slkp, t_slkb], [l_slkp, t_slkb + pin_pitch * pos_count + gc.silk_fab_offset * 2],
                                                        [lower_body_x, t_slkb+pin_pitch*pos_count+gc.silk_fab_offset*2], [lower_body_x, t_slkb+pin_pitch*pos_count-pin_pitch/2+gc.silk_fab_offset+body_lines_y]], layer='F.SilkS', width=gc.silk_line_width))
            else:
                kicad_modg.append(PolygonLine(shape=[[upper_body_x, -body_lines_y], [upper_body_x, t_slkb], [l_slkp, t_slkb], [l_slkp, t_slkb + pin_pitch * pos_count + gc.silk_fab_offset * 2],
                                                        [lower_body_x, t_slkb+pin_pitch*pos_count+gc.silk_fab_offset*2], [lower_body_x, t_slkb+pin_pitch*pos_count-pin_pitch/2+gc.silk_fab_offset+body_lines_y]], layer='F.SilkS', width=gc.silk_line_width))
        else:
            kicad_modg.append(PolygonLine(shape=[[upper_body_x, t_slkb], [l_slkp, t_slkb], [l_slkp, t_slkb + pin_pitch * pos_count + gc.silk_fab_offset * 2],
                                                    [lower_body_x, t_slkb+pin_pitch*pos_count+gc.silk_fab_offset*2]], layer='F.SilkS', width=gc.silk_line_width))

    for r in range(0, pos_count):
        if r != 0:
            if r == 1 and pin_pitch / 2 < body_min_y_square and row_count == 1:
                if l_slkb < body_min_x_square:
                    kicad_modg.append(Line(start=[body_min_x_square, (r-1)*pin_pitch+pin_pitch/2], end=[l_slkp, (r-1)*pin_pitch+pin_pitch/2], layer='F.SilkS',width=gc.silk_line_width))
                else:
                    kicad_modg.append(Line(start=[l_slkb, (r-1)*pin_pitch+pin_pitch/2], end=[l_slkp, (r-1)*pin_pitch+pin_pitch/2], layer='F.SilkS',width=gc.silk_line_width))
            else:
                # add line between rows
                if l_slkb < body_min_x_round + (row_count-1)*row_pitch:
                    kicad_modg.append(Line(start=[body_min_x_round+ (row_count-1)*row_pitch, (r-1)*pin_pitch+pin_pitch/2], end=[l_slkp, (r-1)*pin_pitch+pin_pitch/2], layer='F.SilkS',width=gc.silk_line_width))
                else:
                    kicad_modg.append(Line(start=[l_slkb, (r-1)*pin_pitch+pin_pitch/2], end=[l_slkp, (r-1)*pin_pitch+pin_pitch/2], layer='F.SilkS',width=gc.silk_line_width))
                    if body_lines_y != False:
                        kicad_modg.append(Line(start=[l_slkb, (r-1)*pin_pitch+body_lines_y], end=[l_slkb, (r)*pin_pitch-body_lines_y], layer='F.SilkS',width=gc.silk_line_width))

        # pin outline
        if r != 0:
            kicad_modg.append(
                PolygonLine(
                    shape=[
                        [l_slkp, r * pin_pitch - pin_width / 2 - gc.silk_fab_offset],
                        [l_slkp + pin_length, r * pin_pitch - pin_width / 2 - gc.silk_fab_offset],
                        [l_slkp + pin_length, r * pin_pitch + pin_width / 2 + gc.silk_fab_offset],
                        [l_slkp, r * pin_pitch + pin_width / 2 + gc.silk_fab_offset],
                    ],
                    layer="F.SilkS",
                    width=gc.silk_line_width,
                )
            )
        else:
            # color the first pin
            kicad_modg.append(
                Rectangle(
                    start=Vector2D(l_slkp, -pin_width / 2 - gc.silk_fab_offset),
                    end=Vector2D(l_slkp + pin_length, pin_width / 2 + gc.silk_fab_offset),
                    layer="F.SilkS",
                    width=gc.silk_line_width,
                    fill=True,
                )
            )

        # if body is starting at the pads
        if l_slkb-gc.silk_fab_offset > pad.x/2 + gc.silk_pad_clearance + (row_count-1)*row_pitch:
            if r == 0 and row_count == 1:
                # add the lines between pads and silkscreenbody
                kicad_modg.append(Line(start=[pad.x/2+ silk_pad_offset, r*pin_pitch-pin_width/2-gc.silk_fab_offset],
                    end=[l_slkb, r*pin_pitch-pin_width/2-gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[pad.x/2+ silk_pad_offset, r*pin_pitch+pin_width/2+gc.silk_fab_offset],
                    end=[l_slkb, r*pin_pitch+pin_width/2+gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
            else:
                # add the lines between pads and silkscreenbody
                kicad_modg.append(Line(start=[(row_count-1)*row_pitch + pin_line_x, r*pin_pitch-pin_width/2-gc.silk_fab_offset],
                    end=[l_slkb, r*pin_pitch-pin_width/2-gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[(row_count-1)*row_pitch + pin_line_x, r*pin_pitch+pin_width/2+gc.silk_fab_offset],
                    end=[l_slkb, r*pin_pitch+pin_width/2+gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))

        if row_count > 1:
            for c in range(1, row_count):
                # add the lines between pads
                start_point_x = (c - 1) * row_pitch + pin_line_x
                end_point_x = c * row_pitch - pin_line_x
                if start_point_x < end_point_x - gc.silk_line_width:
                    if r == 0 and c == 1:
                        kicad_modg.append(Line(start=[pad.x/2 + silk_pad_offset, r*pin_pitch-pin_width/2-gc.silk_fab_offset],
                            end=[end_point_x, r*pin_pitch-pin_width/2-gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                        kicad_modg.append(Line(start=[pad.x/2 + silk_pad_offset, r*pin_pitch+pin_width/2+gc.silk_fab_offset],
                            end=[end_point_x, r*pin_pitch+pin_width/2+gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                    else:
                        kicad_modg.append(Line(start=[start_point_x, r*pin_pitch-pin_width/2-gc.silk_fab_offset],
                        end=[end_point_x, r*pin_pitch-pin_width/2-gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
                        kicad_modg.append(Line(start=[start_point_x, r*pin_pitch+pin_width/2+gc.silk_fab_offset],
                        end=[end_point_x, r*pin_pitch+pin_width/2+gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))

    # pin 1 marker
    pin1_min = -(pad.x / 2 + silk_pad_offset)
    if pin1_min < l_slk:
        pin1_x = pin1_min
    else:
        pin1_x = l_slk
    if pin1_min < t_slk:
        pin1_y = pin1_min
    else:
        pin1_y = t_slk
    kicad_modg.append(PolygonLine(shape=[[pin1_x, 0], [pin1_x, pin1_y], [0, pin1_y]], layer='F.SilkS', width=gc.silk_line_width))

    # create courtyard
    kicad_mod.append(Rectangle(start=[roundCrt(l_crt + offset.x), roundCrt(t_crt + offset.y)],
                              end=[roundCrt(l_crt + offset.x + w_crt), roundCrt(t_crt + offset.y + h_crt)],
                              layer='F.CrtYd', width=gc.courtyard_line_width))

    # create pads
    x1 = 0
    y1 = 0

    pad_type = Pad.TYPE_THT
    pad_shape1 = Pad.SHAPE_RECT
    pad_shapeother = Pad.SHAPE_OVAL
    pad_layers = Pad.LAYERS_THT

    p = 1

    for r in range(1, pos_count + 1):
        x1 = 0
        for c in range(1, row_count + 1):
            if p == 1:
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[x1, y1], size=pad, drill=pins_drill,
                                      layers=pad_layers))
            else:
                kicad_modg.append(
                    Pad(number=p, type=pad_type, shape=pad_shapeother, at=[x1, y1], size=pad, drill=pins_drill,
                        layers=pad_layers))

            p = p + 1
            x1 = x1 + row_pitch

        y1 = y1 + pin_pitch

    # add model
    kicad_modg.append(
        Model(
            filename=global_config.model_3d_prefix
            + lib_name
            + ".3dshapes/"
            + footprint_name
            + global_config.model_3d_suffix
        )
    )

    write_footprint(kicad_mod, lib_name, generator_name)


# THT Angled (Horizontal) PinSocket:
#####################################
# <--------------------------------------> body_width
#                                             <- ------> row_pitch
#                                          <-> body_offset
# +---------------------------------------+            ---+
# |                                       |  OOO      OOO |    ^
# |                                       |  OOO ==== OOO | ^  pin_width
# |                                       |  OOO      OOO   |  v
# +---------------------------------------+                 pin_pitch
# |                                       |  OOO      OOO   |
# |                                       |  OOO ==== OOO   v
# |                                       |  OOO      OOO
# +---------------------------------------+
#
def makeSocketStripAngled(
    generator_name,
    global_config: GC.GlobalConfig,
    pos_count: int,
    row_count: int,
    pin_pitch: float,
    row_pitch: float,
    body_width: float,
    body_offset: float,
    pin_width: float,
    pins_drill: float,
    pad: Vec2DCompatible,
    tags_additional: list[str] = [],
    lib_name: str = "Socket_Strips",
    class_name: str = "Socket_Strip",
    class_description: str = "socket strip",
    name_format: str | None = None,
):
    gc = global_config
    pad = Vector2D(pad)
    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    h_fabb = (pos_count - 1) * pin_pitch + pin_pitch / 2 + pin_pitch / 2
    w_fabb = -body_width
    l_fabb = -1 * (row_pitch * (row_count - 1) + body_offset)
    t_fabb = -pin_pitch / 2
    t_fabp = -pin_width / 2

    w_slkb = w_fabb - 2 * gc.silk_fab_offset
    l_slkb = l_fabb + gc.silk_fab_offset
    t_slkb = t_fabb - gc.silk_fab_offset
    l_slkp = l_slkb + w_slkb
    t_slkp = t_fabp - gc.silk_fab_offset

    w_crt = -1*(pin_pitch / 2 + (row_count - 1) * row_pitch + body_offset + body_width  + 2 * crtyd_offset)
    h_crt = h_fabb + 2 * crtyd_offset
    l_crt = pin_pitch / 2 + crtyd_offset
    t_crt = -pin_pitch / 2 - crtyd_offset

    if name_format is None:
        name_format = "{class_name}_{row_count}x{pos_count:02}_P{pitch:03.2f}mm_Horizontal"
    footprint_name = name_format.format(class_name=class_name, row_count=row_count, pos_count=pos_count, pitch=pin_pitch)

    description = "Through hole angled {4}, {0}x{1:02}, {2:03.2f}mm pitch, {3}mm socket length".format(row_count, pos_count,
                                                                                                    pin_pitch,
                                                                                                    body_width,
                                                                                                    class_description)
    tags = "Through hole angled {3} THT {0}x{1:02} {2:03.2f}mm".format(row_count, pos_count, pin_pitch, class_description)
    if (row_count == 1):
        description = description + ", single row"
        tags = tags + " single row"
    elif row_count == 2:
        description = description + ", double rows"
        tags = tags + " double row"
    elif row_count == 3:
        description = description + ", triple rows"
        tags = tags + " triple row"

    if len(tags_additional) > 0:
        for t in tags_additional:
            footprint_name = footprint_name + "_" + t
            description = description + ", " + t
            tags = tags + " " + t

    # init kicad footprint
    kicad_mod = Footprint(footprint_name, FootprintType.THT)
    kicad_mod.description = description
    kicad_mod.tags = tags

    # anchor for SMD-symbols is in the center, for THT-sybols at pin1
    offset = Vector2D(0, 0)
    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    # set general values
    kicad_modg.append(
        Property(name=Property.REFERENCE, text='REF**', at=[l_crt + w_crt / 2, t_crt + crtyd_offset - txt_offset], layer='F.SilkS'))
    kicad_modg.append(
        Text(text='${REFERENCE}', at=[l_crt + w_crt / 2, t_crt + crtyd_offset - txt_offset], layer='F.Fab'))
    kicad_modg.append(
        Property(name=Property.VALUE, text=footprint_name, at=[l_crt + w_crt / 2, t_crt + h_crt - crtyd_offset + txt_offset],
             layer='F.Fab'))

    # create FAB-layer
    y1 = t_fabb
    yp = t_fabp
    for r in range(1, pos_count + 1):
        kicad_modg.append(Rectangle(start=[l_fabb, y1], end=[l_fabb + w_fabb, y1 + pin_pitch], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(
            Rectangle(start=[0, yp], end=[l_fabb , yp + pin_width], layer='F.Fab', width=gc.fab_line_width))
        y1 = y1 + pin_pitch
        yp = yp + pin_pitch

    # create SILKSCREEN-layer + pin1 marker
    y1 = t_slkb
    yp = t_slkp
    for r in range(1, pos_count + 1):
        if pos_count == 1 and r == 1:
            kicad_modg.append(
                Rectangle(start=[l_slkb, y1], end=[l_slkp, y1 + pin_pitch + 2 * gc.silk_fab_offset], layer='F.SilkS',
                         width=gc.silk_line_width))
        if (r == 1 or r == pos_count):
            kicad_modg.append(Rectangle(start=[l_slkb, y1], end=[l_slkp, y1 + pin_pitch + gc.silk_fab_offset], layer='F.SilkS',
                                       width=gc.silk_line_width))
            y1 = y1 + gc.silk_fab_offset
        else:
            kicad_modg.append(Rectangle(start=[l_slkb, y1], end=[l_slkp, y1 + pin_pitch], layer='F.SilkS', width=gc.silk_line_width))

        kicad_modg.append(Line(start=[-1*((row_count - 1) * row_pitch + pad.x / 2 + gc.silk_fab_offset+gc.silk_line_width), yp], end=[l_slkb, yp], layer='F.SilkS',width=gc.silk_line_width))
        kicad_modg.append(Line(start=[-1*((row_count - 1) * row_pitch + pad.x / 2 + gc.silk_fab_offset+gc.silk_line_width), yp + pin_width + 2 * gc.silk_fab_offset],end=[l_slkb, yp + pin_width + 2 * gc.silk_fab_offset], layer='F.SilkS', width=gc.silk_line_width))
        if row_count > 1:
            for c in range(2, row_count + 1):
                kicad_modg.append(Line(start=[-1*((c - 2) * row_pitch + pad.x / 2 + gc.silk_fab_offset+gc.silk_line_width), yp],
                                       end=[-1*((c - 1) * row_pitch - pad.x / 2 - gc.silk_fab_offset-gc.silk_line_width), yp], layer='F.SilkS',
                                       width=gc.silk_line_width))
                kicad_modg.append(
                    Line(start=[-1*((c - 2) * row_pitch + pad.x / 2 + gc.silk_fab_offset+gc.silk_line_width), yp + pin_width + 2 * gc.silk_fab_offset],
                         end=[-1*((c - 1) * row_pitch - pad.x / 2 - gc.silk_fab_offset-gc.silk_line_width), yp + pin_width + 2 * gc.silk_fab_offset],
                         layer='F.SilkS', width=gc.silk_line_width))
        if r == 1:
            y = y1 + gc.silk_line_width
            while y < y1 + pin_pitch + 2 * gc.silk_fab_offset:
                kicad_modg.append(Line(start=[l_slkb, y], end=[l_slkp, y], layer='F.SilkS', width=gc.silk_line_width))
                y = y + gc.silk_line_width
        y1 = y1 + pin_pitch
        yp = yp + pin_pitch

    kicad_modg.append(PolygonLine(shape=[[0, -pin_pitch / 2], [pin_pitch / 2, -pin_pitch / 2], [pin_pitch / 2, 0]], layer='F.SilkS', width=gc.silk_line_width))

    # create courtyard
    kicad_mod.append(Rectangle(start=[roundCrt(l_crt + offset.x), roundCrt(t_crt + offset.y)],
                              end=[roundCrt(l_crt + offset.x + w_crt), roundCrt(t_crt + offset.y + h_crt)],
                              layer='F.CrtYd', width=gc.courtyard_line_width))

    # create pads
    x1 = 0
    y1 = 0

    pad_type = Pad.TYPE_THT
    pad_shape1 = Pad.SHAPE_RECT
    pad_shapeother = Pad.SHAPE_OVAL
    pad_layers = Pad.LAYERS_THT

    p = 1
    for r in range(1, pos_count + 1):
        x1 = 0
        for c in range(1, row_count + 1):
            if p == 1:
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[x1, y1], size=pad, drill=pins_drill,
                                      layers=pad_layers))
            else:
                kicad_modg.append(
                    Pad(number=p, type=pad_type, shape=pad_shapeother, at=[x1, y1], size=pad, drill=pins_drill,
                        layers=pad_layers))

            p = p + 1
            x1 = x1 - row_pitch

        y1 = y1 + pin_pitch

    # add model
    kicad_modg.append(
        Model(
            filename=global_config.model_3d_prefix
            + lib_name
            + ".3dshapes/"
            + footprint_name
            + global_config.model_3d_suffix
        )
    )

    write_footprint(kicad_mod, lib_name, generator_name)


# SMD Straight (Vertical) Pinheader:
#####################################
# <----------------------> body_width
#        <--------> row_pitch
#     <--> pads_offset
# +----------------------+
# | OOOOOOO              |     ^
# | OOOOOOO ====         |  ^  pads_width
# | OOOOOOO              |  |  v
# +                      +  pin_pitch
# |              OOOOOOO |  |
# |         ==== OOOOOOO |  v
# |              OOOOOOO |
# +                      +
# | OOOOOOO              |
# | OOOOOOO ====         |
def makePinHeadStraightSMD(
    generator_name,
    global_config: GC.GlobalConfig,
    pos_count: int,
    row_count: int,
    pin_pitch: float,
    row_pitch: float,
    smd_pad_offset: float,
    posx_pin_length: float,
    pin_width: float,
    body_width: float,
    body_overlength: float,
    pad: Vec2DCompatible,
    start_left: bool = True,
    tags_additional: list[str] = [],
    lib_name: str = "Pin_Headers",
    classname: str = "Pin_Header",
    class_description: str = "pin header",
    isSocket: bool = False,
):
    gc = global_config
    overlen_top = pin_pitch/2 + body_overlength
    overlen_bot = pin_pitch/2 + body_overlength

    pad = Vector2D(pad)
    crtyd_offset = gc.get_courtyard_offset(GC.GlobalConfig.CourtyardType.CONNECTOR)

    # This is set a bit further out than normal, not quite clear why.
    # silk_pad_offset = gc.silk_pad_offset
    silk_pad_offset = gc.silk_pad_clearance + gc.silk_fab_offset

    pins_drill = 0.5
    h_fab = (pos_count - 1) * pin_pitch + overlen_top + overlen_bot
    w_fab = body_width
    l_fab = (row_pitch * (row_count - 1) - w_fab) / 2
    t_fab = -overlen_top

    h_slk = h_fab + 2 * gc.silk_fab_offset
    w_slk = max(
        w_fab + 2 * gc.silk_fab_offset,
        row_pitch * (row_count - 1) - pad.x - 4 * gc.silk_fab_offset,
    )
    l_slk = (row_pitch * (row_count - 1) - w_slk) / 2
    t_slk = -overlen_top - gc.silk_fab_offset

    w_crt = (
        max(body_width, row_pitch * (row_count - 1) + 2 * smd_pad_offset + pad.x)
        + 2 * crtyd_offset
    )
    h_crt = max(h_fab, (pos_count - 1) * pin_pitch + pad.y) + 2 * crtyd_offset
    l_crt = row_pitch * (row_count - 1) / 2 - w_crt / 2
    t_crt = (pos_count - 1) * pin_pitch / 2 - h_crt / 2

    # if pin_pitch == 2.54:
    #    footprint_name = "Pin_Header_Straight_{0}x{1:02}".format(row_count, pos_count)
    # else:
    footprint_name = "{3}_{0}x{1:02}_P{2:03.2f}mm_Vertical_SMD".format(row_count, pos_count, pin_pitch,classname)

    description = "surface-mounted straight {3}, {0}x{1:02}, {2:03.2f}mm pitch".format(row_count, pos_count, pin_pitch,class_description)
    tags = "Surface mounted {3} SMD {0}x{1:02} {2:03.2f}mm".format(row_count, pos_count, pin_pitch,class_description)
    if row_count == 1:
        description = description + ", single row"
        tags = tags + " single row"
        if start_left:
            description = description + ", style 1 (pin 1 left)"
            tags = tags + " style1 pin1 left"
            footprint_name = footprint_name + "_Pin1Left"
        else:
            description = description + ", style 2 (pin 1 right)"
            tags = tags + " style2 pin1 right"
            footprint_name = footprint_name + "_Pin1Right"
    elif row_count == 2:
        description = description + ", double rows"
        tags = tags + " double row"

    if len(tags_additional) > 0:
        for t in tags_additional:
            footprint_name = footprint_name + "_" + t
            description = description + ", " + t
            tags = tags + " " + t

    # init kicad footprint
    kicad_mod = Footprint(footprint_name, FootprintType.SMD)
    kicad_mod.description = description
    kicad_mod.tags = tags

    # anchor for SMD-symbols is in the center, for THT-sybols at pin1
    offset = Vector2D(-(row_count-1)*row_pitch/2, -(pos_count-1)*pin_pitch/2.0)

    kicad_modg = Translation(offset[0], offset[1])
    kicad_mod.append(kicad_modg)

    # set general values
    kicad_modg.append(
        Property(name=Property.REFERENCE, text='REF**', at=[row_pitch * (row_count - 1) / 2, t_slk - txt_offset], layer='F.SilkS'))
    kicad_modg.append(
        Text(text='${REFERENCE}', at=[pin_pitch/2*(row_count-1),(pos_count-1)*pin_pitch/2.0], rotation=90, layer='F.Fab'))
    kicad_modg.append(
        Property(name=Property.VALUE, text=footprint_name, at=[row_pitch * (row_count - 1) / 2, t_slk + h_slk + txt_offset], layer='F.Fab'))

    cleft = range(0, pos_count, 2)
    cright = range(1, pos_count, 2)
    if not start_left:
        cleft = range(1, pos_count, 2)
        cright = range(0, pos_count, 2)

    # create FAB-layer
    chamfer = (pin_pitch - pin_width) / 2
    kicad_modg.append(Line(start=[l_fab + w_fab, t_fab+h_fab], end=[l_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))
    if start_left == True:
        kicad_modg.append(Line(start=[l_fab + chamfer, t_fab], end=[l_fab + w_fab, t_fab], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab, t_fab+h_fab], end=[l_fab, t_fab+chamfer], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab, t_fab+chamfer], end=[l_fab + chamfer, t_fab], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab + w_fab, t_fab], end=[l_fab + w_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))
    else:
        kicad_modg.append(Line(start=[l_fab, t_fab], end=[l_fab + w_fab - chamfer, t_fab], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab + w_fab, t_fab+h_fab], end=[l_fab + w_fab, t_fab+chamfer], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab + w_fab, t_fab+chamfer], end=[l_fab + w_fab - chamfer, t_fab], layer='F.Fab', width=gc.fab_line_width))
        kicad_modg.append(Line(start=[l_fab, t_fab], end=[l_fab, t_fab+h_fab], layer='F.Fab', width=gc.fab_line_width))

    if row_count == 1:
        for c in cleft:
            kicad_modg.append(Line(start=[l_fab, c*pin_pitch-pin_width/2], end=[-posx_pin_length, c*pin_pitch-pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[-posx_pin_length, c*pin_pitch-pin_width/2], end=[-posx_pin_length, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[-posx_pin_length, c*pin_pitch+pin_width/2], end=[l_fab, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
        for c in cright:
            kicad_modg.append(Line(start=[l_fab + w_fab, c*pin_pitch-pin_width/2], end=[posx_pin_length, c*pin_pitch-pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[posx_pin_length, c*pin_pitch-pin_width/2], end=[posx_pin_length, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[posx_pin_length, c*pin_pitch+pin_width/2], end=[l_fab + w_fab, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
    elif row_count == 2:
        for c in range(0,pos_count):
            kicad_modg.append(Line(start=[l_fab, c*pin_pitch-pin_width/2], end=[-posx_pin_length+pin_pitch/2, c*pin_pitch-pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[-posx_pin_length+pin_pitch/2, c*pin_pitch-pin_width/2], end=[-posx_pin_length+pin_pitch/2, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[-posx_pin_length+pin_pitch/2, c*pin_pitch+pin_width/2], end=[l_fab, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[l_fab + w_fab, c*pin_pitch-pin_width/2], end=[pin_pitch/2+posx_pin_length, c*pin_pitch-pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[pin_pitch/2+posx_pin_length, c*pin_pitch-pin_width/2], end=[pin_pitch/2+posx_pin_length, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))
            kicad_modg.append(Line(start=[pin_pitch/2+posx_pin_length, c*pin_pitch+pin_width/2], end=[l_fab + w_fab, c*pin_pitch+pin_width/2], layer='F.Fab', width=gc.fab_line_width))

    # create SILKSCREEN-layer + pin1 marker
    slk_offset_pad = pad.y/2 + silk_pad_offset
    kicad_modg.append(Line(start=[l_slk, t_slk], end=[l_slk + w_slk, t_slk], layer='F.SilkS', width=gc.silk_line_width))
    kicad_modg.append(Line(start=[l_slk, t_slk+h_slk], end=[l_slk + w_slk, t_slk+h_slk], layer='F.SilkS', width=gc.silk_line_width))

    if row_count == 1:
        for c in cleft:
            if c == 0:
                kicad_modg.append(Line(start=[l_slk , -slk_offset_pad], end=[-smd_pad_offset-pad.x/2+gc.silk_line_width/2 , -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk , t_slk], end=[l_slk, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk+w_slk, (pos_count-1)*pin_pitch+slk_offset_pad],end=[l_slk+w_slk, t_slk+h_slk],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk+w_slk, -slk_offset_pad], end=[l_slk+w_slk, min(t_slk+h_slk,(c+1) * pin_pitch - slk_offset_pad)], layer='F.SilkS', width=gc.silk_line_width))
            elif c == pos_count-1:
                kicad_modg.append(Line(start=[l_slk+w_slk, max(t_slk, (c-1) * pin_pitch + slk_offset_pad)], end=[l_slk+w_slk, t_slk+h_slk], layer='F.SilkS', width=gc.silk_line_width))
            else:
                kicad_modg.append(Line(start=[l_slk+w_slk, max(t_slk, (c-1) * pin_pitch + slk_offset_pad)], end=[l_slk+w_slk, min(t_slk+h_slk,(c+1) * pin_pitch - slk_offset_pad)], layer='F.SilkS', width=gc.silk_line_width))
        for c in cright:
            if c == 0:
                kicad_modg.append(Line(start=[l_slk+w_slk, -slk_offset_pad],end=[smd_pad_offset+pad.x/2-gc.silk_line_width/2, -slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk+w_slk, t_slk],end=[l_slk+w_slk, -slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk, (pos_count-1)*pin_pitch+slk_offset_pad],end=[l_slk, t_slk+h_slk],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk , -slk_offset_pad],end=[l_slk, min(t_slk+h_slk,(c+1) * pin_pitch - slk_offset_pad)], layer='F.SilkS',width=gc.silk_line_width))
            if c == pos_count-1:
                kicad_modg.append(Line(start=[l_slk , max(t_slk, (c-1) * pin_pitch + slk_offset_pad)],end=[l_slk, t_slk+h_slk], layer='F.SilkS',width=gc.silk_line_width))
            else:
                kicad_modg.append(Line(start=[l_slk , max(t_slk, (c-1) * pin_pitch + slk_offset_pad)],end=[l_slk, min(t_slk+h_slk,(c+1) * pin_pitch - slk_offset_pad)], layer='F.SilkS',width=gc.silk_line_width))
    if (row_count==2):
        if isSocket:
            # print(pad.x/2+smd_pad_offset,pad.x/2,smd_pad_offset)
            kicad_modg.append(Line(start=[pad.x/2+smd_pad_offset+row_pitch, -(pad.y / 2 + 2*gc.silk_line_width + gc.silk_fab_offset)], end=[l_slk+w_slk, -(pad.y / 2 + 2*gc.silk_line_width + gc.silk_fab_offset)], layer='F.SilkS', width=gc.silk_line_width))
        else:
            kicad_modg.append(Line(start=[-smd_pad_offset+pin_pitch/2-pad.x/2+gc.silk_line_width/2, -slk_offset_pad], end=[l_slk, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[l_slk , t_slk], end=[l_slk, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[l_slk+w_slk , t_slk], end=[l_slk+w_slk, -slk_offset_pad], layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[l_slk, (pos_count-1)*pin_pitch+slk_offset_pad],end=[l_slk, t_slk+h_slk],layer='F.SilkS', width=gc.silk_line_width))
            kicad_modg.append(Line(start=[l_slk+w_slk, (pos_count-1)*pin_pitch+slk_offset_pad],end=[l_slk+w_slk, t_slk+h_slk],layer='F.SilkS', width=gc.silk_line_width))
        if slk_offset_pad*2 < pin_pitch - gc.silk_line_width*2:
            for c in range(0,pos_count-1):
                kicad_modg.append(Line(start=[l_slk, c*pin_pitch+slk_offset_pad],end=[l_slk, (c+1)*pin_pitch-slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
                kicad_modg.append(Line(start=[l_slk+w_slk, c*pin_pitch+slk_offset_pad],end=[l_slk+w_slk, (c+1)*pin_pitch-slk_offset_pad],layer='F.SilkS', width=gc.silk_line_width))
    # create courtyard
    kicad_mod.append(Rectangle(start=[roundCrt(l_crt + offset.x), roundCrt(t_crt + offset.y)],
                              end=[roundCrt(l_crt + offset.x + w_crt), roundCrt(t_crt + offset.y + h_crt)],
                              layer='F.CrtYd', width=gc.courtyard_line_width))

    # create pads
    pad_type = Pad.TYPE_SMT
    pad_shape1 = Pad.SHAPE_RECT
    pad_layers = Pad.LAYERS_SMT

    if row_count == 1:
        for c in cleft:
            kicad_modg.append(Pad(number=c+1, type=pad_type, shape=pad_shape1, at=[-smd_pad_offset, c*pin_pitch], size=pad, drill=pins_drill,layers=pad_layers))
        for c in cright:
            kicad_modg.append(Pad(number=c+1, type=pad_type, shape=pad_shape1, at=[smd_pad_offset, c * pin_pitch], size=pad, drill=pins_drill,layers=pad_layers))
    elif row_count == 2:
        p = 1
        for c in range(0, pos_count):
            if isSocket:
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[pin_pitch/2+smd_pad_offset, c * pin_pitch], size=pad, drill=pins_drill,layers=pad_layers))
                p=p+1
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[-smd_pad_offset+pin_pitch/2, c * pin_pitch], size=pad, drill=pins_drill, layers=pad_layers))
                p=p+1
            else:
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[-smd_pad_offset+pin_pitch/2, c * pin_pitch], size=pad, drill=pins_drill, layers=pad_layers))
                p=p+1
                kicad_modg.append(Pad(number=p, type=pad_type, shape=pad_shape1, at=[smd_pad_offset+pin_pitch/2, c * pin_pitch], size=pad, drill=pins_drill,layers=pad_layers))
                p=p+1

    # add model
    kicad_modg.append(
        Model(
            filename=global_config.model_3d_prefix
            + lib_name
            + ".3dshapes/"
            + footprint_name
            + global_config.model_3d_suffix
        )
    )

    write_footprint(kicad_mod, lib_name, generator_name)
