from typing import TypeVar, Generic, AsyncGenerator, Union
from typing_extensions import Protocol

from coniql._types import ChannelStatus, Time

TValue = TypeVar('TValue')
DEFAULT_TIMEOUT = 10.0  # seconds


class HasValue(Protocol[TValue]):
    async def get(self) -> TValue:
        return NotImplemented


class HasStatus(Protocol):
    async def get_status(self) -> ChannelStatus:
        return NotImplemented


class HasTimestamp(Protocol):
    async def get_timestamp(self) -> Time:
        return NotImplemented


class CanMonitorValue(Protocol[TValue]):
    async def monitor(self) -> AsyncGenerator[TValue, None]:
        yield NotImplemented


class CanMonitorStatus(Protocol):
    async def monitor_status(self) -> AsyncGenerator[ChannelStatus, None]:
        yield NotImplemented


class CanPutValue(Protocol[TValue]):
    async def put(self, value: TValue) -> bool:
        return NotImplemented


class ReadOnlyChannel(HasValue[TValue], HasTimestamp, HasStatus,
                      CanMonitorStatus, CanMonitorValue[TValue],
                      Protocol[TValue]):
    pass


class ReadWriteChannel(ReadOnlyChannel[TValue], CanPutValue[TValue],
                       Protocol[TValue]):
    pass
