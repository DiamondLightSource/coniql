from typing import TypeVar, Generic, AsyncGenerator, Union
from typing_extensions import Protocol

from coniql._types import ChannelStatus, Time, Readback

TValue = TypeVar('TValue', covariant=True)
TInputValue = TypeVar('TInputValue', contravariant=True)
DEFAULT_TIMEOUT = 10.0  # seconds


class HasValue(Protocol[TValue]):
    async def get(self) -> TValue:
        return NotImplemented


class HasReadback(Protocol):
    async def get_readback(self) -> Readback:
        return NotImplemented


class CanMonitorValue(Protocol[TValue]):
    async def monitor(self) -> AsyncGenerator[TValue, None]:
        yield NotImplemented


class CanMonitorReadback(Protocol):
    async def monitor_readback(self) -> AsyncGenerator[Readback, None]:
        yield NotImplemented


class CanPutValue(Protocol[TInputValue]):
    async def put(self, value: TInputValue) -> bool:
        return NotImplemented


class ReadOnlyChannel(HasValue[TValue], HasReadback,
                      CanMonitorReadback, CanMonitorValue[TValue],
                      Protocol[TValue]):
    pass


class ReadWriteChannelDiff(ReadOnlyChannel[TValue], CanPutValue[TInputValue],
                       Protocol[TValue, TInputValue]):
    pass


class ReadWriteChannel(ReadWriteChannelDiff[TValue, TValue]):
    pass
