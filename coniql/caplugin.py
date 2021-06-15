import asyncio
from typing import AsyncIterator, List, Optional

from aioca import (
    DBE_PROPERTY,
    FORMAT_CTRL,
    FORMAT_TIME,
    caget,
    cainfo,
    camonitor,
    caput,
)
from aioca.types import AugmentedValue

from coniql.coniql_schema import Widget
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


class CAChannel(Channel):
    def __init__(
        self, name, config: ChannelConfig, initial_value: AugmentedValue,
    ):
        self.name = name
        self.config = config
        self.value = initial_value
        self.meta_value: Optional[AugmentedValue] = None
        self.precision = 0
        self.formatter = ChannelFormatter()
        self.display = ChannelDisplay(
            description=self.name,
            role="RW",
            widget=self.config.widget or Widget.TEXTINPUT,
            form=self.config.display_form,
        )
        self.writeable = True

    def update_value(self, value: AugmentedValue) -> None:
        # This must be called with a value that has a timestamp.
        assert value.timestamp
        self.value = value

    def update_metadata(self, value: AugmentedValue) -> None:
        if hasattr(value, "precision"):
            self.precision = value.precision
        if hasattr(value, "dtype"):
            self.dtype = value.dtype
        if hasattr(value, "enums"):
            self.enums = value.enums
            self.display.choices = self.enums

        if hasattr(value, "units"):
            self.display.controlRange = Range(
                min=value.lower_ctrl_limit, max=value.upper_ctrl_limit,
            )
            self.display.displayRange = Range(
                min=value.lower_disp_limit, max=value.upper_disp_limit,
            )
            self.display.alarmRange = Range(
                min=value.lower_alarm_limit, max=value.upper_alarm_limit,
            )
            self.display.warningRange = Range(
                min=value.lower_warning_limit, max=value.upper_warning_limit,
            )
            self.display.units = value.units
            self.display.precision = self.precision

        if hasattr(value, "dtype"):
            # numpy array
            self.formatter = ChannelFormatter.for_ndarray(
                self.config.display_form, self.precision, self.display.units,
            )
        elif hasattr(value, "enums"):
            # enum
            self.formatter = ChannelFormatter.for_enum(value.enums)
        elif isinstance(value, (int, float)):
            # number
            self.formatter = ChannelFormatter.for_number(
                self.config.display_form, self.precision, self.display.units,
            )

    def get_time(self) -> Optional[ChannelTime]:
        time = None
        if self.value is not None:
            time = ChannelTime(
                seconds=self.value.timestamp,
                nanoseconds=self.value.raw_stamp[1],
                userTag=0,
            )
        return time

    def get_status(self) -> Optional[ChannelStatus]:
        status = None
        if self.value is not None:
            status = ChannelStatus(
                quality=CHANNEL_QUALITY_MAP[self.value.severity],
                message="",
                mutable=self.writeable,
            )
        return status

    def get_value(self) -> Optional[ChannelValue]:
        value = ChannelValue(self.value, self.formatter)
        return value

    def get_display(self) -> ChannelDisplay:
        return self.display


class CAPlugin(Plugin):
    async def get_channel(
        self, pv: str, timeout: float, config: ChannelConfig
    ) -> Channel:
        info, meta_value, value = await asyncio.gather(
            cainfo(pv, timeout=timeout),
            caget(pv, format=FORMAT_CTRL, timeout=timeout),
            caget(pv, format=FORMAT_TIME, timeout=timeout),
        )
        # Put in channel id so converters can see it
        channel = CAChannel(pv, config, value)
        channel.update_metadata(meta_value)
        return channel

    async def put_channels(
        self, pvs: List[str], values: List[PutValue], timeout: float
    ):
        await caput(pvs, values, timeout=timeout)

    async def subscribe_channel(
        self, pv: str, config: ChannelConfig
    ) -> AsyncIterator[Channel]:
        q: asyncio.Queue[AugmentedValue] = asyncio.Queue()

        value_monitor = camonitor(pv, q.put, format=FORMAT_TIME)
        meta_monitor = None
        try:
            first_value = await q.get()
            channel = CAChannel(pv, config, first_value)
            meta_monitor = camonitor(pv, q.put, events=DBE_PROPERTY, format=FORMAT_CTRL)
            while True:
                value = await q.get()
                if hasattr(value, "timestamp"):
                    # Update from value_monitor.
                    channel.update_value(value)
                else:
                    # Update from meta_monitor.
                    channel.update_metadata(value)
                yield channel
        finally:
            value_monitor.close()
            if meta_monitor is not None:
                meta_monitor.close()
