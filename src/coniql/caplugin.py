# Support type hints for asyncio.Queue
from __future__ import annotations

import asyncio
import logging
import uuid
from asyncio import Event, Queue
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Callable, Dict, List, Optional, Sequence

from aioca import (
    DBE_PROPERTY,
    FORMAT_CTRL,
    FORMAT_TIME,
    CANothing,
    Subscription,
    caget,
    cainfo,
    camonitor,
    caput,
)
from aioca.types import AugmentedValue

from coniql.coniql_schema import Widget
from coniql.metrics import update_subscription_metrics
from coniql.plugin import Plugin, PutValue
from coniql.types import (
    Channel,
    ChannelDisplay,
    ChannelFormatter,
    ChannelQuality,
    ChannelRole,
    ChannelStatus,
    ChannelTime,
    ChannelValue,
    Range,
)

coniql_logger = logging.getLogger(__name__)
TRANSPORT = "ca://"


class CAChannelMaker:
    def __init__(self, name, writeable: bool):
        self.name = name
        self.cached_status: Optional[ChannelStatus] = None
        self.formatter = ChannelFormatter()
        # No camonitor is capable of updating whether a channel is writeable,
        # so this value is immutable.
        self.writeable = writeable

    @staticmethod
    def _create_formatter(value: AugmentedValue) -> ChannelFormatter:
        formatter = ChannelFormatter()
        precision = getattr(value, "precision", 0)
        units = getattr(value, "units", "")
        if hasattr(value, "dtype"):
            # numpy array
            formatter = ChannelFormatter.for_ndarray(
                precision,
                units,
            )
        elif hasattr(value, "enums"):
            # enum
            formatter = ChannelFormatter.for_enum(value.enums)
        elif isinstance(value, (int, float)):
            # number
            formatter = ChannelFormatter.for_number(
                precision,
                units,
            )

        return formatter

    def channel_from_update(
        self,
        time_value: Optional[AugmentedValue] = None,
        meta_value: Optional[AugmentedValue] = None,
        send_quality: bool = False,
    ) -> Channel:
        """Create a Channel object, populated with data taken from the provided
        AugmentedValue(s).

        Specify `send_quality` to force the "quality" attribute to be included in
        the returned channel - by default it will only send this attribute if it
        has changed state.
        """
        value = None
        time = None
        status = None
        display = None

        if meta_value is not None and meta_value.ok:
            self.formatter = CAChannelMaker._create_formatter(meta_value)
            # The value itself should not have changed for a meta_value update,
            # but the formatter may have, so send an updated value.
            value = ChannelValue(meta_value, self.formatter)
            display = ChannelDisplay(
                description=self.name,
                role=ChannelRole.RW,
                widget=Widget.TEXTINPUT,
                form=None,
            )
            if hasattr(meta_value, "enums"):
                display.choices = meta_value.enums
            if hasattr(meta_value, "precision"):
                display.precision = meta_value.precision
            if hasattr(meta_value, "units"):
                display.units = meta_value.units
                display.controlRange = Range(
                    min=meta_value.lower_ctrl_limit,
                    max=meta_value.upper_ctrl_limit,
                )
                display.displayRange = Range(
                    min=meta_value.lower_disp_limit,
                    max=meta_value.upper_disp_limit,
                )
                display.alarmRange = Range(
                    min=meta_value.lower_alarm_limit,
                    max=meta_value.upper_alarm_limit,
                )
                display.warningRange = Range(
                    min=meta_value.lower_warning_limit,
                    max=meta_value.upper_warning_limit,
                )

        if time_value is not None:
            if time_value.ok:
                assert time_value.timestamp
                value = ChannelValue(time_value, self.formatter)
                quality = str(ChannelQuality(time_value.severity))
                if (
                    send_quality
                    or self.cached_status is None
                    or self.cached_status.quality != quality
                ):
                    status = ChannelStatus(
                        quality=quality,
                        message="",
                        mutable=self.writeable,
                    )
                    self.cached_status = status
                time = ChannelTime(
                    seconds=time_value.timestamp,
                    nanoseconds=time_value.raw_stamp[1],
                    userTag=0,
                )
            else:
                # An update where .ok is false indicates a disconnection.
                status = ChannelStatus(
                    quality="INVALID",
                    message="",
                    mutable=self.writeable,
                )
                self.cached_status = status
        id = TRANSPORT + self.name
        return CAChannel(id, value, time, status, display)


@dataclass
class CAChannel(Channel):
    id: Optional[str]
    value: Optional[ChannelValue]
    time: Optional[ChannelTime]
    status: Optional[ChannelStatus]
    display: Optional[ChannelDisplay]

    def get_id(self) -> Optional[str]:
        return self.id

    def get_time(self) -> Optional[ChannelTime]:
        return self.time

    def get_status(self) -> Optional[ChannelStatus]:
        return self.status

    def get_value(self) -> Optional[ChannelValue]:
        return self.value

    def get_display(self) -> Optional[ChannelDisplay]:
        return self.display


@dataclass
class CallbackContext:
    callback: Callable[[Channel], None]


@dataclass
class SubscriptionData:
    pv: str

    time_value: Optional[AugmentedValue]
    time_monitor: Subscription

    meta_value: Optional[AugmentedValue]
    meta_monitor: Subscription

    all_values_received: Event

    callbacks: Dict[str, CallbackContext]
    maker: CAChannelMaker

    subscribers: int


class DataEnum(Enum):
    TIME_VALUE = "time_value"
    META_VALUE = "meta_value"


class CASubscriptionManager:
    """Pools camonitor requests across all subscriptions, ensuring we only have one
    active subscription for each PV."""

    def __init__(self) -> None:
        self.pvs: Dict[str, SubscriptionData] = {}
        self.metrics_task: Optional[asyncio.Task] = None
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def update_metrics(self) -> None:
        value_monitor_last_dropped: Dict[str, int] = defaultdict(int)
        meta_monitor_last_dropped: Dict[str, int] = defaultdict(int)

        while True:
            for x in self.pvs.values():
                value_monitor_last_dropped[x.pv] = update_subscription_metrics(
                    x.time_monitor, value_monitor_last_dropped[x.pv], {"type": "value"}
                )
                meta_monitor_last_dropped[x.pv] = update_subscription_metrics(
                    x.meta_monitor, meta_monitor_last_dropped[x.pv], {"type": "meta"}
                )
            await asyncio.sleep(10)  # Metrics only need updating infrequently

    def __callback(self, pv: str, key: DataEnum, v: AugmentedValue):
        if pv not in self.pvs:
            return

        data = self.pvs[pv]

        if key == DataEnum.TIME_VALUE:
            data.time_value = v
        elif key == DataEnum.META_VALUE:
            data.meta_value = v
        else:
            raise KeyError(f"Unrecognised key {key}")

        # Ensure we have both values before creating the channel
        # This ensures the first update sent to the client has both
        # values and metadata
        if data.time_value is None or data.meta_value is None:
            return

        if not data.all_values_received.is_set():
            # The first subscription return is handled as part of the
            # `subscribe` function, which is blocked waiting on this event
            data.all_values_received.set()
        else:
            # Otherwise, construct the appropriate channel and call all callbacks
            if key == DataEnum.TIME_VALUE:
                channel = data.maker.channel_from_update(time_value=data.time_value)
            elif key == DataEnum.META_VALUE:
                channel = data.maker.channel_from_update(meta_value=data.meta_value)

            for context in data.callbacks.values():
                context.callback(channel)

    async def subscribe(
        self, pv: str, callback: Callable[[Channel], None], callback_key: str
    ):
        """Subscribe to the given PV.

        This function will block until both a time and meta value update has been
        received from the PV. Once the data is received the provided callback will be
        called immediately, with a Channel object that contains both time and meta
        values.

        Caller must provide a key that will be associated with the callback. This same
        key must be passed to the `unsubscribe` function."""
        callback_context = CallbackContext(callback)

        # Restrict access to the shared dictionary - otherwise issues arise if two
        # clients attempt to subscribe to the same PV at the same time
        async with self.locks[pv]:
            # One-time async init across all subscriptions
            if self.metrics_task is None:
                self.metrics_task = asyncio.create_task(self.update_metrics())

            # Either this PV is new or we've previously closed the monitors.
            if (
                pv not in self.pvs
                or self.pvs[pv].meta_monitor.state == Subscription.CLOSED
            ):
                # A specific request required for whether the channel is writeable.
                # This will not be updated, so wait until a callback is received
                # before making the request when the channel is likely be connected.
                # NOTE: This MUST happen before the camonitors are created, otherwise we
                # run the risk of the initial monitor callbacks happening while we're
                # waiting for this cainfo call to return.
                writeable = True
                try:
                    info = await cainfo(pv)
                    writeable = info.write
                except CANothing:
                    # Unlikely, but allow subscriptions to continue.
                    pass

                # Initialize camonitors for this PV
                value_monitor = camonitor(
                    pv,
                    lambda v: self.__callback(pv, DataEnum.TIME_VALUE, v),
                    format=FORMAT_TIME,
                    notify_disconnect=True,
                )

                # Monitor PV only for property changes. For EPICS < 3.15 this monitor
                # will update once on connection but will not subsequently be triggered.
                # https://github.com/dls-controls/coniql/issues/22#issuecomment-863899258
                meta_monitor = camonitor(
                    pv,
                    lambda v: self.__callback(pv, DataEnum.META_VALUE, v),
                    events=DBE_PROPERTY,
                    format=FORMAT_CTRL,
                )

                maker = CAChannelMaker(pv, writeable)

                self.pvs[pv] = SubscriptionData(
                    pv=pv,
                    time_value=None,
                    time_monitor=value_monitor,
                    meta_value=None,
                    meta_monitor=meta_monitor,
                    all_values_received=Event(),
                    callbacks={callback_key: callback_context},
                    maker=maker,
                    subscribers=1,
                )

            else:
                self.pvs[pv].subscribers += 1
                self.pvs[pv].callbacks[callback_key] = callback_context

            # Construct and send a channel with both time and meta values
            data = self.pvs[pv]
            await data.all_values_received.wait()
            channel = data.maker.channel_from_update(
                time_value=data.time_value,
                meta_value=data.meta_value,
                send_quality=True,
            )
            callback_context.callback(channel)

    def unsubscribe(self, pv: str, callback_key: str) -> None:
        """Unsubscribe from the given PV. The callback key must be provided and must
        match the one passed to the `subscribe` function."""
        data = self.pvs[pv]

        data.subscribers -= 1

        data.callbacks.pop(callback_key)

        if data.subscribers == 0:
            data.time_monitor.close()
            data.meta_monitor.close()


class CAPlugin(Plugin):
    def __init__(self):
        self.subscription_manager = CASubscriptionManager()

    async def get_channel(self, pv: str, timeout: float) -> Channel:
        time_value, meta_value, info = await asyncio.gather(
            caget(pv, format=FORMAT_TIME, timeout=timeout),
            caget(pv, format=FORMAT_CTRL, timeout=timeout),
            cainfo(pv, timeout=timeout),
        )
        maker = CAChannelMaker(pv, info.write)
        return maker.channel_from_update(time_value=time_value, meta_value=meta_value)

    async def put_channels(
        self, pvs: List[str], values: Sequence[PutValue], timeout: float
    ):
        await caput(pvs, values, timeout=timeout)

    async def subscribe_channel(self, pv: str) -> AsyncIterator[Channel]:
        value: Queue[Channel] = asyncio.Queue(maxsize=1)

        # Generate unique key for this subscription
        uid = str(uuid.uuid4())

        def __callback(channel: Channel):
            # Ensure queue is empty
            while True:
                try:
                    value.get_nowait()
                except asyncio.QueueEmpty:
                    break

            value.put_nowait(channel)

        await self.subscription_manager.subscribe(pv, __callback, uid)

        try:
            while True:
                yield await value.get()

        finally:
            self.subscription_manager.unsubscribe(pv, uid)
