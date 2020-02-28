from typing import Type, Dict, Any

import yaml

_DATATYPES: Dict[str, Type] = {}


def load_device(yaml_path: str):
    raw_structure = load_raw_devive(yaml_path)
    fields = {
        name: field_from_yaml_def(yaml_def)
        for name, yaml_def in raw_structure.items()
    }

    class Device:
        def __str__(self):
            from pprint import pformat
            return pformat(self.__dict__)

    device = Device()
    device.__dict__.update(**fields)
    return device


def load_raw_devive(yaml_path: str) -> Dict[str, Any]:
    with open(yaml_path, 'r') as file:
        raw_structure = yaml.load(file, Loader=yaml.Loader)
        return raw_structure


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


def tryout():
    from device.channel.ca.channel import CaChannel
    from device.channel.ca.bool import CaBool
    register_datatype(CaChannel, 'CaFloat')
    register_datatype(CaBool, 'CaBool')

    path = 'device/motor/epicsmotor.yaml'
    device = load_device(path)
    print(device)
tryout()