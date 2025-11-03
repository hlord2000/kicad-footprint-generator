import cadquery as cq

from _tools import export_tools, parameters

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

        # Safety check to make sure the selected model is valid
        if not model in all_params.keys():
            print("Parameters for %s doesn't exist in 'all_params', skipping." % model)
            continue

        body, leads = generate_part(all_params[model])

        # Translation and rotation of the parts, if needed
        body = body.translate(all_params[model]["translation"]).rotate(
            (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
        )
        leads = leads.translate(all_params[model]["translation"]).rotate(
            (0, 0, 0), (0, 0, 1), all_params[model]["rotation"]
        )

        parts: list[cq.Workplane] = [body, leads]
        color_names: list[str] = [
            all_params[model]["body_color_key"],
            all_params[model]["pins_color_key"],
        ]
        export_tools.export(
            root_output_dir=output_dir_prefix,
            lib_name=generator_directory,
            model_name=model,
            parts=parts,
            color_names=color_names,
            export_as_vrml=enable_vrml,
        )
