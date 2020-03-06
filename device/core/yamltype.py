from functools import reduce
from pprint import pformat
from re import Match
from typing import Type, Dict, Any

import re
import yaml

from device.core.dicttypes import field_from_dict_def
from device.viewableasdict import ViewableAsDict


def yaml_load(yaml_path: str, **kwargs):
    return yaml_type(yaml_path)(**kwargs)


INCLUDE_REGEX = '#include (.*)\n'


def load_and_preprocess(yaml_path: str) -> str:
    text = read_file(yaml_path)
    return re.sub(INCLUDE_REGEX, include_match, text)


def include_match(match: Match):
    return load_and_preprocess(match.group(1))


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


def concat_files(*paths: str):
    return reduce(lambda x, y: x + y, map(read_file, paths))


def read_file(file_path: str) -> str:
    with open(file_path, 'r') as f:
        return f.read()


def replace_substitutions_dct(dct: Dict[str, Any],
                              substitutions: Dict[str, str]) -> Dict[str, Any]:
    return {k: replace_substitutions(v, substitutions) for k, v in dct.items()}


def replace_substitutions(value: str, substitutions: Dict[str, str]) -> str:
    for s in substitutions:
        value = value.replace("$(%s)" % s, str(substitutions[s]))
    return value
