#!/usr/bin/env python3

import os
import argparse
import logging
import yaml

from KicadModTree import (
    ExposedPad,
    Footprint,
    FootprintType,
)

from kilibs.geom import Vector2D
from kilibs.ipc_tools import ipc_rules
from kilibs.util.toleranced_size import TolerancedSize
from scripts.tools.nodes.layouts.dual_and_quad_pad_array_layout import DualAndQuadPadArrayLayout
from KicadModTree.nodes.specialized.PadArray import get_pad_radius_from_arrays

from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.ipc_pad_size_calculators import (
    ipc_body_edge_inside_pull_back,
    ipc_pad_center_plus_size,
)
from scripts.tools.quad_dual_pad_border import create_dual_or_quad_pad_border
from scripts.tools.declarative_def_tools import (
    ast_evaluator,
    common_metadata,
    pad_overrides,
    rule_area_properties,
)

from scripts.Packages.utils.ep_handling_utils import getEpRoundRadiusParams


ipc_density = 'nominal'
category = 'NoLead'
default_library = 'Package_DFN_QFN'

DEFAULT_PASTE_COVERAGE = 0.65
DEFAULT_VIA_PASTE_CLEARANCE = 0.15
DEFAULT_MIN_ANNULAR_RING = 0.15

SILK_MIN_LEN = 0.1


class NoLeadConfiguration:
    """
    A type that represents the configuration of a gullwing footprint
    (probably from a YAML config block).

    Over time, add more type-safe accessors to this class, and replace
    use of the raw dictionary.
    """
    _spec_dictionary: dict
    metadata: common_metadata.CommonMetadata
    pad_overrides: pad_overrides.PadOverrides
    rule_areas: list[rule_area_properties.RuleAreaProperties] = []

    def __init__(self, spec: dict):
        self._spec_dictionary = spec
        self.metadata = common_metadata.CommonMetadata(spec)

        self.pad_overrides = pad_overrides.PadOverrides(
            spec.get(pad_overrides.PAD_OVERRIDES_KEY, [])
        )

        self.rule_areas = rule_area_properties.RuleAreaProperties.from_standard_yaml(spec)

    @property
    def spec_dictionary(self) -> dict:
        return self._spec_dictionary


class NoLeadGenerator(FootprintGenerator):
    def __init__(self, configuration, ipc_defs: ipc_rules.IpcRules, **kwargs):
        super().__init__(**kwargs)

        self.configuration = configuration

        # for nwow, just use the dict-base data
        self.ipc_definitions = ipc_defs

        self.configuration['min_ep_to_pad_clearance'] = ipc_defs.min_ep_to_pad_clearance

    def calcPadDetails(
        self,
        device_dimensions,
        EP_size,
        ipc_offsets: ipc_rules.Offsets,
        ipc_round_base: ipc_rules.Roundoff,
    ):
        # Zmax = Lmin + 2JT + √(CL^2 + F^2 + P^2)
        # Gmin = Smax − 2JH − √(CS^2 + F^2 + P^2)
        # Xmax = Wmin + 2JS + √(CW^2 + F^2 + P^2)

        # Some manufacturers do not list the terminal spacing (S) in their datasheet but list the terminal length (T)
        # Then one can calculate
        # Stol(RMS) = √(Ltol^2 + 2*^2)
        # Smin = Lmin - 2*Tmax
        # Smax(RMS) = Smin + Stol(RMS)

        manf_tol = ipc_rules.ManufacturingTolerance(
            manufacturing_tolerance=self.configuration.get(
                "manufacturing_tolerance", 0.1
            ),
            placement_tolerance=self.configuration.get("placement_tolerance", 0.05),
        )

        pull_back_0 = TolerancedSize(nominal=0)
        pull_back = device_dimensions.get('lead_to_edge', pull_back_0)

        if 'lead_center_pos_x' in device_dimensions or 'lead_center_pos_y' in device_dimensions:
            Gmin_x, Zmax_x, Xmax_x = ipc_pad_center_plus_size(ipc_offsets, ipc_round_base, manf_tol,
                                                            center_position=device_dimensions.get(
                                                                'lead_center_pos_x', TolerancedSize(nominal=0)),
                                                            lead_length=device_dimensions.get('lead_len_H'),
                                                            lead_width=device_dimensions['lead_width_H'])

            Gmin_y, Zmax_y, Xmax_y = ipc_pad_center_plus_size(ipc_offsets, ipc_round_base, manf_tol,
                                                            center_position=device_dimensions.get(
                                                                'lead_center_pos_y', TolerancedSize(nominal=0)),
                                                            lead_length=device_dimensions.get('lead_len_V'),
                                                            lead_width=device_dimensions['lead_width_V'])
        else:
            Gmin_x, Zmax_x, Xmax_x = ipc_body_edge_inside_pull_back(
                ipc_offsets, ipc_round_base, manf_tol,
                body_size=device_dimensions['body_size_x'],
                lead_width=device_dimensions['lead_width_H'],
                lead_len=device_dimensions.get('lead_len_H'),
                body_to_inside_lead_edge=device_dimensions.get('body_to_inside_lead_edge'),
                heel_reduction=device_dimensions.get('heel_reduction', 0),
                pull_back=pull_back
            )

            Gmin_y, Zmax_y, Xmax_y = ipc_body_edge_inside_pull_back(
                ipc_offsets, ipc_round_base, manf_tol,
                body_size=device_dimensions['body_size_y'],
                lead_width=device_dimensions['lead_width_V'],
                lead_len=device_dimensions.get('lead_len_V'),
                body_to_inside_lead_edge=device_dimensions.get('body_to_inside_lead_edge'),
                heel_reduction=device_dimensions.get('heel_reduction', 0),
                pull_back=pull_back
            )

        min_ep_to_pad_clearance = self.configuration['min_ep_to_pad_clearance']

        heel_reduction_max = 0

        if EP_size['x'] > 0 and Gmin_x - 2 * min_ep_to_pad_clearance < EP_size['x']:
            heel_reduction_max = ((EP_size['x'] + 2 * min_ep_to_pad_clearance - Gmin_x) / 2)
            # print('{}, {}, {}'.format(Gmin_x, EP_size['x'], min_ep_to_pad_clearance))
            Gmin_x = EP_size['x'] + 2 * min_ep_to_pad_clearance
        if EP_size['y'] > 0 and Gmin_y - 2 * min_ep_to_pad_clearance < EP_size['y']:
            heel_reduction = ((EP_size['y'] + 2 * min_ep_to_pad_clearance - Gmin_y) / 2)
            if heel_reduction > heel_reduction_max:
                heel_reduction_max = heel_reduction
            Gmin_y = EP_size['y'] + 2 * min_ep_to_pad_clearance

        heel_reduction_max += device_dimensions.get('heel_reduction', 0)  # include legacy stuff
        if heel_reduction_max > 0:
            logging.info(f'Heel reduced by {heel_reduction_max:.4f} to reach minimum EP to pad clearances')

        pad = {}
        pad['left'] = {'center': [-(Zmax_x + Gmin_x) / 4, 0], 'size': [(Zmax_x - Gmin_x) / 2, Xmax_x]}
        pad['right'] = {'center': [(Zmax_x + Gmin_x) / 4, 0], 'size': [(Zmax_x - Gmin_x) / 2, Xmax_x]}
        pad['top'] = {'center': [0, -(Zmax_y + Gmin_y) / 4], 'size': [Xmax_y, (Zmax_y - Gmin_y) / 2]}
        pad['bottom'] = {'center': [0, (Zmax_y + Gmin_y) / 4], 'size': [Xmax_y, (Zmax_y - Gmin_y) / 2]}

        return pad

    @staticmethod
    def deviceDimensions(device_config: NoLeadConfiguration, fp_id: str) -> dict:
        # Pull out the old-style raw data
        device_size_data = device_config.spec_dictionary

        unit = device_size_data.get('unit')
        dimensions = {
            'body_size_x': TolerancedSize.fromYaml(device_size_data, base_name='body_size_x', unit=unit),
            'body_size_y': TolerancedSize.fromYaml(device_size_data, base_name='body_size_y', unit=unit)
        }

        if 'pitch_x' in device_size_data and 'pitch_y' in device_size_data:
            dimensions['pitch_x'] = TolerancedSize.fromYaml(device_size_data, base_name='pitch_x', unit=unit).nominal
            dimensions['pitch_y'] = TolerancedSize.fromYaml(device_size_data, base_name='pitch_y', unit=unit).nominal
        else:
            dimensions['pitch_x'] = TolerancedSize.fromYaml(device_size_data, base_name='pitch', unit=unit).nominal
            dimensions['pitch_y'] = dimensions['pitch_x']

        dimensions['has_EP'] = False
        if ('EP_size_x_min' in device_size_data and 'EP_size_x_max' in device_size_data
                or 'EP_size_x' in device_size_data):
            dimensions['EP_size_x'] = TolerancedSize.fromYaml(device_size_data, base_name='EP_size_x', unit=unit)
            dimensions['EP_size_y'] = TolerancedSize.fromYaml(device_size_data, base_name='EP_size_y', unit=unit)
            dimensions['has_EP'] = True
            dimensions['EP_center_x'] = TolerancedSize(nominal=0)
            dimensions['EP_center_y'] = TolerancedSize(nominal=0)
            if 'EP_center_x' in device_size_data and 'EP_center_y' in device_size_data:
                dimensions['EP_center_x'] = TolerancedSize.fromYaml(
                    device_size_data, base_name='EP_center_x', unit=unit)
                dimensions['EP_center_y'] = TolerancedSize.fromYaml(
                    device_size_data, base_name='EP_center_y', unit=unit)

        if 'heel_reduction' in device_size_data:
            print(
                "\033[1;35mThe use of manual heel reduction is deprecated. " +
                "It is automatically calculated from the minimum EP to pad clearance (ipc config file)\033[0m"
            )
            dimensions['heel_reduction'] = device_size_data.get('heel_reduction', 0)

        if 'lead_to_edge' in device_size_data:
            dimensions['lead_to_edge'] = TolerancedSize.fromYaml(device_size_data, base_name='lead_to_edge', unit=unit)

        if 'lead_center_pos_x' in device_size_data:
            dimensions['lead_center_pos_x'] = TolerancedSize.fromYaml(
                device_size_data, base_name='lead_center_pos_x', unit=unit)
        if 'lead_center_to_center_x' in device_size_data:
            dimensions['lead_center_pos_x'] = TolerancedSize.fromYaml(
                device_size_data, base_name='lead_center_to_center_x', unit=unit) / 2

        if 'lead_center_pos_y' in device_size_data:
            dimensions['lead_center_pos_y'] = TolerancedSize.fromYaml(
                device_size_data, base_name='lead_center_pos_y', unit=unit)
        if 'lead_center_to_center_y' in device_size_data:
            dimensions['lead_center_pos_y'] = TolerancedSize.fromYaml(
                device_size_data, base_name='lead_center_to_center_y', unit=unit) / 2

        if 'lead_width_H' in device_size_data and 'lead_width_V' in device_size_data:
            # Different lead widths on H and V sides
            dimensions['lead_width_H'] = TolerancedSize.fromYaml(device_size_data, base_name='lead_width_H', unit=unit)
            dimensions['lead_width_V'] = TolerancedSize.fromYaml(device_size_data, base_name='lead_width_V', unit=unit)
        else:
            # Same on all sizes (i.e. normal)
            dimensions['lead_width_H'] = TolerancedSize.fromYaml(device_size_data, base_name='lead_width', unit=unit)
            dimensions['lead_width_V'] = dimensions['lead_width_H']

        dimensions['lead_len_H'] = None
        dimensions['lead_len_V'] = None
        if 'lead_len_H' in device_size_data and 'lead_len_V' in device_size_data:
            # Different lead lengths on H and V sides
            dimensions['lead_len_H'] = TolerancedSize.fromYaml(device_size_data, base_name='lead_len_H', unit=unit)
            dimensions['lead_len_V'] = TolerancedSize.fromYaml(device_size_data, base_name='lead_len_V', unit=unit)
        elif 'lead_len' in device_size_data or (
                'lead_len_min' in device_size_data and 'lead_len_max' in device_size_data):
            dimensions['lead_len_H'] = TolerancedSize.fromYaml(device_size_data, base_name='lead_len', unit=unit)
            dimensions['lead_len_V'] = dimensions['lead_len_H']

        if 'body_to_inside_lead_edge' in device_size_data:
            dimensions['body_to_inside_lead_edge'] = TolerancedSize.fromYaml(
                device_size_data, base_name='body_to_inside_lead_edge', unit=unit)
        elif dimensions['lead_len_H'] is None:
            raise KeyError('{}: Either lead length or inside lead to edge dimension must be given.'.format(fp_id))
        if 'pad_width' in device_size_data:
            dimensions['pad_width'] = TolerancedSize.fromYaml(
                device_size_data, base_name='pad_width', unit=unit).nominal
        if 'pad_length' in device_size_data:
            dimensions['pad_length'] = TolerancedSize.fromYaml(
                device_size_data, base_name='pad_length', unit=unit).nominal
        if 'pad_center_to_center_x' in device_size_data:
            dimensions['pad_center_to_center_x'] = TolerancedSize.fromYaml(
                device_size_data, base_name='pad_center_to_center_x', unit=unit).nominal
        if 'pad_center_to_center_y' in device_size_data:
            dimensions['pad_center_to_center_y'] = TolerancedSize.fromYaml(
                device_size_data, base_name='pad_center_to_center_y', unit=unit).nominal
        return dimensions

    def generateFootprint(self, device_params: dict, pkg_id: str, header_info: dict = None):
        nolead_config = NoLeadConfiguration(device_params)

        device_dimensions = NoLeadGenerator.deviceDimensions(nolead_config, pkg_id)

        if 'deleted_pins' in device_params:
            if type(device_params['deleted_pins']) is int:
                device_params['deleted_pins'] = [device_params['deleted_pins']]

        if 'hidden_pins' in device_params:
            if type(device_params['hidden_pins']) is int:
                device_params['hidden_pins'] = [device_params['hidden_pins']]

        if 'deleted_pins' in device_params and 'hidden_pins' in device_params:
            raise ValueError("A footprint may not have deleted pins and hidden pins.")

        if device_dimensions['has_EP'] and 'thermal_vias' in device_params:
            self._createFootprintVariant(nolead_config, device_dimensions, True)
        self._createFootprintVariant(nolead_config, device_dimensions, False)

    def _createFootprintVariant(self, device_config: NoLeadConfiguration,
                                 device_dimensions, with_thermal_vias):
        # Pull out the old-style raw data
        device_params = device_config.spec_dictionary

        lib_name = device_params.get('library', default_library)

        # pincount = device_params['num_pins_x'] * 2 + device_params['num_pins_y'] * 2
        pincount_full = device_params['num_pins_x'] * 2 + device_params['num_pins_y'] * 2

        if 'pin_count' in device_params:
            # If the pin count is explicitly given, we use that and don't adjust for hidden/deleted pins
            pincount_full = device_params['pin_count']
            pincount_text = '{}'.format(pincount_full)
            pincount = pincount_full
        elif 'hidden_pins' in device_params and len(device_params['hidden_pins'])>0:
            pincount_text = '{}-{}'.format(pincount_full - len(device_params['hidden_pins']), pincount_full)
            pincount = pincount_full - len(device_params['hidden_pins'])
        elif 'deleted_pins' in device_params and len(device_params['deleted_pins'])>0:
            pincount_text = '{}-{}'.format(pincount_full, pincount_full - len(device_params['deleted_pins']))
            pincount = pincount_full - len(device_params['deleted_pins'])
        else:
            pincount_text = '{}'.format(pincount_full)
            pincount = pincount_full

        is_pull_back = 'lead_to_edge' in device_params

        default_ipc_config = 'qfn_pull_back' if is_pull_back else 'qfn'
        if device_params.get('ipc_class', default_ipc_config) == 'qfn_pull_back':
            ipc_reference = 'ipc_spec_flat_no_lead_pull_back'
        else:
            ipc_reference = 'ipc_spec_flat_no_lead'

        used_density = ipc_rules.IpcDensity(device_params.get('ipc_density', ipc_density))
        ipc_offsets = self.ipc_definitions.get_class(ipc_reference).get_offsets(used_density)
        ipc_round_base = self.ipc_definitions.get_class(ipc_reference).roundoff

        layout = ''
        if device_dimensions['has_EP']:
            # name_format = self.configuration['fp_name_EP_format_string_no_trailing_zero']
            name_format = self.configuration['fp_name_EP_format_string_no_trailing_zero_pincount_text']

            if 'EP_size_x_overwrite' in device_params:
                EP_size = Vector2D(
                    device_params['EP_size_x_overwrite'],
                    device_params['EP_size_y_overwrite']
                )
            else:
                EP_size = Vector2D(
                    device_dimensions['EP_size_x'].nominal,
                    device_dimensions['EP_size_y'].nominal
                )
            EP_center = Vector2D(
                device_dimensions['EP_center_x'].nominal,
                device_dimensions['EP_center_y'].nominal
            )
        else:
            # name_format = self.configuration['fp_name_format_string_no_trailing_zero']
            name_format = self.configuration['fp_name_format_string_no_trailing_zero_pincount_text']

            if device_params.get('use_name_format', 'QFN') == 'LGA':
                # name_format = self.configuration['fp_name_lga_format_string_no_trailing_zero']
                name_format = self.configuration['fp_name_lga_format_string_no_trailing_zero_pincount_text']

                if device_params['num_pins_x'] > 0 and device_params['num_pins_y'] > 0:
                    layout = self.configuration['lga_layout_border'].format(
                        nx=device_params['num_pins_x'], ny=device_params['num_pins_y'])

            EP_size = Vector2D(0, 0)

        if device_config.metadata.custom_name_format:
            name_format = device_config.metadata.custom_name_format

        if {"pad_width", "pad_length"}.issubset(device_dimensions.keys()):
            pad_pos_x = device_dimensions.get("pad_center_to_center_x", 0.0)/2
            pad_pos_y = device_dimensions.get("pad_center_to_center_y", 0.0)/2
            pad_length = device_dimensions["pad_length"]
            pad_width = device_dimensions["pad_width"]
            pad_details = {}
            pad_details['left'] = {
                'center': [-pad_pos_x, 0], 'size': [pad_length, pad_width]
            }
            pad_details['right'] = {
                'center': [pad_pos_x, 0], 'size': [pad_length, pad_width]
            }
            pad_details['top'] = {
                'center': [0, -pad_pos_y], 'size': [pad_width, pad_length]
            }
            pad_details['bottom'] = {
                'center': [0, pad_pos_y], 'size': [pad_width, pad_length]
            }
        else:
            pad_details = self.calcPadDetails(device_dimensions, EP_size, ipc_offsets, ipc_round_base)

        pad_suffix = '_Pad{pad_x:.2f}x{pad_y:.2f}mm'.format(pad_x=pad_details['left']['size'][0],
                                                            pad_y=pad_details['left']['size'][1])
        pad_suffix = '' if device_params.get('include_pad_size', 'none') not in ('fp_name_only', 'both') else pad_suffix
        pad_suffix_3d = '' if device_params.get('include_pad_size', 'none') not in ('both') else pad_suffix

        suffix = device_params.get('suffix', '')
        suffix_3d = suffix if device_params.get('include_suffix_in_3dpath', 'True') == 'True' else ""

        size_x = device_dimensions['body_size_x'].nominal
        size_y = device_dimensions['body_size_y'].nominal

        fp_ast_evaluator = ast_evaluator.ASTevaluator()

        fp_name = name_format.format(
            man=device_config.metadata.manufacturer or "",
            mpn=device_config.metadata.part_number or "",
            pkg=device_params['device_type'],
            pincount=pincount_text,
            size_y=size_y,
            size_x=size_x,
            pitch=device_dimensions['pitch_x'],
            layout=layout,
            ep_size_x=EP_size.x,
            ep_size_y=EP_size.y,
            suffix=pad_suffix,
            suffix2=suffix,
            vias=self.configuration.get('thermal_via_suffix', '_ThermalVias') if with_thermal_vias else ''
        ).replace('__', '_').lstrip('_')

        fp_name_2 = name_format.format(
            man=device_config.metadata.manufacturer or "",
            mpn=device_config.metadata.part_number or "",
            pkg=device_params['device_type'],
            pincount=pincount_text,
            size_y=size_y,
            size_x=size_x,
            pitch=device_dimensions['pitch_x'],
            layout=layout,
            ep_size_x=EP_size.x,
            ep_size_y=EP_size.y,
            suffix=pad_suffix_3d,
            suffix2=suffix_3d,
            vias=''
        ).replace('__', '_').lstrip('_')

        if 'fp_name_prefix' in device_params:
            prefix = device_params['fp_name_prefix']
            if not prefix.endswith('_'):
                prefix += '_'
            fp_name = prefix + fp_name
            fp_name_2 = prefix + fp_name_2

        model_name = fp_name_2

        kicad_mod = Footprint(fp_name, FootprintType.SMD)
        if "mask_margin" in device_params:
            kicad_mod.setMaskMargin(device_params["mask_margin"])
        if "paste_margin" in device_params:
            kicad_mod.setPasteMargin(device_params["paste_margin"])
        if "paste_ratio" in device_params:
            kicad_mod.setPasteMarginRatio(device_params["paste_ratio"])

        # init kicad footprint
        kicad_mod.setDescription(
            "{manufacturer} {mpn} {package}, {pincount} Pin ({datasheet}), "
            "generated with kicad-footprint-generator {scriptname}"
            .format(
                manufacturer=device_config.metadata.manufacturer or "",
                package=device_params['device_type'],
                mpn=device_config.metadata.part_number or "",
                pincount=pincount,
                datasheet=device_config.metadata.datasheet,
                scriptname=os.path.basename(__file__).replace("  ", " ")
            ).lstrip())

        kicad_mod.tags = self.configuration['keyword_fp_string'].format(
            man=device_config.metadata.manufacturer or "",
            package=device_params['device_type'],
            category=category
        ).lstrip().split()

        kicad_mod.tags += device_config.metadata.compatible_mpns
        kicad_mod.tags += device_config.metadata.additional_tags

        pad_arrays = create_dual_or_quad_pad_border(self.global_config, pad_details, device_params,
                                                    pad_overrides=device_config.pad_overrides)
        pad_radius = get_pad_radius_from_arrays(pad_arrays)

        if device_dimensions['has_EP']:
            pad_shape_details = getEpRoundRadiusParams(device_params, self.global_config, pad_radius)
            ep_pad_number = device_params.get('EP_pin_number', pincount_full + 1)
            if with_thermal_vias:
                thermals = device_params['thermal_vias']
                paste_coverage = thermals.get('EP_paste_coverage',
                                              device_params.get('EP_paste_coverage', DEFAULT_PASTE_COVERAGE))

                # Override the via avoid setting in the YAML to avoid broken paste
                # aperture spacing.
                # See the same reasoning in the gullwing generator for more background.
                # (https://gitlab.com/kicad/libraries/kicad-footprint-generator/-/issues/674)
                paste_via_avoid = False

                exposed_pad = ExposedPad(
                    number=ep_pad_number, size=EP_size,
                    at=EP_center,
                    paste_layout=thermals.get('EP_num_paste_pads', device_params.get('EP_num_paste_pads', 1)),
                    paste_coverage=paste_coverage,
                    via_layout=thermals.get('count', 0),
                    paste_between_vias=thermals.get('paste_between_vias'),
                    paste_rings_outside=thermals.get('paste_rings_outside'),
                    via_drill=thermals.get('drill', 0.3),
                    via_grid=thermals.get('grid'),
                    remove_corner_vias=thermals.get('remove_corner_vias'),
                    paste_avoid_via=paste_via_avoid,
                    via_paste_clarance=thermals.get('paste_via_clearance', DEFAULT_VIA_PASTE_CLEARANCE),
                    min_annular_ring=thermals.get('min_annular_ring', DEFAULT_MIN_ANNULAR_RING),
                    bottom_pad_min_size=thermals.get('bottom_min_size', 0),
                    **pad_shape_details
                )
            else:
                exposed_pad = ExposedPad(
                    number=ep_pad_number, size=EP_size,
                    at=EP_center,
                    paste_layout=device_params.get('EP_num_paste_pads', 1),
                    paste_coverage=device_params.get('EP_paste_coverage', DEFAULT_PASTE_COVERAGE),
                    **pad_shape_details
                )
        else:
            exposed_pad = None

        ###  Rule Areas  ###############################################################
        zones = rule_area_properties.create_rule_area_zones(
            device_config.rule_areas, fp_ast_evaluator
        )
        kicad_mod.extend(zones)

        ###  Layout  ###################################################################
        layout = DualAndQuadPadArrayLayout(
            global_config=self.global_config,
            courtyard_offset_body=ipc_offsets.courtyard,
            courtyard_offset_pads=ipc_offsets.courtyard,
            pad_arrays=pad_arrays,
            exposed_pad=exposed_pad,
            body_size=Vector2D.from_floats(size_x, size_y),
        )
        kicad_mod += layout

        ###  3D Model  #################################################################
        self.add_standard_3d_model_to_footprint(kicad_mod, lib_name, model_name)

        ###  Save Footprint  ###########################################################
        self.write_footprint(kicad_mod, lib_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='use confing .yaml files to create footprints.')
    parser.add_argument('files', metavar='file', type=str, nargs='*',
                        help='list of files holding information about what devices should be created.')
    parser.add_argument('--series_config', type=str, nargs='?',
                        help='the config file defining series parameters.', default='../package_config_KLCv3.yaml')
    parser.add_argument('--density', type=str, nargs='?', help='IPC density level (L,N,M)', default='N')
    parser.add_argument('--ipc_doc', type=str, nargs='?', help='IPC definition document',
                        default='ipc_7351b')

    args = FootprintGenerator.add_standard_arguments(parser)

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
        NoLeadGenerator,
        args,
        file_autofind_dir='size_definitions',
        configuration=configuration,
        ipc_defs=ipc_rule_defs,
    )
