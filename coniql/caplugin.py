import asyncio
from typing import AsyncIterator, Optional

from aioca import FORMAT_CTRL, FORMAT_TIME, caget, camonitor, caput
from aioca.types import AugmentedValue

from coniql.coniql_schema import Widget
from coniql.device_config import ChannelConfig
from coniql.plugin import Plugin
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
        self,
        value: AugmentedValue,
        config: ChannelConfig,
        meta_value: AugmentedValue,
        last_value: AugmentedValue = None,
    ):
        self.value = value
        self.meta_value = meta_value
        self.config = config
        self.last_value = last_value

    def get_time(self) -> Optional[ChannelTime]:
        time = ChannelTime(
            seconds=self.value.timestamp, nanoseconds=self.value.raw_stamp[1], userTag=0
        )
        return time

    def get_status(self) -> Optional[ChannelStatus]:
        status = None
        if self.last_value and self.last_value.severity != self.value.severity:
            status = ChannelStatus(
                quality=CHANNEL_QUALITY_MAP[self.value.severity],
                message="",
                mutable=True,
            )
        return status

    def get_value(self) -> Optional[ChannelValue]:
        precision = getattr(self.meta_value, "precision", 0)
        if hasattr(self.value, "dtype"):
            # numpy array
            formatter = ChannelFormatter.for_ndarray(
                self.config.display_form, precision, self.meta_value.units,
            )
        elif hasattr(self.meta_value, "enums"):
            # enum
            formatter = ChannelFormatter.for_enum(self.meta_value.enums)
        elif isinstance(self.value, (int, float)):
            # number
            formatter = ChannelFormatter.for_number(
                self.config.display_form, precision, self.meta_value.units,
            )
        else:
            formatter = ChannelFormatter()
        value = ChannelValue(self.value, formatter)
        return value

    def get_display(self) -> Optional[ChannelDisplay]:
        display = None
        if self.last_value is None:
            # Only produce display the first time
            display = ChannelDisplay(
                description=self.value.name,
                role="RW",
                widget=self.config.widget or Widget.TEXTINPUT,
            )
            if hasattr(self.meta_value, "precision"):
                display.controlRange = Range(
                    min=self.meta_value.lower_ctrl_limit,
                    max=self.meta_value.upper_ctrl_limit,
                )
                display.displayRange = Range(
                    min=self.meta_value.lower_disp_limit,
                    max=self.meta_value.upper_disp_limit,
                )
                display.alarmRange = Range(
                    min=self.meta_value.lower_alarm_limit,
                    max=self.meta_value.upper_alarm_limit,
                )
                display.warningRange = Range(
                    min=self.meta_value.lower_warning_limit,
                    max=self.meta_value.upper_warning_limit,
                )
                display.units = self.meta_value.units
                display.precision = self.meta_value.precision
        return display


class CAPlugin(Plugin):
    async def get_channel(
        self, channel_id: str, timeout: float, config: ChannelConfig
    ) -> Channel:
        meta_value, value = await asyncio.gather(
            caget(channel_id, format=FORMAT_CTRL, timeout=timeout),
            caget(channel_id, format=FORMAT_TIME, timeout=timeout),
        )
        # Put in channel id so converters can see it
        channel = CAChannel(value, config, meta_value)
        return channel

    async def put_channel(
        self, channel_id: str, value, timeout: float, config: ChannelConfig
    ) -> Channel:
        await caput(channel_id, value, timeout=timeout)
        channel = await self.get_channel(channel_id, timeout, config)
        return channel

    async def subscribe_channel(
        self, channel_id: str, config: ChannelConfig
    ) -> AsyncIterator[Channel]:
        q: asyncio.Queue[AugmentedValue] = asyncio.Queue()
        meta_value = await caget(channel_id, format=FORMAT_CTRL)
        m = camonitor(channel_id, q.put, format=FORMAT_TIME)
        try:
            # This will hold the current version of alarm data
            last_value = None
            while True:
                value = await q.get()
                channel = CAChannel(value, config, meta_value, last_value)
                last_value = value
                yield channel
        finally:
            m.close()
