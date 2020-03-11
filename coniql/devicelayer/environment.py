from typing import List

_ADDR_DELIMITER = '.'


class DeviceEnvironment:
    """Wrapper for device tree that allows for resource lookup via a
    dot-separated string (e.g. detector.exposure_time)"""
    def __init__(self, device_tree):
        self.device_tree = device_tree

    def get_fields(self, resource_addr: str):
        resource = self.get_resource(resource_addr)
        return resource.dict_view()

    def get_resource(self, resource_addr: str):
        addr = parse_resource_addr(resource_addr)
        return get_resource(self.device_tree, addr)


def parse_resource_addr(resource_addr: str) -> List[str]:
    return resource_addr.split(_ADDR_DELIMITER)


def get_resource(device_tree, resource_addr: List[str]):
    """Traverses a device tree and finds the requested resource"""
    nxt = resource_addr[0]
    nxt_attr = getattr(device_tree, nxt)
    if len(resource_addr) == 1:
        return nxt_attr
    elif len(resource_addr) > 1:
        return get_resource(nxt_attr, resource_addr[1:])
    else:
        raise Exception('Resource not found')
