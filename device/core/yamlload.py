import importlib

from typing import Type, Dict, Any, Tuple


def field_from_dict_def(dict_def: Dict[str, Any]):
    """Creates an object based on a dictionary definition of the following
    format:{
        'type': <Full address of the constructor of object
                 e.g. device.pmac.Pmac>
        **kwargs <Keyword arguments for the type's constructor>
    }"""
    dtype = type_from_dict_def(dict_def)
    return dtype(**dict_def)


def type_from_dict_def(dict_def: Dict[str, Any]) -> Type:
    """Resolves the type from the a dictionary definition and removes it"""
    return import_type(dict_def.pop('type'))


def import_type(type_addr: str) -> Type:
    """Dynamically imports a type via its module address
    (e.g. module.inner_module.SomeClass) and returns it."""
    parts = type_addr.split('.')

    mod_name = '.'.join(parts[:-1])
    part_name = parts[-1]

    module = importlib.import_module(mod_name)
    return getattr(module, part_name)
