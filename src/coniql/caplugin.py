import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List, Optional

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

from coniql.coniql_schema import DisplayForm, Widget
from coniql.device_config import ChannelConfig
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
    def __init__(self, name, config: ChannelConfig, writeable: bool):
        self.name = name
        self.config = config
        self.cached_status: Optional[ChannelStatus] = None
        self.formatter = ChannelFormatter()
        # No camonitor is capable of updating whether a channel is writeable,
        # so this value is immutable.
        self.writeable = writeable

    @staticmethod
    def _create_formatter(
        value: AugmentedValue, display_form: DisplayForm
    ) -> ChannelFormatter:
        formatter = ChannelFormatter()
        precision = getattr(value, "precision", 0)
        units = getattr(value, "units", "")
        if hasattr(value, "dtype"):
            # numpy array
            formatter = ChannelFormatter.for_ndarray(
                display_form,
                precision,
                units,
            )
        elif hasattr(value, "enums"):
            # enum
            formatter = ChannelFormatter.for_enum(value.enums)
        elif isinstance(value, (int, float)):
            # number
            formatter = ChannelFormatter.for_number(
                display_form,
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
            self.formatter = CAChannelMaker._create_formatter(
                meta_value, self.config.display_form
            )
            # The value itself should not have changed for a meta_value update,
            # but the formatter may have, so send an updated value.
            value = ChannelValue(meta_value, self.formatter)
            display = ChannelDisplay(
                description=self.name,
                role="RW",
                widget=self.config.widget or Widget.TEXTINPUT,
                form=self.config.display_form,
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
    async def get_channel(
        self, pv: str, timeout: float, config: ChannelConfig
    ) -> Channel:
        time_value, meta_value, info = await asyncio.gather(
            caget(pv, format=FORMAT_TIME, timeout=timeout),
            caget(pv, format=FORMAT_CTRL, timeout=timeout),
            cainfo(pv, timeout=timeout),
        )
        maker = CAChannelMaker(pv, config, info.write)
        return maker.channel_from_update(time_value=time_value, meta_value=meta_value)

    async def put_channels(
        self, pvs: List[str], values: List[PutValue], timeout: float
    ):
        await caput(pvs, values, timeout=timeout)

    async def subscribe_channel(
        self, pv: str, config: ChannelConfig
    ) -> AsyncIterator[Channel]:
        # A queue that contains a monitor update and the keyword with which
        # the channel's update_value function should be called.
        q: asyncio.Queue[Dict[str, AugmentedValue]] = asyncio.Queue()
        # Monitor PV for value and alarm changes with associated timestamp.
        # Use this monitor also for notifications of disconnections.
        value_monitor = camonitor(
            pv,
            lambda v: q.put({"time_value": v}),
            format=FORMAT_TIME,
            notify_disconnect=True,
        )
        # Monitor PV only for property changes. For EPICS < 3.15 this monitor
        # will update once on connection but will not subsequently be triggered.
        # https://github.com/dls-controls/coniql/issues/22#issuecomment-863899258
        meta_monitor = camonitor(
            pv,
            lambda v: q.put({"meta_value": v}),
            events=DBE_PROPERTY,
            format=FORMAT_CTRL,
        )
        try:
            first_channel_value = await q.get()
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

            maker = CAChannelMaker(pv, config, writeable)
            # Do not continue until both monitors have returned.
            # Then the first Channel returned will be complete.
            while len(first_channel_value) < 2:
                update = await q.get()
                first_channel_value.update(update)

            yield maker.channel_from_update(**first_channel_value)

            # Handle all subsequent updates from both monitors.
            while True:
                update = await q.get()
                yield maker.channel_from_update(**update)
        finally:
            value_monitor.close()
            meta_monitor.close()
