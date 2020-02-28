from typing import Type, Dict, Any

import yaml

_DATATYPES: Dict[str, Type] = {}


def field_from_yaml_def(yaml_def: Dict[str, Any]):
    dtype_name = yaml_def.pop('type')
    dtype = _DATATYPES[dtype_name]
    return dtype(**yaml_def)


def register_as_datatype(dtype: Type):
    return register_datatype(dtype, dtype.__name__)


def register_datatype(dtype: Type, name: str):
    assert name not in _DATATYPES, \
        f'{name} is already registered as {_DATATYPES[name]}'
    _DATATYPES[name] = dtype
