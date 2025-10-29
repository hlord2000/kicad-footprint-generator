#!/usr/bin/env python3

from KicadModTree.nodes.base.Pad import Pad
from KicadModTree.util import corner_handling
from scripts.tools.global_config_files.global_config import GlobalConfig


def getEpRoundRadiusParams(
    device_params: dict, global_config: GlobalConfig, pad_radius: float
) -> dict:
    """
    Construct some parameters for the ExposedPad construction, based on device configs and
    global config.
    """

    pad_shape_details = {}

    pad_shape_details['paste_radius_handler'] = global_config.paste_roundrect_radius_handler

    round_radius_params = {}

    if 'EP_round_radius' in device_params:
        if type(device_params['EP_round_radius']) in [float, int]:
            round_radius_params['round_radius_exact'] = device_params['EP_round_radius']
        elif device_params['EP_round_radius'] == "pad":
            round_radius_params['round_radius_exact'] = pad_radius
        else:
            raise TypeError(
                    "round radius must be a number or 'pad', is {}"
                    .format(type(device_params['EP_round_radius']))
                    )
    elif 'EP_round_radius_ratio' in device_params:
        round_radius_params['radius_ratio'] = device_params['EP_round_radius_ratio']
    else:
        round_radius_params['radius_ratio'] = global_config.ep_roundrect_radius_handler.radius_ratio

    if 'radius_ratio' in round_radius_params and round_radius_params['radius_ratio'] > 0:
        if 'EP_maximum_radius' in device_params:
            round_radius_params['maximum_radius'] = device_params['EP_maximum_radius']
        else:
            round_radius_params['maximum_radius'] = global_config.ep_roundrect_radius_handler.maximum_radius

    pad_shape_details['round_radius_handler'] = corner_handling.RoundRadiusHandler(**round_radius_params)

    return pad_shape_details
