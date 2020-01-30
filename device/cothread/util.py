import asyncio
from dataclasses import dataclass
from typing import TypeVar, Generic, AsyncGenerator

from cothread.aioca import caget_one, FORMAT_CTRL, FORMAT_TIME, caput_one, \
    camonitor, connect

from device.devicetypes.channel import DEFAULT_TIMEOUT

T = TypeVar('T')

@dataclass
class CaDef:
    pv: str
    rbv: str

    @classmethod
    def for_single_pv(cls, pv: str):
        return CaDef(pv, pv)

    @classmethod
    def with_rbv_prefix(cls, pv: str, rbv_prefix: str):
        return CaDef(pv, f'{pv}{rbv_prefix}')


class RawCaChannel(Generic[T]):
    def __init__(self, cadef: CaDef, timeout: float = DEFAULT_TIMEOUT):
        self.cadef = cadef
        self.timeout = timeout

    async def connect(self):
        await connect([self.cadef.pv, self.cadef.rbv])

    async def get_meta(self):
        return await caget_one(self.cadef.rbv, format=FORMAT_CTRL,
                               timeout=self.timeout)

    async def get(self) -> T:
        value = await caget_one(self.cadef.rbv,
                                format=FORMAT_TIME, timeout=self.timeout)
        return value

    async def put(self, value: T):
        return await caput_one(self.cadef.pv, value, timeout=self.timeout)

    async def monitor(self) -> AsyncGenerator[T, None]:
        q: asyncio.Queue = asyncio.Queue()

        def queue_callback(value):
            asyncio.create_task(q.put(value))

        subscription = await camonitor(self.cadef.rbv,
                                       queue_callback, format=FORMAT_TIME)
        try:
            while True:
                yield await q.get()
        finally:
            subscription.close()
