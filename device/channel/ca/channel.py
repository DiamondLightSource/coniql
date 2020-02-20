from typing import TypeVar, Optional, AsyncGenerator, Generic
from typing_extensions import Protocol

from aioca._aioca import caget_one, FORMAT_TIME, caput_one, connect

from device.channel.ca.util import camonitor_as_async_generator

T = TypeVar('T')


def find_rbv(pv: str, rbv: Optional[str] = None,
             rbv_suffix: Optional[str] = None) -> str:
    if rbv is not None:
        return rbv
    elif rbv_suffix is not None:
        return f'{pv}{rbv_suffix}'
    else:
        return pv


class CaChannel(Generic[T]):
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
        return await connect([self.pv, self.rbv])

    async def put(self, value: T) -> bool:
        await self.caput(value)
        return True

    async def caput(self, value):
        return await caput_one(self.pv, value,
                         timeout=self.timeout,
                         wait=self.wait)

    async def get(self) -> T:
        value = await self.caget()
        return value.real

    async def caget(self):
        return await caget_one(self.rbv,
                         format=FORMAT_TIME,
                         timeout=self.timeout)

    async def monitor(self) -> AsyncGenerator[T, None]:
        gen = await self.camonitor()
        async for value in gen:
            yield value.real

    async def camonitor(self):
        return camonitor_as_async_generator(self.rbv)
