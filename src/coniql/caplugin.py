import asyncio
import collections
import logging
import threading
from dataclasses import dataclass
from typing import Any, AsyncIterator, Deque, List, Optional, Sequence

from aioca import (
    DBE_PROPERTY,
    FORMAT_CTRL,
    FORMAT_TIME,
    CANothing,
    caget,
    cainfo,
    camonitor,
    caput,
)
from aioca.types import AugmentedValue

from coniql.coniql_schema import Widget
from coniql.plugin import Plugin, PutValue
from coniql.types import (
    CHANNEL_QUALITY_MAP,
    Channel,
    ChannelDisplay,
    ChannelFormatter,
    ChannelStatus,
    ChannelTime,
    ChannelValue,
    Range,
)


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
    ) -> Channel:
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
                role="RW",
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
                quality = CHANNEL_QUALITY_MAP[time_value.severity]
                if self.cached_status is None or self.cached_status.quality != quality:
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

        return CAChannel(value, time, status, display)


@dataclass
class CAChannel(Channel):
    value: Optional[ChannelValue]
    time: Optional[ChannelTime]
    status: Optional[ChannelStatus]
    display: Optional[ChannelDisplay]

    def get_time(self) -> Optional[ChannelTime]:
        return self.time

    def get_status(self) -> Optional[ChannelStatus]:
        return self.status

    def get_value(self) -> Optional[ChannelValue]:
        return self.value

    def get_display(self) -> Optional[ChannelDisplay]:
        return self.display


class CAPlugin(Plugin):
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

    @staticmethod
    async def __signal_single_channel(
        value: "UpdateSignal",
        values: Deque[AugmentedValue],
        maker: CAChannelMaker,
        lock: threading.Lock,
    ) -> Channel:
        """Called when a specific signals is armed indicating that data are
        are ready to be read from the corresponding deques. The signal is
        disarmed so it is ready for the next update and the deque's contents
        is used to create and return a Channel object containing the update."""
        with lock:
            try:
                # Consume a single value from the queue
                value.disarm()
                return maker.channel_from_update(**values.popleft())
            except IndexError:
                # In case deque is empty just return an empty channel
                return maker.channel_from_update()

    @staticmethod
    async def __signal_double_channel(
        value: "UpdateSignal",
        meta: "UpdateSignal",
        values: Deque[AugmentedValue],
        metas: Deque[AugmentedValue],
        maker: CAChannelMaker,
        value_lock: threading.Lock,
        meta_lock: threading.Lock,
    ) -> Channel:
        """Called when both value and metadata signals are armed indicating
        that values are ready to be read from the value and metadata deques.
        Signals are disarmed so they are ready for next update and the deque's
        contents are used to create and return a Channel object containing
        the update."""
        with value_lock and meta_lock:
            try:
                # Consume a single value from the queue
                value.disarm()
                meta.disarm()
                return maker.channel_from_update(**values.popleft(), **metas.popleft())
            except IndexError:
                # In case deque is empty just return an empty channel
                return maker.channel_from_update()

    class UpdateSignal:
        """Class used to signal when an update is available"""

        def __init__(self):
            self.signal: bool = False

        def arm(self):
            self.signal = True

        def disarm(self):
            self.signal = False

        def is_armed(self) -> bool:
            return self.signal

    def __callback(
        self,
        v: Any,
        dict_key: str,
        signal: UpdateSignal,
        value_deque: Deque[AugmentedValue],
        lock: threading.Lock,
    ) -> None:
        with lock:
            value_deque.append({dict_key: v})
            signal.arm()

    async def subscribe_channel(self, pv: str) -> AsyncIterator[Channel]:
        # Monitor PV for value and alarm changes with associated timestamp.
        # Use this monitor also for notifications of disconnections.
        value_signal = self.UpdateSignal()
        value_lock = threading.Lock()
        values: Deque[AugmentedValue] = collections.deque(maxlen=1)
        value_monitor = camonitor(
            pv,
            lambda v: self.__callback(
                v, "time_value", value_signal, values, value_lock
            ),
            format=FORMAT_TIME,
            notify_disconnect=True,
        )
        # Monitor PV only for property changes. For EPICS < 3.15 this monitor
        # will update once on connection but will not subsequently be triggered.
        # https://github.com/dls-controls/coniql/issues/22#issuecomment-863899258
        meta_signal = self.UpdateSignal()
        meta_lock = threading.Lock()
        metas: Deque[AugmentedValue] = collections.deque(maxlen=1)
        meta_monitor = camonitor(
            pv,
            lambda v: self.__callback(v, "meta_value", meta_signal, metas, meta_lock),
            events=DBE_PROPERTY,
            format=FORMAT_CTRL,
        )

        try:
            # A specific request required for whether the channel is writeable.
            # This will not be updated, so wait until a callback is received
            # before making the request when the channel is likely be connected.
            writeable = True
            try:
                info = await cainfo(pv)
                writeable = info.write
            except CANothing:
                # Unlikely, but allow subscriptions to continue.
                pass

            maker = CAChannelMaker(pv, writeable)

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 'RuntimeError: There is no current event loop...'
                logging.error("No running event loop...")
                loop = None

            # Handle all subsequent updates from both monitors.
            firstChannelReceived = False
            while True:
                await asyncio.sleep(0.01)
                # Wait to receive both channels at the beginning
                if loop is not None and not firstChannelReceived:
                    if value_signal.is_armed() and meta_signal.is_armed():
                        data = loop.create_task(
                            self.__signal_double_channel(
                                value_signal,
                                meta_signal,
                                values,
                                metas,
                                maker,
                                value_lock,
                                meta_lock,
                            )
                        )
                        await data
                        if data.result() is not None:
                            yield data.result()
                        firstChannelReceived = True
                # Now update accordingly
                elif loop is not None and firstChannelReceived:
                    if value_signal.is_armed():
                        data = loop.create_task(
                            self.__signal_single_channel(
                                value_signal, values, maker, value_lock
                            )
                        )
                        await data
                        if data.result() is not None:
                            yield data.result()
                    if meta_signal.is_armed():
                        data = loop.create_task(
                            self.__signal_single_channel(
                                meta_signal, metas, maker, meta_lock
                            )
                        )
                        await data
                        if data.result() is not None:
                            yield data.result()
        finally:
            value_monitor.close()
            meta_monitor.close()
