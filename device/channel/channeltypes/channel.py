from typing import TypeVar, Generic, AsyncGenerator, Union
from typing_extensions import Protocol, runtime_checkable

from coniql._types import ChannelStatus, Time, Readback

TValue = TypeVar('TValue', covariant=True)
TInputValue = TypeVar('TInputValue', contravariant=True)
DEFAULT_TIMEOUT = 10.0  # seconds


@runtime_checkable
class HasValue(Protocol[TValue]):
    async def get(self) -> TValue:
        return NotImplemented


@runtime_checkable
class HasReadback(Protocol):
    async def get_readback(self) -> Readback:
        return NotImplemented


@runtime_checkable
class CanMonitorValue(Protocol[TValue]):
    async def monitor(self) -> AsyncGenerator[TValue, None]:
        yield NotImplemented


@runtime_checkable
class CanMonitorReadback(Protocol):
    async def monitor_readback(self) -> AsyncGenerator[Readback, None]:
        yield NotImplemented


@runtime_checkable
class CanPutValue(Protocol[TInputValue]):
    async def put(self, value: TInputValue) -> bool:
        return NotImplemented


@runtime_checkable
class ReadOnlyChannel(HasValue[TValue], HasReadback,
                      CanMonitorReadback, CanMonitorValue[TValue],
                      Protocol[TValue]):
    pass


@runtime_checkable
class ReadWriteChannelDiff(ReadOnlyChannel[TValue], CanPutValue[TInputValue],
                       Protocol[TValue, TInputValue]):
    pass


@runtime_checkable
class ReadWriteChannel(ReadWriteChannelDiff[TValue, TValue]):
    pass
