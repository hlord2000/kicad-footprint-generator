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

# Run this script from the root of the repository with the venv activated and optional output_dir:
# Unix:            ./scripts/Pin-Headers_Socket-Strips/pin_headers_gen.py --output-dir ../footprints/
# Powershell:     python .\scripts\Pin-Headers_Socket-Strips\pin_headers_gen.py --output-dir ..\footprints\

# check README.md in repository root for installing venv
# on windows powershell: (deactivate script does not always work)
# .\venv\Scripts\Activate.ps1
# & {. .\venv\Scripts\Activate.ps1; deactivate}

from .spec import FPconfiguration #, makePinHeadOrSocket
from .def_makeIdcHeader import makeIdcHeader
from .def_makePinHeadStraight import makePinHeadStraight
from .def_makePinHeadAngled import makePinHeadAngled
from .def_makePinHeadStraightSMD import makePinHeadStraightSMD


def create_footprints(spec: FPconfiguration, generator_name: str) -> int:
    """Create the footprint(s) corresponding to the spec.

    Args:
        spec: the gullwing specification.

    Returns:
        The number of footprints generated.
    """
    num_fps_generated = 0
    if spec.type == "pin_headers":
        for pos_count in spec.pos_range:
            spec.pos_count = pos_count

            # for latch_length in (spec.latch_length_range if spec.latch_length_range is not None else [spec.latch_length]):
            #     spec.latch_length = latch_length
            #     if (spec.mount_type == "THT"):
            #         makeIdcHeader(spec, generator_name)
            #         num_fps_generated += 1
            #     elif (spec.mount_type == "SMD" and spec.orientation == "Vertical"):
            #         makeIdcHeader(spec, generator_name)
            #         num_fps_generated += 1
            #     else:
            #         raise ValueError(
            #             f"Unsupported mount/orientation combination: {spec.mount_type}"
            #             f"/{spec.orientation}"
            #         )
            if spec.mount_type == "THT" and spec.orientation == "Vertical":
                makePinHeadStraight(spec, generator_name)
                num_fps_generated += 1
            elif spec.mount_type =="THT" and spec.orientation == "Horizontal":
                makePinHeadAngled(spec, generator_name)
                num_fps_generated += 1
            elif spec.mount_type == "SMD" and spec.orientation == "Vertical":
                makePinHeadStraightSMD(spec, generator_name)
                num_fps_generated += 1
            else:
                raise ValueError(
                    f"Unsupported mount/orientation combination: {spec.mount_type}/"
                    f"{spec.orientation}"
                )

    elif spec.type == "idc_headers":                
        for pos_count in spec.pos_range:
            spec.pos_count = pos_count
            #print(spec.pos_range, spec.pos_count)
            
            for latch_length in (spec.latch_length_range if spec.latch_length_range is not None else [spec.latch_length]):
                spec.latch_length = latch_length
                if (spec.mount_type == "THT"):
                    makeIdcHeader(spec, generator_name)
                    num_fps_generated += 1
                elif (spec.mount_type == "SMD" and spec.orientation == "Vertical"):
                    makeIdcHeader(spec, generator_name)
                    num_fps_generated += 1
                else:
                    raise ValueError(
                        f"Unsupported mount/orientation combination: {spec.mount_type}/{spec.orientation}"
                    )

    return num_fps_generated
