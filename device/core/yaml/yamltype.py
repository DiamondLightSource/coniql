from pprint import pformat
from typing import Type, Dict

import yaml

from device.core.dicttypes import field_from_dict_def
from device.core.yaml.load import load_and_preprocess
from device.viewableasdict import ViewableAsDict


def yaml_load(yaml_path: str, **kwargs):
    return yaml_type(yaml_path)(**kwargs)


def yaml_type(yaml_path: str) -> Type:
    text = load_and_preprocess(yaml_path)

    def make_raw_structure(**kwargs):
        to_parse = replace_substitutions(text, kwargs)
        return yaml.load(to_parse)

    def make_args(**kwargs):
        raw_structure = make_raw_structure(**kwargs)
        fields = {
            name: field_from_dict_def(yaml_def)
            for name, yaml_def in raw_structure.items()
        }
        return fields

    class YamlType:
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
    for s in substitutions:
        value = value.replace("$(%s)" % s, str(substitutions[s]))
    return value
