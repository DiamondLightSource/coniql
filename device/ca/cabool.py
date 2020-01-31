from device.ca.channel import CaChannel
from device.devicetypes.channel import DEFAULT_TIMEOUT
from device.devicetypes.result import Readback


class CaBool(CaChannel[bool]):
    async def put(self, value: bool) -> Readback[bool]:
        return await super().put(int(value))

    def format_value(self, value):
        return bool(value.real)
