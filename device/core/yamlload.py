import importlib

from typing import Type, Dict, Any, Tuple


def field_from_yaml_def(yaml_def: Dict[str, Any]):
    dtype_name = yaml_def.pop('type')
    dtype = import_type(dtype_name)
    return dtype(**yaml_def)


def import_type(type_addr: str) -> Type:
    parts = type_addr.split('.')
    module = importlib.import_module(parts[0])
    for part in parts[1:]:
        module = getattr(module, part)
    return module
