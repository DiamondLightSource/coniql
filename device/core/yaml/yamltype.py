from pprint import pformat
from typing import Type, Dict

import yaml

from device.core.dicttypes import field_from_dict_def
from device.core.yaml.load import load_and_preprocess
from device.viewableasdict import ViewableAsDict


def yaml_load(yaml_path: str, **kwargs):
    """Shortcut to creating and instantiating a YAML type. Good for the root of
    a device tree if the type only needs to be used once."""
    return yaml_type(yaml_path)(**kwargs)


def yaml_type(yaml_path: str) -> Type:
    """Dynamically constructs a new type from a YAML definition, creates a
    constructor which takes any variables in the file using the $(<var name>)
    syntax as keyword arguments."""

    text = load_and_preprocess(yaml_path)

    def make_raw_structure(**kwargs):
        """Replaces the variables according to kwargs and returns a new
        dictionary representing the YAML."""
        to_parse = replace_substitutions(text, kwargs)
        return yaml.load(to_parse)

    def make_args(**kwargs):
        """Turns the top-level elements of the dictionary into objects via the
        following rule:
        ['type'] is assumed to be the address of the type within the Python
        path. All other key value pairs are given as keyword arguments to the
        constructor."""
        raw_structure = make_raw_structure(**kwargs)
        fields = {
            name: field_from_dict_def(yaml_def)
            for name, yaml_def in raw_structure.items()
        }
        return fields

    class YamlType:
        """Dynamic type just for this file. TODO: Rename it to the file name."""

        def __init__(self, **kwargs):
            args = make_args(**kwargs)
            self.__dict__.update(**args)

        def __str__(self):
            return pformat(self.dict_view())

        def dict_view(self):
            view = {}
            for k, v in self.__dict__.items():
                if isinstance(v, ViewableAsDict):
                    view[k] = v.dict_view()
                else:
                    view[k] = type(v).__name__
            return view

    return YamlType


def replace_substitutions(value: str, substitutions: Dict[str, str]) -> str:
    """Replaces variables using the $(<var name>) syntax according to the
    mapping provided."""
    for s in substitutions:
        value = value.replace("$(%s)" % s, str(substitutions[s]))
    return value
