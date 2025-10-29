import os

import cadquery as cq

from _tools import cq_color_correct, cq_globals, export_tools, parameters, shaderColors
from exportVRML.export_part_to_VRML import export_VRML

from .model_module import generate_part

__title__ = "main generator for [your model name here] model generators"
__author__ = "scripts: [author name(s)]; models: see cq_model files;"
__Comment__ = """[Description of this generator]"""

___ver___ = "2.0.0"


generator_directory = "Example"


def make_models(model_to_build=None, output_dir_prefix=None, enable_vrml=True):
    """
    Main entry point into this generator.
    """
    models = []

    # TODO: Update example to be the name of your library (variable above)
    all_params = parameters.load_parameters(generator_directory)

    if all_params == None:
        print("ERROR: Model parameters must be provided.")
        return

    # Handle the case where no model has been passed
    if model_to_build is None:
        print("No variant name is given! building: {0}".format(model_to_build))

        model_to_build = all_params.keys()[0]

    # Handle being able to generate all models or just one
    if model_to_build == "all":
        models = all_params
    else:
        models = {model_to_build: all_params[model_to_build]}

    # Step through the selected models
    for model in models:
        if output_dir_prefix == None:
            print("ERROR: An output directory must be provided.")
            return
        else:
            # Construct the final output directory
            output_dir = os.path.join(
                output_dir_prefix, all_params[model]["destination_dir"]
            )

        # Safety check to make sure the selected model is valid
        if not model in all_params.keys():
            print("Parameters for %s doesn't exist in 'all_params', skipping." % model)
            continue

        # TODO: Load the appropriate colors from the generator's configuration file
        body_color = shaderColors.named_colors[
            all_params[model]["body_color_key"]
        ].getDiffuseFloat()
        pins_color = shaderColors.named_colors[
            all_params[model]["pins_color_key"]
        ].getDiffuseFloat()

        # Used to wrap all the parts into an assembly
        component = cq.Assembly()

        body, leads = generate_part(all_params[model])

        # Translation and rotation of the parts, if needed
        body = body.translate(all_params[model]["translation"]).rotate(
            (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
        )
        leads = leads.translate(all_params[model]["translation"]).rotate(
            (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
        )

        # Wrap the component parts in an assembly so that we can attach colors
        component.add(
            body,
            color=cq_color_correct.Color(body_color[0], body_color[1], body_color[2]),
        )
        component.add(
            leads,
            color=cq_color_correct.Color(pins_color[0], pins_color[1], pins_color[2]),
        )

        # Export the assembly to STEP
        component.name = model
        export_tools.export_step(component, output_dir, model)

        # Export the assembly to VRML
        if enable_vrml:
            export_VRML(
                os.path.join(output_dir, model + ".wrl"),
                [body, leads],
                [
                    all_params[model]["body_color_key"],
                    all_params[model]["pins_color_key"],
                ],
            )
