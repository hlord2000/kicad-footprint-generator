import os
import sys

import cadquery as cq

from _tools.stepreduce import stepreduce

skip_list = []

_exit_process_after_first_part = False


def make_only_one_part_per_process() -> None:
    global _exit_process_after_first_part
    _exit_process_after_first_part = True


def export_step(
    component: cq.Assembly, output_dir: str, model: str, fused: bool = True
) -> None:
    # Setting this to True might help in faster development cycle as the step files generate more quickly
    QUICK_STEP_GENERATE = False

    # Create the output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not fused or QUICK_STEP_GENERATE:
        mode = cq.exporters.assembly.ExportModes.DEFAULT
    else:
        mode = cq.exporters.assembly.ExportModes.FUSED

    if not hasattr(component, "export"):
        # for backward compatibility with CadQuery < 2.5.0
        component.export = component.save

    # Export the assembly to STEP
    component.export(
        os.path.join(output_dir, model + ".step"),
        cq.exporters.ExportTypes.STEP,
        mode=mode,
        write_pcurves=False,
    )

    # Don't improve the step files any further in the quick mode
    if QUICK_STEP_GENERATE:
        return

    # Check for a proper union
    if fused:
        check_step_export_union(component, output_dir, model)

    # Do STEP post-processing
    postprocess_step(component, output_dir, model)

    # Update the license
    from _tools import add_license  # type: ignore

    add_license.addLicenseToStep(  # type: ignore
        output_dir,
        model + ".step",
        add_license.LIST_int_license,
        add_license.STR_int_licAuthor,
        add_license.STR_int_licEmail,
        add_license.STR_int_licOrgSys,
        add_license.STR_int_licPreProc,
    )

    if _exit_process_after_first_part:
        sys.exit(0)


def check_step_export_union(
    component: cq.Assembly, output_dir: str, model: str
) -> None:
    # Skip models that cannot be unioned properly
    if model in skip_list:
        return

    # Path to the STEP file to be validated
    cur_path = os.path.join(output_dir, model + ".step")

    # Import the STEP that was exported so that the number of solids can be checked
    union = cq.importers.importStep(cur_path)

    # Our starting tolerance
    tol = 0.001

    # Try multiple fuzzy tolerance values to try to fix
    while union.solids().size() != 1:
        component.save(
            cur_path,
            cq.exporters.ExportTypes.STEP,
            mode=cq.exporters.assembly.ExportModes.FUSED,
            assembly_name=model,
            write_pcurves=False,
            fuzzy_tol=tol,
        )

        # Make the fuse gradually less precise
        tol = tol / 0.5
        print(tol)

        # Escape clause
        if tol > 0.001:
            break

    assert union.solids().size() == 1


def postprocess_step(component: cq.Assembly, output_dir: str, model: str) -> None:
    # Path to the STEP file
    cur_path = os.path.join(output_dir, model + ".step")

    # The stepreduce algorithm seems stable, so disable verification by default
    verify = False

    if verify:
        orig_cmp = cq.Assembly(cq.importers.importStep(cur_path)).toCompound()
        stepreduce(cur_path, cur_path)
        reduced_cmp = cq.Assembly(cq.importers.importStep(cur_path)).toCompound()

        # Check volumes
        orig_volume = orig_cmp.Volume()
        reduced_volume = reduced_cmp.Volume()
        assert (
            orig_volume == reduced_volume
        ), f"Volume mismatch: {orig_volume} != {reduced_volume}"

        # Check center of mass
        orig_center_of_mass = orig_cmp.Center()
        reduced_center_of_mass = reduced_cmp.Center()
        assert (
            orig_center_of_mass == reduced_center_of_mass
        ), f"Center of mass mismatch: {orig_center_of_mass} != {reduced_center_of_mass}"
    else:
        stepreduce(cur_path, cur_path)
