import asyncio
import atexit
from typing import AsyncIterator, Callable, Dict, Optional

from p4p.client.asyncio import Context, Value

from coniql.coniql_schema import DisplayForm, Widget
from coniql.device_config import ChannelConfig
from coniql.plugin import Plugin
from coniql.types import (
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

# Map from alarm.severity to ChannelQuality string
CHANNEL_QUALITY_MAP = [
    "VALID",
    "WARNING",
    "ALARM",
    "INVALID",
    "UNDEFINED",
]

# Map from display form to DisplayForm enum
DISPLAY_FORM_MAP = {
    "Default": DisplayForm.DEFAULT,
    "String": DisplayForm.STRING,
    "Binary": DisplayForm.BINARY,
    "Decimal": DisplayForm.DECIMAL,
    "Hex": DisplayForm.HEX,
    "Exponential": DisplayForm.EXPONENTIAL,
    "Engineering": DisplayForm.ENGINEERING,
}


def convert_status(value: Value) -> Optional[ChannelStatus]:
    v_alarm = value.alarm
    status = ChannelStatus(
        quality=CHANNEL_QUALITY_MAP[v_alarm.severity],
        message=v_alarm.message,
        mutable=True,
    )
    return status


def convert_time(value: Value) -> Optional[ChannelTime]:
    v_timestamp = value.timeStamp
    time = ChannelTime(
        seconds=v_timestamp.secondsPastEpoch + v_timestamp.nanoseconds * 1e-9,
        nanoseconds=v_timestamp.nanoseconds,
        userTag=v_timestamp.userTag,
    )
    return time


class ScalarChannel(Channel):
    def __init__(self, value: Value) -> None:
        self._value = value
        type_specifier = value.type()["value"]
        if type_specifier.startswith("a"):
            self.is_array = True
            type_specifier = type_specifier[1:]
        else:
            self.is_array = False
        self.is_number = type_specifier in NUMBER_TYPES
        if self.is_number:
            if self.is_array:
                factory = ChannelFormatter.for_ndarray
            else:
                factory = ChannelFormatter.for_number
            formatter = factory(*self.get_form_precision_units())
        else:
            formatter = ChannelFormatter()
        self._formatter = formatter

    def get_form_precision_units(self) -> Tuple[DisplayForm, int, str]:
        v_display = self._value.display
        form = DISPLAY_FORM_MAP[v_display.form.choices[v_display.form.index]]
        precision = v_display.precision
        units = v_display.units
        return (form, precision, units)

    def get_value(self) -> Optional[ChannelValue]:
        value = ChannelValue(self._value.value, self._formatter)
        return value

    def get_status(self) -> Optional[ChannelStatus]:
        return convert_status(self._value)

    def get_time(self) -> Optional[ChannelTime]:
        return convert_time(self._value)

    def get_display(self) -> Optional[ChannelDisplay]:
        v_display = self._value.display
        display = ChannelDisplay(
            description=v_display.description, role="RW", widget=Widget.TEXTINPUT
        )
        if self.is_number:
            v_control = self._value.control
            v_value_alarm = self._value.valueAlarm
            display.controlRange = Range(min=v_control.limitLow, max=v_control.limitHigh)
            display.displayRange = Range(min=v_display.limitLow, max=v_display.limitHigh)
            display.alarmRange = Range(
                min=v_value_alarm.lowAlarmLimit, max=v_value_alarm.highAlarmLimit
            )
            display.warningRange = Range(
                min=v_value_alarm.lowWarningLimit, max=v_value_alarm.highWarningLimit
            )
            display.form, display.precision, display.units = self.get_form_precision_units()
        return display


class EnumChannel(Channel):
    def __init__(self, value: Value) -> None:
        self._value = value
        self._formatter = ChannelFormatter.for_enum(value["value.choices"])

    def get_value(self) -> Optional[ChannelValue]:
        value = ChannelValue(self._value.value, self._formatter)
        return value

    def get_status(self) -> Optional[ChannelStatus]:
        return convert_status(self._value)

    def get_time(self) -> Optional[ChannelTime]:
        return convert_time(self._value)

    def get_display(self) -> Optional[ChannelDisplay]:
        display = ChannelDisplay(
            description="",
            role="RW",
            widget=Widget.COMBO,
            choices=self._value["value.choices"],
        )
        return display



def update_display(display: ChannelDisplay, config: ChannelConfig):
    # Role defined by presence of PVs, delete modes without PV
    if config.read_pv is None:
        display.role = display.role[1:]
    if config.write_pv is None:
        display.role = display.role[:-1]
    # Override description and widget
    display.description = config.description
    display.widget = config.widget


Converter = Callable[[Value, Channel], None]

ntscalar_converters: Dict[str, Converter] = {
    "value": convert_value,
    "alarm": convert_alarm,
    "timeStamp": convert_timestamp,
    "display": convert_display,
    "control": convert_display,
    "valueAlarm": convert_display,
}

CONVERTERS: Dict[str, Dict[str, Converter]] = {
    "epics:nt/NTScalar:1.0": ntscalar_converters,
    "epics:nt/NTScalarArray:1.0": ntscalar_converters,
    "epics:nt/NTEnum:1.0": {
        "value.index": convert_enum_value,
        "value.choices": convert_enum_choices,
        "alarm": convert_alarm,
        "timeStamp": convert_timestamp,
    },
}


class PVAPlugin(Plugin):
    def __init__(self):
        self.ctxt = Context("pva", nt=False)
        atexit.register(self.ctxt.close)

    async def get_channel(
        self, channel_id: str, timeout: float, config: Optional[ChannelConfig]
    ) -> Channel:
        try:
            value = await asyncio.wait_for(self.ctxt.get(channel_id), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while getting %s" % channel_id)
        # Put in channel id so converters can see it
        channel = Channel(id=self.full_id(channel_id), value=ChannelValue(None))
        converters = CONVERTERS[value.getID()]
        for convert in set(converters.values()):
            convert(value, channel)
        if config and channel.display:
            update_display(channel.display, config)
        return channel

    async def put_channel(
        self, channel_id: str, value, timeout: float, config: Optional[ChannelConfig]
    ) -> Channel:
        # TODO: make enums work again by getting and updating
        try:
            await asyncio.wait_for(self.ctxt.put(channel_id, value), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while putting to %s" % channel_id)
        channel = await self.get_channel(channel_id, timeout, config)
        return channel

    async def subscribe_channel(
        self, channel_id: str, config: Optional[ChannelConfig]
    ) -> AsyncIterator[Channel]:
        q: asyncio.Queue[Value] = asyncio.Queue()
        m = self.ctxt.monitor(channel_id, q.put)
        try:
            # This will hold the current version of alarm data
            last_status = None
            value = await q.get()
            converters = CONVERTERS[value.getID()]
            formatter = ChannelFormatter()
            while True:
                channel = Channel(id=self.full_id(channel_id), value=ChannelValue(None))
                # Work out which converters to call
                triggers = value.changedSet(parents=True).intersection(converters)
                # Add any data that has changed
                for convert in set(converters[x] for x in triggers):
                    convert(value, channel)
                # Value should still be there
                assert channel.value, channel
                # Alarms are always published, but we only want to display it
                # if it has changed
                if channel.status:
                    if last_status == channel.status:
                        channel.status = None
                    else:
                        last_status = channel.status
                if channel.display:
                    formatter = channel.value.formatter
                    if config:
                        update_display(channel.display, config)
                if channel.value.value is None:
                    # Value didn't change, so delete it
                    channel.value = None
                else:
                    # Value did change, but display might not have, so restore
                    channel.value.formatter = formatter
                yield channel
                value = await q.get()
        finally:
            m.close()
