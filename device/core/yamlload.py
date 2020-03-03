import importlib

from typing import Type, Dict, Any, Tuple


def field_from_yaml_def(yaml_def: Dict[str, Any]):
    dtype_name = yaml_def.pop('type')
    dtype = import_type(dtype_name)
    return dtype(**yaml_def)


def import_type(type_addr: str) -> Type:
    parts = type_addr.split('.')

    mod_name = '.'.join(parts[:-1])
    part_name = parts[-1]

    module = importlib.import_module(mod_name)
    return getattr(module, part_name)
