from typing import TypeVar, Optional, AsyncGenerator, Generic

from aioca._aioca import caget_one, FORMAT_TIME, caput_one, connect

from coniql._types import Readback
from device.channel.ca.util.camonitor import camonitor_as_async_generator
from device.channel.ca.util.readback import ca_value_to_readback

T = TypeVar('T')


def find_rbv(pv: str, rbv: Optional[str] = None,
             rbv_suffix: Optional[str] = None) -> str:
    """Determines readback PV given the PV and optionally a readback PV and
    a readback suffix."""
    if rbv is not None:
        return rbv
    elif rbv_suffix is not None:
        return f'{pv}{rbv_suffix}'
    else:
        return pv


class CaChannel(Generic[T]):
    """A Channel that can communicate with a PV over Channel Access"""
    timeout: float
    wait: bool
    pv: str
    rbv: str

    def __init__(self, pv: str, pv_prefix: Optional[str] = None,
                 rbv: Optional[str] = None, rbv_suffix: Optional[str] = None,
                 wait: bool = True, timeout: Optional[float] = None):
        pv_prefix = pv_prefix or ''
        self.pv = f'{pv_prefix}{pv}'
        self.rbv = find_rbv(pv, rbv, rbv_suffix)
        self.wait = wait
        self.timeout = timeout or 5

    async def setup(self):
        """Performs any setup for this channel. Verifies that the PV is
        reachable and gather any metadata"""
        pvs = [self.pv, self.rbv]
        print(f'Connecting to {pvs}')
        return await connect(pvs)

    async def put(self, value: T) -> bool:
        """Write a value to this channel"""
        await self.__caput(value)
        return True

    async def get(self) -> T:
        """Request and read a value from this channel"""
        value = await self.__caget()
        return self.format_value(value)

    async def get_readback(self) -> Readback:
        """Request and read a Readback structure from this channel"""
        value = await self.__caget()
        return await self.as_readback(value)

    async def monitor(self) -> AsyncGenerator[T, None]:
        """Returns an asynchronous generator that yields values of this
        channel. The first value is yeilded when the request is made.
        Subsequent values are yeilded when the channel changes."""
        gen = await self.__camonitor()
        async for value in gen:
            yield value.real

    async def monitor_readback(self) -> AsyncGenerator[Readback, None]:
        """Returns an asynchronous generator that yields Readback objects
        associated with this channel. The first value is yeilded when the
        request is made. Subsequent values are yeilded when the channel
        changes."""
        gen = await self.__camonitor()
        async for value in gen:
            yield self.as_readback(value)

    async def as_readback(self, value) -> Readback:
        """Converts a value structure from aioca to a Readback object"""
        return ca_value_to_readback(self.format_value(value), value)

    def format_value(self, value) -> T:
        """Converts an aioca value into a simpler value. Should be used for
        formatting and conversion to a simpler Python type"""
        return value.real

    # Simple wrappers around CA functions

    async def __caput(self, value):
        return await caput_one(self.pv, value,
                               timeout=self.timeout,
                               wait=self.wait)

    async def __caget(self):
        return await caget_one(self.rbv,
                               format=FORMAT_TIME,
                               timeout=self.timeout)

    async def __camonitor(self):
        return camonitor_as_async_generator(self.rbv)
