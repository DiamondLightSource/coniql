from device.channel.ca.channel import CaChannel, CaField
from device.channel.channeltypes.result import Readback


class CaBool(CaField):
    async def create_channel(self) -> 'CaBoolChannel':
        return CaBoolChannel(self.pv, self.rbv, self.wait, self.timeout)


class CaBoolChannel(CaChannel[bool]):
    async def put(self, value: bool) -> Readback[bool]:
        return await super().put(int(value))

    def format_value(self, value):
        return bool(value.real)
