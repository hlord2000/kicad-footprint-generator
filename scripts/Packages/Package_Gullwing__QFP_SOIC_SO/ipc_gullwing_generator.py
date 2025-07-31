#!/usr/bin/env python3

import os
import argparse
import yaml
from typing import List, Optional, Union, Literal

from KicadModTree import (
    ExposedPad,
    Footprint,
    FootprintType,
    ChamferRect,
    CornerSelection,
    PolygonLine,
)

from kilibs.geom import GeomRectangle
from kilibs.ipc_tools import ipc_rules
from kilibs.util.toleranced_size import TolerancedSize
from KicadModTree.util.courtyard_builder import CourtyardBuilder
from kilibs.geom import Direction, Vector2D
from KicadModTree.nodes.specialized.PadArray import (
    find_lowest_numbered_pad,
    get_pad_radius_from_arrays,
)
from KicadModTree.nodes.specialized.Cruciform import Cruciform

from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.footprint_text_fields import addTextFields
from scripts.tools.ipc_pad_size_calculators import ipc_gull_wing
from scripts.tools.quad_dual_pad_border import create_dual_or_quad_pad_border
from scripts.tools import drawing_tools
from scripts.tools.drawing_tools import nearestSilkPointOnOrthogonalLine
from scripts.tools.nodes import pin1_arrow

from scripts.tools.declarative_def_tools import (
    ast_evaluator,
    common_metadata,
    fp_additional_drawing,
    rule_area_properties,
)

from scripts.Packages.utils.ep_handling_utils import getEpRoundRadiusParams


DEFAULT_PASTE_COVERAGE = 0.65
DEFAULT_VIA_PASTE_CLEARANCE = 0.15
DEFAULT_MIN_ANNULAR_RING = 0.15


def roundToBase(value, base):
    return round(value / base) * base


class TopSlugConfiguration:
    """
    A type that represents the configuration of a "top slug"
    (top heat sink pad), probably from a YAML config block.
    """

    shape: str
    x: TolerancedSize
    y: TolerancedSize
    # Optional tail_x for rectangular slugs with vertical "tails" to the
    # package edge.
    tail_x: Optional[TolerancedSize]

    def __init__(self, spec: dict):

        self.shape = spec['shape']

        if self.shape not in ['rectangle', 'cruciform']:
            raise ValueError(f"Unsupported top slug shape: {self.shape}")

        self.x = TolerancedSize.fromYaml(spec, base_name='x')
        self.y = TolerancedSize.fromYaml(spec, base_name='y')

        self.tail_x = None

        if self.shape == 'cruciform':
            self.tail_x = TolerancedSize.fromYaml(spec, base_name='tail_x')

    def get_name_suffix(self):

        # See https://github.com/KiCad/kicad-footprints/issues/955 for discussion
        s = 'TopEP'

        if self.shape == 'rectangle' or self.shape == 'cruciform':
            s += f'{self.x.nominal:.2f}x{self.y.nominal:.2f}mm'
        else:
            raise ValueError(f"Unsupported top slug shape: {self.shape}")

        return s

class GullwingConfiguration:
    """
    A type that represents the configuration of a gullwing footprint
    (probably from a YAML config block).

    Over time, add more type-safe accessors to this class, and replace
    use of the raw dictionary.
    """

    _spec_dictionary: dict
    metadata: common_metadata.CommonMetadata
    rule_areas: List[rule_area_properties.RuleAreaProperties] = []

    lead_type: Union[Literal['gullwing', 'flat_lead']]
    pitch: float
    force_small_pitch_ipc_definition: bool
    ipc_density: ipc_rules.IpcDensity

    top_slug: Optional[TopSlugConfiguration]
    additional_drawings: list[fp_additional_drawing.FPAdditionalDrawing]

    def __init__(self, spec: dict):
        self._spec_dictionary = spec

        self.metadata = common_metadata.CommonMetadata(spec)

        self.top_slug = None
        if 'top_slug' in spec:
            self.top_slug = TopSlugConfiguration(spec['top_slug'])

        self.lead_type = spec.get('lead_type', 'gullwing')

        # only gullwing and flat are supported by this generator
        if self.lead_type not in ['gullwing', 'flat_lead']:
            raise ValueError(f"Unsupported lead type: {self.lead_type}")

        self.pitch = spec["pitch"]

        if self.pitch <= 0:
            raise ValueError(f"Pitch must be positive, got {self.pitch}")

        self.force_small_pitch_ipc_definition = spec.get(
            "force_small_pitch_ipc_definition", False
        )

        if self.force_small_pitch_ipc_definition and self.lead_type != "gullwing":
            raise ValueError(
                f"force_small_pitch_ipc_definition is not supported for lead type: {self.lead_type}"
            )

        self.ipc_density = ipc_rules.IpcDensity.from_str(spec.get('ipc_density', 'nominal'))

        self.additional_drawings = (
            fp_additional_drawing.FPAdditionalDrawing.from_standard_yaml(spec)
        )

        self.rule_areas = rule_area_properties.RuleAreaProperties.from_standard_yaml(spec)

    @property
    def spec_dictionary(self) -> dict:
        """
        Get the raw spec dictionary.

        This is only temporary, and can be piecewise replaced by
        type-safe declarative definitions, but that requires deep changes
        """
        return self._spec_dictionary

    @property
    def has_top_slug(self) -> bool:
        return self.top_slug is not None


class GullwingGenerator(FootprintGenerator):
    def __init__(self, configuration, ipc_defs: ipc_rules.IpcRules, **kwargs):

        super().__init__(**kwargs)

        self.configuration = configuration

        # For now, use the dict-base data
        self.ipc_definitions = ipc_defs

        self.configuration['min_ep_to_pad_clearance'] = ipc_defs.min_ep_to_pad_clearance

    def calcPadDetails(self, device_dimensions, overrides, ipc_offsets, ipc_round_base):
        # Z - Length (overall) of the land pattern
        # G - Inside length distance between lands of the pattern
        # L - Component Length (edge to edge of the gullwings)
        # S - Distance between the inside edges of the gullwings
        # JT - Solder fillet at toe
        # JH - Solder fillet at heel
        # JS - Solder fillet at side
        # CL - Component Length tolerance
        # F - Fabrication tolerance
        # P - Placement tolerance
        # X - Width (overall) of the land pattern
        # W - Width of a lead

        # Zmax = Lmin + 2JT + √(CL^2 + F^2 + P^2)
        # Gmin = Smax − 2JH − √(CS^2 + F^2 + P^2)
        # Xmax = Wmin + 2JS + √(CW^2 + F^2 + P^2)

        # Some manufacturers do not list the terminal spacing (S) in their datasheet but list the terminal length (T)
        # Then one can calculate
        # Stol(RMS) = √(Ltol^2 + 2*^2)
        # Smin = Lmin - 2*Tmax
        # Smax(RMS) = Smin + Stol(RMS)

        manf_tol = ipc_rules.ManufacturingTolerance(
            manufacturing_tolerance=self.configuration.get('manufacturing_tolerance', 0.1),
            placement_tolerance=self.configuration.get('placement_tolerance', 0.05),
        )

        Gmin_x, Zmax_x, Xmax = ipc_gull_wing(
            ipc_offsets, ipc_round_base, manf_tol,
            device_dimensions['lead_width'],
            device_dimensions['overall_size_x'],
            lead_len=device_dimensions.get('lead_len'),
            heel_reduction=device_dimensions.get('heel_reduction', 0)
        )

        Gmin_y, Zmax_y, Xmax_y_ignored = ipc_gull_wing(
            ipc_offsets, ipc_round_base, manf_tol,
            device_dimensions['lead_width'],
            device_dimensions['overall_size_y'],
            lead_len=device_dimensions.get('lead_len'),
            heel_reduction=device_dimensions.get('heel_reduction', 0)
        )

        min_ep_to_pad_clearance = configuration['min_ep_to_pad_clearance']

        heel_reduction_max = 0

        if Gmin_x - 2 * min_ep_to_pad_clearance < overrides['EP_x']:
            heel_reduction_max = ((overrides['EP_x'] + 2 * min_ep_to_pad_clearance - Gmin_x) / 2)
            # print('{}, {}, {}'.format(Gmin_x, overrides['EP_x'], min_ep_to_pad_clearance))
            Gmin_x = overrides['EP_x'] + 2 * min_ep_to_pad_clearance
        if Gmin_y - 2 * min_ep_to_pad_clearance < overrides['EP_y']:
            heel_reduction = ((overrides['EP_y'] + 2 * min_ep_to_pad_clearance - Gmin_y) / 2)
            if heel_reduction > heel_reduction_max:
                heel_reduction_max = heel_reduction
            Gmin_y = overrides['EP_y'] + 2 * min_ep_to_pad_clearance

        if overrides['pad_to_pad_min_x'] > 0:
            Gmin_x = overrides['pad_to_pad_min_x']
            Zmax_x = overrides['pad_to_pad_max_x']

        if overrides['pad_to_pad_min_y'] > 0:
            Gmin_y = overrides['pad_to_pad_min_y']
            Zmax_y = overrides['pad_to_pad_max_y']

        if overrides['pad_size_y'] > 0:
            Xmax = overrides['pad_size_y']

        Pad = {}
        Pad['left'] = {'center': [-(Zmax_x + Gmin_x) / 4.0, 0], 'size': [(Zmax_x - Gmin_x) / 2.0, Xmax]}
        Pad['right'] = {'center': [(Zmax_x + Gmin_x) / 4.0, 0], 'size': [(Zmax_x - Gmin_x) / 2.0, Xmax]}
        Pad['top'] = {'center': [0, -(Zmax_y + Gmin_y) / 4.0], 'size': [Xmax, (Zmax_y - Gmin_y) / 2.0]}
        Pad['bottom'] = {'center': [0, (Zmax_y + Gmin_y) / 4.0], 'size': [Xmax, (Zmax_y - Gmin_y) / 2.0]}

        return Pad

    @staticmethod
    def deviceDimensions(gullwing_config: GullwingConfiguration):
        # Pull out the old-style raw data
        device_size_data = gullwing_config.spec_dictionary

        dimensions = {
            'body_size_x': TolerancedSize.fromYaml(device_size_data, base_name='body_size_x'),
            'body_size_y': TolerancedSize.fromYaml(device_size_data, base_name='body_size_y'),
            'lead_width': TolerancedSize.fromYaml(device_size_data, base_name='lead_width'),
            'lead_len': TolerancedSize.fromYaml(device_size_data, base_name='lead_len')
        }
        dimensions['has_EP'] = False
        if ('EP_size_x_min' in device_size_data
                and 'EP_size_x_max' in device_size_data or 'EP_size_x' in device_size_data):
            dimensions['EP_size_x'] = TolerancedSize.fromYaml(device_size_data, base_name='EP_size_x')
            dimensions['EP_size_y'] = TolerancedSize.fromYaml(device_size_data, base_name='EP_size_y')
            dimensions['has_EP'] = True

        if 'EP_mask_x' in device_size_data:
            dimensions['EP_mask_x'] = TolerancedSize.fromYaml(device_size_data, base_name='EP_mask_x')
            dimensions['EP_mask_y'] = TolerancedSize.fromYaml(device_size_data, base_name='EP_mask_y')

        dimensions['heel_reduction'] = device_size_data.get('heel_reduction', 0)

        if 'overall_size_x' in device_size_data or 'overall_size_y' in device_size_data:
            if 'overall_size_x' in device_size_data:
                dimensions['overall_size_x'] = TolerancedSize.fromYaml(device_size_data, base_name='overall_size_x')
            else:
                dimensions['overall_size_x'] = TolerancedSize.fromYaml(device_size_data, base_name='overall_size_y')

            if 'overall_size_y' in device_size_data:
                dimensions['overall_size_y'] = TolerancedSize.fromYaml(device_size_data, base_name='overall_size_y')
            else:
                dimensions['overall_size_y'] = TolerancedSize.fromYaml(device_size_data, base_name='overall_size_x')
        else:
            raise KeyError("Either overall size x or overall size y must be given (Outside to outside lead dimensions)")

        return dimensions

    def generateFootprint(self, device_params: dict, pkg_id: str, header_info: dict):
        gullwing_config = GullwingConfiguration(device_params)

        dimensions = GullwingGenerator.deviceDimensions(gullwing_config)

        if 'deleted_pins' in device_params:
            if type(device_params['deleted_pins']) is int:
                device_params['deleted_pins'] = [device_params['deleted_pins']]

        if 'hidden_pins' in device_params:
            if type(device_params['hidden_pins']) is int:
                device_params['hidden_pins'] = [device_params['hidden_pins']]

        if 'deleted_pins' in device_params and 'hidden_pins' in device_params:
            raise ValueError("A footprint may not have deleted pins and hidden pins.")

        if dimensions['has_EP'] and 'thermal_vias' in device_params:
            self.__createFootprintVariant(gullwing_config, header_info, dimensions, True)

        self.__createFootprintVariant(gullwing_config, header_info, dimensions, False)

    def __createFootprintVariant(self, gullwing_config: GullwingConfiguration, header, dimensions, with_thermal_vias):
        fab_line_width = self.global_config.fab_line_width

        device_params = gullwing_config.spec_dictionary

        # The evaluator for complex expressions
        # Any useful variables can be injected into this object for use in expressions.
        fp_ast_evaluator = ast_evaluator.ASTevaluator()

        if 'override_lib_name' in header:
            lib_name = header['override_lib_name']
        else:
            lib_name = self.configuration['lib_name_format_string'].format(category=header['library_Suffix'])

        device_type = device_params.get('device_type', header['device_type'])

        size_x = dimensions['body_size_x'].nominal
        size_y = dimensions['body_size_y'].nominal

        pincount_full = device_params['num_pins_x'] * 2 + device_params['num_pins_y'] * 2

        if 'pin_count' in device_params:
            # If the pin count is explicitly given, we use that and don't adjust for hidden/deleted pins
            pincount_full = device_params['pin_count']
            pincount_text = '{}'.format(pincount_full)
            pincount = pincount_full
        elif 'hidden_pins' in device_params:
            pincount_text = '{}-{}'.format(pincount_full - len(device_params['hidden_pins']), pincount_full)
            pincount = pincount_full - len(device_params['hidden_pins'])
        elif 'deleted_pins' in device_params:
            pincount_text = '{}-{}'.format(pincount_full, pincount_full - len(device_params['deleted_pins']))
            pincount = pincount_full - len(device_params['deleted_pins'])
        else:
            pincount_text = '{}'.format(pincount_full)
            pincount = pincount_full

        if gullwing_config.lead_type == 'flat_lead':
            ipc_reference = 'ipc_spec_flat_lead'
        else:
            if gullwing_config.pitch < 0.625 or gullwing_config.force_small_pitch_ipc_definition:
                ipc_reference = 'ipc_spec_gw_small_pitch'
            else:
                ipc_reference = 'ipc_spec_gw_large_pitch'

        ipc_offsets = self.ipc_definitions.get_class(ipc_reference).get_offsets(gullwing_config.ipc_density)
        ipc_round_base = self.ipc_definitions.get_class(ipc_reference).roundoff

        pitch = gullwing_config.pitch

        name_format = self.configuration['fp_name_format_string_no_trailing_zero_pincount_text']
        EP_size = {'x': 0, 'y': 0}
        EP_mask_size = {'x': 0, 'y': 0}

        if dimensions['has_EP']:
            name_format = self.configuration['fp_name_EP_format_string_no_trailing_zero_pincount_text']
            if 'EP_size_x_overwrite' in device_params:
                EP_size = {
                    'x': device_params['EP_size_x_overwrite'],
                    'y': device_params['EP_size_y_overwrite']
                }
            else:
                EP_size = {
                    'x': dimensions['EP_size_x'].nominal,
                    'y': dimensions['EP_size_y'].nominal
                }
            if 'EP_mask_x' in dimensions:
                name_format = self.configuration['fp_name_EP_custom_mask_format_string_no_trailing_zero_pincount_text']
                EP_mask_size = {'x': dimensions['EP_mask_x'].nominal, 'y': dimensions['EP_mask_y'].nominal}

        overrides = {
            'EP_x': 0,
            'EP_y': 0,
            'pad_to_pad_min_x': 0,
            'pad_to_pad_max_x': 0,
            'pad_to_pad_min_y': 0,
            'pad_to_pad_max_y': 0,
            'pad_size_y': 0
        }

        if 'pad_size_y_overwrite' in device_params:
            overrides['pad_size_y'] = device_params['pad_size_y_overwrite']

        if 'pad_to_pad_min_x_overwrite' in device_params:
            overrides['pad_to_pad_min_x'] = device_params['pad_to_pad_min_x_overwrite']
            overrides['pad_to_pad_max_x'] = device_params['pad_to_pad_max_x_overwrite']

        if 'pad_to_pad_min_y_overwrite' in device_params:
            overrides['pad_to_pad_min_y'] = device_params['pad_to_pad_min_y_overwrite']
            overrides['pad_to_pad_max_y'] = device_params['pad_to_pad_max_y_overwrite']

        overrides['EP_x'] = EP_size['x']
        overrides['EP_y'] = EP_size['y']

        EP_size = Vector2D(EP_size)

        pad_details = self.calcPadDetails(dimensions, overrides, ipc_offsets, ipc_round_base)

        if gullwing_config.metadata.custom_name_format:
            name_format = gullwing_config.metadata.custom_name_format

        # This suffix is always added to the footprint name, as it is important for the 3D model
        always_suffix = ""

        if gullwing_config.has_top_slug:
            always_suffix = "_" + gullwing_config.top_slug.get_name_suffix()

        suffix = device_params.get('suffix', '').format(pad_x=pad_details['left']['size'][0],
                                                        pad_y=pad_details['left']['size'][1])

        if always_suffix:
            suffix = always_suffix + suffix

        suffix_3d = suffix if device_params.get('include_suffix_in_3dpath', 'True') == 'True' else always_suffix

        fp_name = name_format.format(
            man=gullwing_config.metadata.manufacturer or "",
            mpn=gullwing_config.metadata.part_number or "",
            pkg=device_type,
            pincount=pincount_text,
            size_y=size_y,
            size_x=size_x,
            pitch=device_params['pitch'],
            ep_size_x=EP_size['x'],
            ep_size_y=EP_size['y'],
            mask_size_x=EP_mask_size['x'],
            mask_size_y=EP_mask_size['y'],
            suffix=suffix,
            suffix2="",
            vias=self.configuration.get('thermal_via_suffix', '_ThermalVias') if with_thermal_vias else ''
        ).replace('__', '_').lstrip('_')

        fp_name_2 = name_format.format(
            man=gullwing_config.metadata.manufacturer or "",
            mpn=gullwing_config.metadata.part_number or "",
            pkg=device_type,
            pincount=pincount_text,
            size_y=size_y,
            size_x=size_x,
            pitch=device_params['pitch'],
            ep_size_x=EP_size['x'],
            ep_size_y=EP_size['y'],
            mask_size_x=EP_mask_size['x'],
            mask_size_y=EP_mask_size['y'],
            suffix=suffix_3d,
            suffix2="",
            vias=''
        ).replace('__', '_').lstrip('_')

        model_name = fp_name_2

        kicad_mod = Footprint(fp_name, FootprintType.SMD)

        if gullwing_config.metadata.description:
            # The part has a custom description
            description = gullwing_config.metadata.description
        else:
            description = "{manufacturer} {mpn} {package}, {pincount} Pin".format(
                manufacturer=gullwing_config.metadata.manufacturer or "",
                package=device_type,
                mpn=gullwing_config.metadata.part_number or "",
                pincount=pincount,
            ).lstrip()

        if gullwing_config.metadata.datasheet:
            description += f" ({gullwing_config.metadata.datasheet})"

        description += ", generated with kicad-footprint-generator {scriptname}".format(
            scriptname=os.path.basename(__file__)
        )

        kicad_mod.description = description

        kicad_mod.tags = self.configuration['keyword_fp_string'].format(
            man=gullwing_config.metadata.manufacturer or "",
            package=device_type,
            category=header['override_lib_name'] if 'override_lib_name' in header else header['library_Suffix']
        ).lstrip().split()

        kicad_mod.tags += gullwing_config.metadata.compatible_mpns
        kicad_mod.tags += gullwing_config.metadata.additional_tags

        pad_arrays = create_dual_or_quad_pad_border(self.global_config, pad_details, device_params)

        for pad_array in pad_arrays:
            kicad_mod.append(pad_array)

        tl_pad = find_lowest_numbered_pad(pad_arrays)
        pad_radius = get_pad_radius_from_arrays(pad_arrays)

        EP_round_radius = 0
        if dimensions['has_EP']:
            pad_shape_details = getEpRoundRadiusParams(device_params, self.global_config, pad_radius)
            EP_mask_size = EP_mask_size if EP_mask_size['x'] > 0 else None

            device_paste_pads = device_params.get('EP_num_paste_pads', 1)

            if with_thermal_vias:
                thermals = device_params['thermal_vias']
                paste_coverage = thermals.get('EP_paste_coverage',
                                              device_params.get('EP_paste_coverage', DEFAULT_PASTE_COVERAGE))

                # The paste_avoid_via function is pretty badly broken for smaller footprints
                # (the paste regions get too close by trying to even out area)
                #
                # See: https://gitlab.com/kicad/libraries/kicad-footprint-generator/-/issues/674
                #
                # In the interests of allowing these footprints to actually be regenerated
                # at all, we override YAML options here to disable it.
                #
                # When this function works again, reinstate this line.
                # And also decide if default-on is correct.
                paste_avoid_via = False  # thermals.get('paste_avoid_via', True)

                EP = ExposedPad(
                    number=pincount_full + 1, size=EP_size, mask_size=EP_mask_size,
                    paste_layout=thermals.get('EP_num_paste_pads', device_paste_pads),
                    paste_coverage=paste_coverage,
                    via_layout=thermals.get('count', 0),
                    paste_between_vias=thermals.get('paste_between_vias'),
                    paste_rings_outside=thermals.get('paste_rings_outside'),
                    via_drill=thermals.get('drill', 0.3),
                    via_grid=thermals.get('grid'),
                    remove_corner_vias=thermals.get('remove_corner_vias'),
                    paste_avoid_via=paste_avoid_via,
                    via_paste_clarance=thermals.get('paste_via_clearance', DEFAULT_VIA_PASTE_CLEARANCE),
                    min_annular_ring=thermals.get('min_annular_ring', DEFAULT_MIN_ANNULAR_RING),
                    bottom_pad_min_size=thermals.get('bottom_min_size', 0),
                    **pad_shape_details
                )
            else:
                EP = ExposedPad(
                    number=pincount_full + 1, size=EP_size, mask_size=EP_mask_size,
                    paste_layout=device_paste_pads,
                    paste_coverage=device_params.get('EP_paste_coverage', DEFAULT_PASTE_COVERAGE),
                    **pad_shape_details
                )

            kicad_mod.append(EP)
            EP_round_radius = EP.get_round_radius()

        # # ############################ CrtYd ##################################
        courtyard_offset = ipc_offsets.courtyard
        body_rect = GeomRectangle(center=Vector2D(0,0), size=Vector2D(size_x, size_y))
        cb = CourtyardBuilder.from_node(
            node=kicad_mod,
            global_config=self.global_config,
            offset_fab=courtyard_offset,
            outline=body_rect)
        kicad_mod += cb.node
        courtyard_bbox = cb.bbox

        # ############################ SilkS ##################################
        silk_pad_clearance = self.global_config.silk_pad_clearance
        silk_line_width = self.global_config.silk_line_width
        silk_pad_offset = silk_pad_clearance + (silk_line_width / 2)
        silk_offset = self.global_config.silk_fab_offset

        right_pads_silk_bottom = (device_params['num_pins_y'] - 1) * device_params['pitch'] / 2\
            + pad_details['right']['size'][1] / 2 + silk_pad_offset
        silk_bottom = body_rect.bottom + silk_offset
        if EP_size['y'] / 2 <= body_rect.bottom and right_pads_silk_bottom >= silk_bottom:
            silk_bottom = max(silk_bottom, EP_size['y'] / 2 + silk_pad_offset)

        silk_bottom = max(silk_bottom, right_pads_silk_bottom)
        silk_bottom = min(body_rect.bottom + silk_pad_offset, silk_bottom)

        bottom_pads_silk_right = (device_params['num_pins_x'] - 1) * device_params['pitch'] / 2\
            + pad_details['bottom']['size'][0] / 2 + silk_pad_offset
        silk_right = body_rect.right + silk_offset
        if EP_size['x'] / 2 <= body_rect.right and bottom_pads_silk_right >= silk_right:
            silk_right = max(silk_right, EP_size['x'] / 2 + silk_pad_offset)
        silk_right = max(silk_right, bottom_pads_silk_right)
        silk_right = min(body_rect.right + silk_pad_offset, silk_right)

        min_length = self.global_config.silk_line_length_min
        silk_corner_bottom_right = Vector2D(silk_right, silk_bottom)

        silk_point_bottom_inside = nearestSilkPointOnOrthogonalLine(
            pad_size=EP_size,
            pad_position=[0, 0],
            pad_radius=EP_round_radius,
            fixed_point=silk_corner_bottom_right,
            moving_point=Vector2D(0, silk_bottom),
            silk_pad_offset=silk_pad_offset,
            min_length=min_length)

        if silk_point_bottom_inside is not None and device_params['num_pins_x'] > 0:
            silk_point_bottom_inside = nearestSilkPointOnOrthogonalLine(
                pad_size=pad_details['bottom']['size'],
                pad_position=[
                    pad_details['bottom']['center'][0] + (device_params['num_pins_x'] - 1) / 2 * pitch,
                    pad_details['bottom']['center'][1]],
                pad_radius=pad_radius,
                fixed_point=silk_corner_bottom_right,
                moving_point=silk_point_bottom_inside,
                silk_pad_offset=silk_pad_offset,
                min_length=min_length)

        silk_point_right_inside = nearestSilkPointOnOrthogonalLine(
            pad_size=EP_size,
            pad_position=[0, 0],
            pad_radius=EP_round_radius,
            fixed_point=silk_corner_bottom_right,
            moving_point=Vector2D(silk_right, 0),
            silk_pad_offset=silk_pad_offset,
            min_length=min_length)
        if silk_point_right_inside is not None and device_params['num_pins_y'] > 0:
            silk_point_right_inside = nearestSilkPointOnOrthogonalLine(
                pad_size=pad_details['right']['size'],
                pad_position=[
                    pad_details['right']['center'][0],
                    pad_details['right']['center'][1] + (device_params['num_pins_y'] - 1) / 2 * pitch],
                pad_radius=pad_radius,
                fixed_point=silk_corner_bottom_right,
                moving_point=silk_point_right_inside,
                silk_pad_offset=silk_pad_offset,
                min_length=min_length)

        if silk_point_bottom_inside is None and silk_point_right_inside is not None:
            silk_corner_bottom_right['y'] = body_rect.bottom
            silk_corner_bottom_right = nearestSilkPointOnOrthogonalLine(
                pad_size=pad_details['bottom']['size'],
                pad_position=[
                    pad_details['bottom']['center'][0] + (device_params['num_pins_x'] - 1) / 2 * pitch,
                    pad_details['bottom']['center'][1]],
                pad_radius=pad_radius,
                fixed_point=silk_point_right_inside,
                moving_point=silk_corner_bottom_right,
                silk_pad_offset=silk_pad_offset,
                min_length=min_length)

        elif silk_point_right_inside is None and silk_point_bottom_inside is not None:
            silk_corner_bottom_right['x'] = body_rect.right
            silk_corner_bottom_right = nearestSilkPointOnOrthogonalLine(
                pad_size=pad_details['right']['size'],
                pad_position=[
                    pad_details['right']['center'][0],
                    pad_details['right']['center'][1] + (device_params['num_pins_y'] - 1) / 2 * pitch],
                pad_radius=pad_radius,
                fixed_point=silk_point_bottom_inside,
                moving_point=silk_corner_bottom_right,
                silk_pad_offset=silk_pad_offset,
                min_length=min_length)

        poly_bottom_right = []
        if silk_point_bottom_inside is not None:
            poly_bottom_right.append(silk_point_bottom_inside)
        poly_bottom_right.append(silk_corner_bottom_right)
        if silk_point_right_inside is not None:
            poly_bottom_right.append(silk_point_right_inside)

        is_qfp = device_params['num_pins_x'] > 0 and device_params['num_pins_y'] > 0

        body_size_min = min(
            dimensions['body_size_x'].nominal,
            dimensions['body_size_y'].nominal
        )

        if is_qfp:
            # Even the smallest QFPs have a large enough corner area
            # to fit a large arrow
            arrow_size_enum = drawing_tools.SilkArrowSize.LARGE
        else:
            # give large, non-fine-pitch parts a larger arrow
            if body_size_min < 6.0 or pitch < 1.0:
                arrow_size_enum = drawing_tools.SilkArrowSize.MEDIUM
            else:
                arrow_size_enum = drawing_tools.SilkArrowSize.LARGE

        arrow_size, arrow_length = drawing_tools.getStandardSilkArrowSize(
            arrow_size_enum, silk_line_width)

        # poly_bottom_right is used 4 times in all mirror configurations
        if len(poly_bottom_right) > 1 and silk_corner_bottom_right is not None:
            kicad_mod.append(PolygonLine(
                shape=poly_bottom_right,
                width=silk_line_width,
                layer="F.SilkS"))
            kicad_mod.append(PolygonLine(
                shape=poly_bottom_right,
                width=silk_line_width,
                layer="F.SilkS", x_mirror=0))
            kicad_mod.append(PolygonLine(
                shape=poly_bottom_right,
                width=silk_line_width,
                layer="F.SilkS", y_mirror=0))
            kicad_mod.append(PolygonLine(
                shape=poly_bottom_right,
                width=silk_line_width,
                layer="F.SilkS", y_mirror=0, x_mirror=0))

            # The edges of the pad clearance area
            tl_pad_with_clearance_top = tl_pad.at.y - tl_pad.size.y / 2 - silk_pad_clearance
            tl_pad_with_clearance_left = tl_pad.at.x - tl_pad.size.x / 2 - silk_pad_clearance

            # Allow a top-down arrow if there is enough space between the top pad and the courtyard
            # (it is allowed to overlap the courtyard by the courtyard offset, as a neigbouring part
            # with touching courtyards will nearly always have the same offset for itself, giving
            # our arrow a place. And the arrow is directional, so it's clear which part it belongs
            # to.)
            arrow_permitted_spill_over_top_courtyard = courtyard_offset
            minimum_space_to_fit_arrow = arrow_length + silk_line_width - arrow_permitted_spill_over_top_courtyard

            # we need a different arrow depending on the device orientation
            if device_params['num_pins_y'] > 0:
                # Pins on the left and right side

                pad_to_courtyard_corner_gap = tl_pad_with_clearance_top - courtyard_bbox.top
                tl_pad_left = tl_pad.at.x - tl_pad.size.x / 2

                # For parts like J-lead/SOJ, there may be no pad extending out past the body
                # so no left-right space to fit an arrow
                left_right_space = body_rect.left - tl_pad_left
                south_arrow_fits = left_right_space >= arrow_size

                if (south_arrow_fits and
                        (is_qfp or (pad_to_courtyard_corner_gap >= minimum_space_to_fit_arrow))):
                    # We can fit an arrow in the courtyard, or it's a QFN

                    pad_left_body_left_midpoint = (tl_pad_left + body_rect.left) / 2

                    # put a down arrow top of pin1
                    arrow_apex = Vector2D(pad_left_body_left_midpoint,
                                          tl_pad_with_clearance_top - silk_line_width / 2)
                    arrow_direction = Direction.SOUTH
                else:
                    # put a East arrow left of pin1
                    arrow_apex = Vector2D(tl_pad_with_clearance_left - silk_line_width / 2,
                                          tl_pad.at.y)
                    arrow_direction = Direction.EAST

                kicad_mod.append(
                    pin1_arrow.Pin1SilkscreenArrow(
                        arrow_apex,
                        arrow_direction,
                        arrow_size,
                        arrow_length,
                        "F.SilkS",
                        silk_line_width,
                    )
                )

            else:
                # Pins on the top and bottom side

                pad_to_courtyard_corner_gap = tl_pad_with_clearance_left - courtyard_bbox.left

                # J-lead type parts
                tl_pad_top = tl_pad.at.y - tl_pad.size.y / 2
                top_bottom_space = body_rect.top - tl_pad_top
                east_arrow_fits = top_bottom_space >= arrow_size

                if east_arrow_fits and pad_to_courtyard_corner_gap >= minimum_space_to_fit_arrow:
                    pad_top_body_top_midpoint = (tl_pad_top + body_rect.top) / 2

                    arrow_apex = Vector2D(tl_pad_with_clearance_left - silk_line_width / 2,
                                          pad_top_body_top_midpoint)
                    arrow_direction = Direction.EAST.value
                else:
                    # put a down arrow top of pin1
                    arrow_apex = Vector2D(tl_pad.at.x,
                                          tl_pad_with_clearance_top - silk_line_width / 2)
                    arrow_direction = Direction.SOUTH

                kicad_mod.append(
                    pin1_arrow.Pin1SilkscreenArrow(
                        arrow_apex,
                        arrow_direction,
                        arrow_size,
                        arrow_length,
                        "F.SilkS",
                        silk_line_width,
                    )
                )

        # # ######################## Fabrication Layer ###########################

        kicad_mod += ChamferRect(
                at=body_rect.center,
                size=body_rect.size,
                chamfer=self.global_config.fab_bevel,
                corners=CornerSelection({CornerSelection.TOP_LEFT: True}),
                layer="F.Fab",
                width=fab_line_width,
            )

        # ########################## Top heat slugs ###############################

        if gullwing_config.has_top_slug:

            if gullwing_config.top_slug.shape in ['rectangle', 'cruciform']:
                cruciform_w = gullwing_config.top_slug.x.nominal
                cruciform_tail_h = gullwing_config.top_slug.y.nominal

                # Default to a rectangle
                cruciform_h = cruciform_tail_h
                cruciform_tail_w = cruciform_w

                if gullwing_config.top_slug.shape == 'cruciform':
                    cruciform_tail_w = gullwing_config.top_slug.tail_x.nominal
                    # Tail to the top and bottom of the package
                    cruciform_h = body_rect.bottom - body_rect.top

                topslug_rect = Cruciform(
                    overall_w=cruciform_w,
                    overall_h=cruciform_h,
                    tail_w=cruciform_tail_w,
                    tail_h=cruciform_tail_h,
                    layer="Cmts.User",
                    width=0.1,
                    fill=False
                )

                kicad_mod.append(topslug_rect)
            else:
                raise ValueError("Unsupported top slug shape: {}".format(gullwing_config.top_slug.shape))

        # ######################### Rule Areas ################################

        zones = rule_area_properties.create_rule_area_zones(gullwing_config.rule_areas,
                                                            fp_ast_evaluator)
        for zone in zones:
            kicad_mod.append(zone)

        # ######################### Text Fields ###############################

        addTextFields(kicad_mod=kicad_mod, configuration=self.global_config,
                      body_edges=body_rect, courtyard=courtyard_bbox,
                      fp_name=fp_name, text_y_inside_position='center')

        # ######################### Additional drawings #######################

        if gullwing_config.additional_drawings:
            kicad_mod.extend(
                fp_additional_drawing.create_additional_drawings(
                    gullwing_config.additional_drawings,
                    self.global_config,
                    fp_ast_evaluator,
                )
            )

        # #################### Output and 3d model ############################

        self.add_standard_3d_model_to_footprint(kicad_mod, lib_name, model_name)

        self.write_footprint(kicad_mod, lib_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='use confing .yaml files to create footprints. See readme.md for details about the parameter '
                    'file format.')
    parser.add_argument('--series_config', type=str, nargs='?',
                        help='the config file defining series parameters.', default='../package_config_KLCv3.yaml')
    parser.add_argument('--density', type=str, nargs='?', help='IPC density level (L,N,M)', default='N')
    parser.add_argument('--ipc_doc', type=str, nargs='?', help='IPC definition document',
                        default='ipc_7351b')

    args = FootprintGenerator.add_standard_arguments(parser, file_autofind=True)

    if args.density == 'L':
        ipc_density = 'least'
    elif args.density == 'M':
        ipc_density = 'most'

    with open(args.series_config, 'r') as config_stream:
        try:
            configuration = yaml.safe_load(config_stream)
        except yaml.YAMLError as exc:
            print(exc)

    ipc_rule_defs = ipc_rules.IpcRules.from_file(args.ipc_doc)

    FootprintGenerator.run_on_files(
        GullwingGenerator,
        args,
        file_autofind_dir='size_definitions',
        configuration=configuration,
        ipc_defs=ipc_rule_defs,
    )
