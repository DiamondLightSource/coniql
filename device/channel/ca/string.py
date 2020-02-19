from typing_extensions import Protocol

from device.channel.ca.channel import CaChannel


class CaString(CaChannel[str]):
    async def get(self) -> str:
        value = await self.caget()
        return str(value)
