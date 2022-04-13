import asyncio
import atexit
from typing import AsyncIterator, Dict, List, Optional, Tuple, Type

from p4p.client.asyncio import Context, Value

from coniql.coniql_schema import DisplayForm, Widget
from coniql.device_config import ChannelConfig
from coniql.plugin import Plugin, PutValue
from coniql.types import (
    CHANNEL_QUALITY_MAP,
    DISPLAY_FORM_MAP,
    Channel,
    ChannelDisplay,
    ChannelFormatter,
    ChannelStatus,
    ChannelTime,
    ChannelValue,
    Range,
)

# https://mdavidsaver.github.io/p4p/values.html
NUMBER_TYPES = {"b", "B", "h", "H", "i", "I", "l", "L", "f", "d"}
OTHER_TYPES = {"?", "s"}


class PVAChannel(Channel):
    def __init__(
        self, value: Value, config: ChannelConfig, last_channel: "PVAChannel" = None
    ):
        self.value = value
        self.config = config
        self.last_channel = last_channel
        self.formatter: Optional[ChannelFormatter] = None

    def get_status(self) -> Optional[ChannelStatus]:
        status = None
        v_alarm = self.value.alarm
        # Alarms change each time, so compare them
        if self.last_channel is None or self.last_channel.value.alarm != v_alarm:
            status = ChannelStatus(
                quality=CHANNEL_QUALITY_MAP[v_alarm.severity],
                message=v_alarm.message,
                mutable=True,
            )
        return status

    def get_time(self) -> Optional[ChannelTime]:
        time = None
        v_timestamp = self.value.timeStamp
        if self.last_channel is None or v_timestamp.changed():
            time = ChannelTime(
                seconds=v_timestamp.secondsPastEpoch + v_timestamp.nanoseconds * 1e-9,
                nanoseconds=v_timestamp.nanoseconds,
                userTag=v_timestamp.userTag,
            )
        return time


def update_display(display: ChannelDisplay, config: ChannelConfig):
    # Role defined by presence of PVs, delete modes without PV
    if config.read_pv or config.write_pv:
        if config.read_pv is None:
            display.role = display.role[1:]
        if config.write_pv is None:
            display.role = display.role[:-1]
    # Override description and widget
    display.description = config.description or display.description
    display.widget = config.widget or display.widget
    display.form = config.display_form or display.form


class ScalarPVAChannel(PVAChannel):
    def is_number(self) -> bool:
        type_specifier: str = self.value.type()["value"]
        return type_specifier.strip("a") in NUMBER_TYPES

    def is_array(self) -> bool:
        type_specifier: str = self.value.type()["value"]
        return type_specifier.startswith("a")

    def get_form_precision_units(self) -> Tuple[DisplayForm, int, str]:
        v_display = self.value.display
        try:
            form = DISPLAY_FORM_MAP[v_display.form.index]
            precision = v_display.precision
        except AttributeError:
            # Test version doesn't have these
            form = DisplayForm.DEFAULT
            precision = 3
        units = v_display.units
        form = self.config.display_form or form
        return (form, precision, units)

    def get_value(self) -> Optional[ChannelValue]:
        value = None
        if self.last_channel is None or self.value.changed("value"):
            if self.last_channel and not self.value.display.changed():
                # the last channel had one
                assert (
                    self.last_channel.formatter
                ), "Last channel doesn't have a formatter"
                self.formatter = self.last_channel.formatter
            elif self.is_number():
                form, prec, units = self.get_form_precision_units()
                if self.is_array():
                    self.formatter = ChannelFormatter.for_ndarray(form, prec, units)
                else:
                    self.formatter = ChannelFormatter.for_number(form, prec, units)
            else:
                self.formatter = ChannelFormatter()
            value = ChannelValue(self.value.value, self.formatter)
        return value

    def get_display(self) -> Optional[ChannelDisplay]:
        display = None
        v_display = self.value.display
        if self.last_channel is None or v_display.changed():
            display = ChannelDisplay(
                description=v_display.description, role="RW", widget=Widget.TEXTINPUT
            )
            if self.is_number():
                v_control = self.value.control
                v_value_alarm = self.value.valueAlarm
                display.controlRange = Range(
                    min=v_control.limitLow, max=v_control.limitHigh
                )
                display.displayRange = Range(
                    min=v_display.limitLow, max=v_display.limitHigh
                )
                display.alarmRange = Range(
                    min=v_value_alarm.lowAlarmLimit, max=v_value_alarm.highAlarmLimit
                )
                display.warningRange = Range(
                    min=v_value_alarm.lowWarningLimit,
                    max=v_value_alarm.highWarningLimit,
                )
                (
                    display.form,
                    display.precision,
                    display.units,
                ) = self.get_form_precision_units()
            update_display(display, self.config)
        return display


class EnumPVAChannel(PVAChannel):
    def get_value(self) -> Optional[ChannelValue]:
        value = None
        v_value = self.value.value
        if self.last_channel is None or v_value.changed():
            if self.last_channel and not v_value.changed("choices"):
                # use the last channel's formatter
                assert (
                    self.last_channel.formatter
                ), "Last channel doesn't have a formatter"
                self.formatter = self.last_channel.formatter
            else:
                self.formatter = ChannelFormatter.for_enum(v_value.choices)
            value = ChannelValue(v_value.index, self.formatter)
        return value

    def get_display(self) -> Optional[ChannelDisplay]:
        display = None
        v_value = self.value.value
        if self.last_channel is None or v_value.changed("choices"):
            display = ChannelDisplay(
                description="",
                role="RW",
                widget=Widget.COMBO,
                choices=v_value.choices,
            )
            update_display(display, self.config)
        return display


CHANNEL_CLASS: Dict[str, Type[PVAChannel]] = {
    "epics:nt/NTScalar:1.0": ScalarPVAChannel,
    "epics:nt/NTScalarArray:1.0": ScalarPVAChannel,
    "epics:nt/NTEnum:1.0": EnumPVAChannel,
}


class PVAPlugin(Plugin):
    def __init__(self):
        self.ctxt = Context("pva", nt=False)
        atexit.register(self.ctxt.close)

    async def get_channel(
        self, pv: str, timeout: float, config: ChannelConfig
    ) -> Channel:
        try:
            value: Value = await asyncio.wait_for(self.ctxt.get(pv), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while getting %s" % pv)
        channel = CHANNEL_CLASS[value.getID()](value, config)
        return channel

    async def put_channels(
        self, pvs: List[str], values: List[PutValue], timeout: float
    ):
        try:
            await asyncio.wait_for(self.ctxt.put(pvs, values), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while putting to %s" % pvs)

    async def subscribe_channel(
        self, pv: str, config: ChannelConfig
    ) -> AsyncIterator[Channel]:
        q: asyncio.Queue[Value] = asyncio.Queue()
        m = self.ctxt.monitor(pv, q.put)
        try:
            # Hold last channel for squashing identical alarms
            last_channel = None
            while True:
                value = await q.get()
                channel = CHANNEL_CLASS[value.getID()](value, config, last_channel)
                yield channel
                last_channel = channel
        finally:
            m.close()
