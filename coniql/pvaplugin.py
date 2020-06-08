import asyncio
import atexit
from typing import AsyncIterator, Dict, Optional, Tuple, Type

from p4p.client.asyncio import Context, Value

from coniql.coniql_schema import DisplayForm, Widget
from coniql.device_config import ChannelConfig
from coniql.plugin import Plugin
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
    def __init__(self, value: Value, config: ChannelConfig) -> None:
        self._value = value
        self._config = config

    def get_status(self) -> Optional[ChannelStatus]:
        status = None
        v_alarm = self._value.alarm
        if v_alarm.changed:
            status = ChannelStatus(
                quality=CHANNEL_QUALITY_MAP[v_alarm.severity],
                message=v_alarm.message,
                mutable=True,
            )
        return status

    def get_time(self) -> Optional[ChannelTime]:
        time = None
        v_timestamp = self._value.timeStamp
        if v_timestamp.changed:
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
    def __init__(self, value: Value, config: ChannelConfig) -> None:
        super().__init__(value, config)
        type_specifier = value.type()["value"]
        if type_specifier.startswith("a"):
            self.is_array = True
            type_specifier = type_specifier[1:]
        else:
            self.is_array = False
        self.is_number = type_specifier in NUMBER_TYPES
        if self.is_number:
            display_form, precision, units = self.get_form_precision_units()
            if self.is_array:
                formatter = ChannelFormatter.for_ndarray(display_form, precision, units)
            else:
                formatter = ChannelFormatter.for_number(display_form, precision, units)
        else:
            formatter = ChannelFormatter()
        self._formatter = formatter

    def get_form_precision_units(self) -> Tuple[DisplayForm, int, str]:
        v_display = self._value.display
        try:
            form = DISPLAY_FORM_MAP[v_display.form.index]
            precision = v_display.precision
        except AttributeError:
            # Test version doesn't have these
            form = DisplayForm.DEFAULT
            precision = 3
        units = v_display.units
        if self._config:
            form = self._config.display_form or form
        return (form, precision, units)

    def get_value(self) -> Optional[ChannelValue]:
        value = None
        if self._value.changed("value"):
            value = ChannelValue(self._value.value, self._formatter)
        return value

    def get_display(self) -> Optional[ChannelDisplay]:
        display = None
        v_display = self._value.display
        if v_display.changed:
            display = ChannelDisplay(
                description=v_display.description, role="RW", widget=Widget.TEXTINPUT
            )
            if self.is_number:
                v_control = self._value.control
                v_value_alarm = self._value.valueAlarm
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
            update_display(display, self._config)
        return display


class EnumPVAChannel(PVAChannel):
    def __init__(self, value: Value, config: ChannelConfig) -> None:
        super().__init__(value, config)
        self._formatter = ChannelFormatter.for_enum(value["value.choices"])

    def get_value(self) -> Optional[ChannelValue]:
        value = None
        v_value = self._value.value
        if v_value.changed:
            value = ChannelValue(v_value.index, self._formatter)
        return value

    def get_display(self) -> Optional[ChannelDisplay]:
        display = None
        v_value = self._value.value
        if v_value.changed:
            display = ChannelDisplay(
                description="", role="RW", widget=Widget.COMBO, choices=v_value.choices,
            )
            update_display(display, self._config)
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
        self, channel_id: str, timeout: float, config: ChannelConfig
    ) -> Channel:
        try:
            value = await asyncio.wait_for(self.ctxt.get(channel_id), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while getting %s" % channel_id)
        channel = CHANNEL_CLASS[value.getID()](value, config)
        return channel

    async def put_channel(
        self, channel_id: str, value, timeout: float, config: ChannelConfig
    ) -> Channel:
        try:
            await asyncio.wait_for(self.ctxt.put(channel_id, value), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while putting to %s" % channel_id)
        channel = await self.get_channel(channel_id, timeout, config)
        return channel

    async def subscribe_channel(
        self, channel_id: str, config: ChannelConfig
    ) -> AsyncIterator[Channel]:
        q: asyncio.Queue[Value] = asyncio.Queue()
        m = self.ctxt.monitor(channel_id, q.put)
        try:
            # This will hold the current version of alarm data
            last_alarm = None
            while True:
                value = await q.get()
                # Alarms are always published, but we only want to display it
                # if it has changed
                v_alarm = value.alarm
                if v_alarm.changed and v_alarm == last_alarm:
                    v_alarm.unmark()
                last_alarm = v_alarm
                channel = CHANNEL_CLASS[value.getID()](value, config)
                yield channel
        finally:
            m.close()
