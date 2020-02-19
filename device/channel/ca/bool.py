from typing_extensions import Protocol

from device.channel.ca.channel import CaChannel


class CaBool(CaChannel[bool]):
    async def get(self) -> bool:
        value = await self.caget()
        return bool(value.real)
