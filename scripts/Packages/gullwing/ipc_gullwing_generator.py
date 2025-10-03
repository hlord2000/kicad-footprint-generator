#!/usr/bin/env python3

import os
import argparse
import yaml
from typing import Any

from KicadModTree import (
    ExposedPad,
    Footprint,
    FootprintType,
)

from kilibs.ipc_tools import ipc_rules
from kilibs.geom import Vector2D
from KicadModTree.nodes.specialized.PadArray import get_pad_radius_from_arrays

from scripts.tools.nodes.layouts.dual_and_quad_pad_array_layout import DualAndQuadPadArrayLayout
from KicadModTree.nodes.specialized.Cruciform import Cruciform

from scripts.tools.footprint_generator import FootprintGenerator
from scripts.tools.ipc_pad_size_calculators import ipc_gull_wing
from scripts.tools.quad_dual_pad_border import create_dual_or_quad_pad_border

from scripts.tools.declarative_def_tools import (
    ast_evaluator,
    fp_additional_drawing,
    rule_area_properties,
)

from scripts.Packages.utils.ep_handling_utils import getEpRoundRadiusParams
from gullwing_configuration import GullwingConfiguration

DEFAULT_PASTE_COVERAGE = 0.65
DEFAULT_VIA_PASTE_CLEARANCE = 0.15
DEFAULT_MIN_ANNULAR_RING = 0.15

class GullwingGenerator(FootprintGenerator):
    def __init__(
        self,
        configuration: dict[str, Any],
        ipc_defs: ipc_rules.IpcRules,
        **kwargs: dict[str, Any]
    ) -> None:

        super().__init__(**kwargs)  # type: ignore

        self.configuration = configuration

        # For now, use the dict-base data
        self.ipc_definitions = ipc_defs

        self.configuration['min_ep_to_pad_clearance'] = ipc_defs.min_ep_to_pad_clearance

    def calc_pad_details(
        self,
        gwc: GullwingConfiguration,
        overrides: dict[str, float],
        ipc_offsets: ipc_rules.Offsets,
        ipc_round_base: ipc_rules.Roundoff
    ) -> dict[str, Any]:
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
            gwc.lead_width,
            gwc.overall_size_x,
            lead_len=gwc.lead_len,
            heel_reduction=gwc.heel_reduction
        )

        Gmin_y, Zmax_y, _ = ipc_gull_wing(
            ipc_offsets, ipc_round_base, manf_tol,
            gwc.lead_width,
            gwc.overall_size_y,
            lead_len=gwc.lead_len,
            heel_reduction=gwc.heel_reduction
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

        pad: dict[str, Any] = {}
        pad['left'] = {'center': [-(Zmax_x + Gmin_x) / 4.0, 0], 'size': [(Zmax_x - Gmin_x) / 2.0, Xmax]}
        pad['right'] = {'center': [(Zmax_x + Gmin_x) / 4.0, 0], 'size': [(Zmax_x - Gmin_x) / 2.0, Xmax]}
        pad['top'] = {'center': [0, -(Zmax_y + Gmin_y) / 4.0], 'size': [Xmax, (Zmax_y - Gmin_y) / 2.0]}
        pad['bottom'] = {'center': [0, (Zmax_y + Gmin_y) / 4.0], 'size': [Xmax, (Zmax_y - Gmin_y) / 2.0]}

        return pad

    def generateFootprint(
        self,
        device_params: dict[str, Any],
        pkg_id: str,
        header_info: dict[str, Any]
    ) -> None:
        gwc = GullwingConfiguration(device_params, header_info, pkg_id, self.configuration)

        if gwc.has_fp_data:
            if gwc.has_ep and 'thermal_vias' in device_params:
                self._createFootprintVariant(gwc, header_info, True)
            self._createFootprintVariant(gwc, header_info, False)

    def _createFootprintVariant(self, gwc: GullwingConfiguration, header: dict[str, Any], with_thermal_vias: bool) -> None:
        device_params = gwc.spec_dictionary
        # The evaluator for complex expressions
        # Any useful variables can be injected into this object for use in expressions.
        fp_ast_evaluator = ast_evaluator.ASTevaluator()

        if gwc.lead_type == 'flat_lead':
            ipc_reference = 'ipc_spec_flat_lead'
        else:
            if gwc.pitch < 0.625 or gwc.force_small_pitch_ipc_definition:
                ipc_reference = 'ipc_spec_gw_small_pitch'
            else:
                ipc_reference = 'ipc_spec_gw_large_pitch'

        ipc_offsets = self.ipc_definitions.get_class(ipc_reference).get_offsets(gwc.ipc_density)
        ipc_round_base = self.ipc_definitions.get_class(ipc_reference).roundoff

        if gwc.has_ep and 'EP_size_x_overwrite' in device_params:
            ep_size = Vector2D(
                device_params['EP_size_x_overwrite'],
                device_params['EP_size_y_overwrite']
            )
        else:
            ep_size = Vector2D(gwc.ep_size_x.nominal, gwc.ep_size_y.nominal)

        ep_mask_size = Vector2D(gwc.ep_mask_x.nominal, gwc.ep_mask_y.nominal)
        overrides = {
            'EP_x': 0.0,
            'EP_y': 0.0,
            'pad_to_pad_min_x': 0.0,
            'pad_to_pad_max_x': 0.0,
            'pad_to_pad_min_y': 0.0,
            'pad_to_pad_max_y': 0.0,
            'pad_size_y': 0.0
        }

        if 'pad_size_y_overwrite' in device_params:
            overrides['pad_size_y'] = device_params['pad_size_y_overwrite']

        if 'pad_to_pad_min_x_overwrite' in device_params:
            overrides['pad_to_pad_min_x'] = device_params['pad_to_pad_min_x_overwrite']
            overrides['pad_to_pad_max_x'] = device_params['pad_to_pad_max_x_overwrite']

        if 'pad_to_pad_min_y_overwrite' in device_params:
            overrides['pad_to_pad_min_y'] = device_params['pad_to_pad_min_y_overwrite']
            overrides['pad_to_pad_max_y'] = device_params['pad_to_pad_max_y_overwrite']

        overrides['EP_x'] = ep_size.x
        overrides['EP_y'] = ep_size.y

        pad_details = self.calc_pad_details(gwc, overrides, ipc_offsets, ipc_round_base)

        if with_thermal_vias:
            fp_name = gwc.fp_name_with_vias
        else:
            fp_name = gwc.fp_name_without_vias

        kicad_mod = Footprint(fp_name, FootprintType.SMD)

        if gwc.metadata.description:
            # The part has a custom description
            description = gwc.metadata.description
        else:
            description = "{manufacturer} {mpn} {package}, {pincount} Pin".format(
                manufacturer=gwc.metadata.manufacturer or "",
                package=gwc.device_type,
                mpn=gwc.metadata.part_number or "",
                pincount=gwc.pincount_real,
            ).lstrip()

        if gwc.metadata.datasheet:
            description += f" ({gwc.metadata.datasheet})"

        description += ", generated with kicad-footprint-generator {scriptname}".format(
            scriptname=os.path.basename(__file__)
        )

        kicad_mod.description = description

        kicad_mod.tags = self.configuration['keyword_fp_string'].format(
            man=gwc.metadata.manufacturer or "",
            package=gwc.device_type,
            category=header['override_lib_name'] if 'override_lib_name' in header else header['library_Suffix']
        ).lstrip().split()

        kicad_mod.tags += gwc.metadata.compatible_mpns
        kicad_mod.tags += gwc.metadata.additional_tags

        pad_arrays = create_dual_or_quad_pad_border(self.global_config, pad_details, device_params)
        pad_radius = get_pad_radius_from_arrays(pad_arrays)

        if gwc.has_ep:
            pad_shape_details = getEpRoundRadiusParams(device_params, self.global_config, pad_radius)  # type: ignore
            ep_mask_size = ep_mask_size if ep_mask_size.x > 0.0 else None

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

                exposed_pad = ExposedPad(
                    number=gwc.pincount_full + 1,
                    size=ep_size,
                    mask_size=ep_mask_size,
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
                    **pad_shape_details  # type: ignore
                )
            else:
                exposed_pad = ExposedPad(
                    number=gwc.pincount_full + 1,
                    size=ep_size,
                    mask_size=ep_mask_size,
                    paste_layout=device_paste_pads,
                    paste_coverage=device_params.get('EP_paste_coverage', DEFAULT_PASTE_COVERAGE),
                    **pad_shape_details  # type: ignore
                )
        else:
            exposed_pad = None

        # ########################## Top heat slugs ###############################

        if gwc.has_top_slug:

            if gwc.top_slug.shape in ['rectangle', 'cruciform']:
                cruciform_w = gwc.top_slug.x.nominal
                cruciform_tail_h = gwc.top_slug.y.nominal

                # Default to a rectangle
                cruciform_h = cruciform_tail_h
                cruciform_tail_w = cruciform_w

                if gwc.top_slug.shape == 'cruciform':
                    cruciform_tail_w = gwc.top_slug.tail_x.nominal
                    # Tail to the top and bottom of the package
                    cruciform_h = gwc.body_size_y.nominal

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
                raise ValueError("Unsupported top slug shape: {}".format(gwc.top_slug.shape))

        ###  Rule Areas  ###############################################################
        zones = rule_area_properties.create_rule_area_zones(
            gwc.rule_areas, fp_ast_evaluator
        )
        kicad_mod.extend(zones)

        ###  Additional Drawings  ######################################################
        if gwc.additional_drawings:
            kicad_mod.extend(
                fp_additional_drawing.create_additional_drawings(
                    gwc.additional_drawings,
                    self.global_config,
                    fp_ast_evaluator,
                )
            )

        ###  Layout  ###################################################################
        layout = DualAndQuadPadArrayLayout(
            global_config=self.global_config,
            courtyard_offset_body=ipc_offsets.courtyard,
            courtyard_offset_pads=ipc_offsets.courtyard,
            pad_arrays=pad_arrays,
            exposed_pad=exposed_pad,
            body_size=Vector2D.from_floats(gwc.body_size_x.nominal, gwc.body_size_y.nominal),
        )
        kicad_mod += layout

        ###  3D Model  #################################################################
        self.add_standard_3d_model_to_footprint(kicad_mod, gwc.lib_name, gwc.model_name)

        ###  Save Footprint  ###########################################################
        self.write_footprint(kicad_mod, gwc.lib_name)

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
        file_autofind_dir='../../../data/Gullwing/',
        configuration=configuration,
        ipc_defs=ipc_rule_defs,
    )
