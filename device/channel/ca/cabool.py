from device.channel.ca.channel import CaChannel
from device.channel.channeltypes.result import Readback


class CaBool(CaChannel[bool]):
    async def put(self, value: bool) -> Readback[bool]:
        return await super().put(int(value))

    def format_value(self, value):
        return bool(value.real)
