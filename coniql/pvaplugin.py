import asyncio
import base64
from pathlib import Path

from p4p.client.asyncio import Context, Value

from .plugin import Plugin
from ._types import NumberType, ChannelQuality, DisplayForm, Range, \
    NumberDisplay, Channel, ChannelStatus, Time, EnumMeta, NumberMeta, \
    ObjectMeta, ArrayWrapper

# https://mdavidsaver.github.io/p4p/values.html
NUMBER_TYPES = {
    'b': NumberType.INT8,
    'B': NumberType.UINT8,
    'h': NumberType.INT16,
    'H': NumberType.UINT16,
    'i': NumberType.INT32,
    'I': NumberType.UINT32,
    'l': NumberType.INT64,
    'L': NumberType.UINT64,
    'f': NumberType.FLOAT32,
    'd': NumberType.FLOAT64,
}

OTHER_TYPES = {
    "?": "Boolean",
    "s": "String"
}

# Map from alarm.severity to ChannelQuality string
CHANNEL_QUALITY_MAP = [
    ChannelQuality.VALID,
    ChannelQuality.WARNING,
    ChannelQuality.ALARM,
    ChannelQuality.INVALID,
    ChannelQuality.UNDEFINED,
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


def label(channel_id):
    return channel_id.split(":")[-1].split(".")[0].title()


def convert_value(value: Value, channel: Channel):
    type_specifier = value.type()["value"]
    scalar_types = list(NUMBER_TYPES) + list(OTHER_TYPES)
    assert type_specifier in scalar_types, \
        "Expected a scalar type, got %r" % type_specifier
    if type_specifier in ("l", "L"):
        # 64-bit signed and unsigned numbers in javascript can overflow, use
        # a string conversion
        channel.value = str(value.value)
    else:
        # Native type is fine
        channel.value = value.value


def convert_value_array(value: Value, channel: Channel):
    type_specifier = value.type()["value"]
    assert type_specifier[0] == "a", \
        "Expected an array type, got %r" % type_specifier
    type_specifier = type_specifier[1:]
    if type_specifier in NUMBER_TYPES:
        channel.value = ArrayWrapper(value.value)
    else:
        raise ValueError("Don't support %r at the moment" % type_specifier)


def convert_alarm(value: Value, channel: Channel):
    v_alarm = value.alarm
    channel.status = ChannelStatus(
        quality=CHANNEL_QUALITY_MAP[v_alarm.severity],
        message=v_alarm.message,
        mutable=True
    )


def convert_timestamp(value: Value, channel: Channel):
    v_timestamp = value.timeStamp
    channel.time = Time(
        seconds=v_timestamp.secondsPastEpoch + v_timestamp.nanoseconds * 1e-9,
        nanoseconds=v_timestamp.nanoseconds,
        userTag=v_timestamp.userTag
    )


def convert_display(value: Value, channel: Channel):
    type_specifier = value.type()["value"]
    v_display = value.display
    meta_args = dict(
        description=v_display.description,
        label=label(channel.id)
    )
    if type_specifier.startswith("a"):
        meta_args["tags"] = ["widget:table", "role:user"]
        meta_args["array"] = True
        type_specifier = type_specifier[1:]
    else:
        meta_args["tags"] = ["widget:textinput", "role:user"]
        meta_args["array"] = False
    if type_specifier in NUMBER_TYPES:
        v_control = value.control
        v_value_alarm = value.valueAlarm
        display = NumberDisplay(
            controlRange=Range(
                min=v_control.limitLow,
                max=v_control.limitHigh),
            displayRange=Range(
                min=v_display.limitLow,
                max=v_display.limitHigh),
            alarmRange=Range(
                min=v_value_alarm.lowAlarmLimit,
                max=v_value_alarm.highAlarmLimit),
            warningRange=Range(
                min=v_value_alarm.lowWarningLimit,
                max=v_value_alarm.highWarningLimit),
            units=v_display.units,
            precision=v_display.precision,
            form=DISPLAY_FORM_MAP[v_display.form.choices[v_display.form.index]])
        channel.meta = NumberMeta(
            numberType=NUMBER_TYPES[type_specifier],
            display=display,
            **meta_args)
    elif type_specifier in OTHER_TYPES:
        channel.meta = ObjectMeta(
            type=OTHER_TYPES[type_specifier],
            **meta_args)
    else:
        raise ValueError("Can't deal with type specifier %r" % type_specifier)


def convert_enum_value(value: Value, channel: Channel):
    channel.value = value.value.index


def convert_enum_choices(value: Value, channel: Channel):
    channel.meta = EnumMeta(
        description=channel.id,
        tags=["widget:combo", "role:user"],
        label=label(channel.id),
        choices=value["value.choices"],
        array=False,
    )


CONVERTERS = {
    "epics:nt/NTScalar:1.0": {
        "value": convert_value,
        "alarm": convert_alarm,
        "timeStamp": convert_timestamp,
        "display": convert_display,
        "control": convert_display,
        "valueAlarm": convert_display,
    },
    "epics:nt/NTScalarArray:1.0": {
        "value": convert_value_array,
        "alarm": convert_alarm,
        "timeStamp": convert_timestamp,
        "display": convert_display,
        "control": convert_display,
        "valueAlarm": convert_display,
    },
    "epics:nt/NTEnum:1.0": {
        "value.index": convert_enum_value,
        "value.choices": convert_enum_choices,
        "alarm": convert_alarm,
        "timeStamp": convert_timestamp
    }
}


DB = Path(__file__).parent / "database.db"


async def run_ioc():
    cmd = f'/scratch/base-7.0.2.2/bin/linux-x86_64/softIocPVA -d {DB}'
    print(f'{cmd!r}')
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')


class PVAPlugin(Plugin):
    def __init__(self):
        self.ctxt = Context("pva", nt=False)
        self.ioc = None

    async def get_channel(self, channel_id: str, timeout: float) -> Channel:
        try:
            value = await asyncio.wait_for(self.ctxt.get(channel_id), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while getting %s" % channel_id)
        # Put in channel id so converters can see it
        channel = Channel(id=channel_id)
        converters = CONVERTERS[value.getID()]
        for convert in set(converters.values()):
            convert(value, channel)
        return channel

    async def put_channel(self, channel_id: str, value, timeout: float):
        # TODO: make enums work again by getting and updating
        try:
            await asyncio.wait_for(self.ctxt.put(channel_id, value), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while putting to %s" % channel_id)
        channel = await self.get_channel(channel_id, timeout)
        return channel

    async def subscribe_channel(self, channel_id: str):
        q = asyncio.Queue()
        m = self.ctxt.monitor(channel_id, q.put)
        try:
            # This will hold the current version of alarm data
            last_status = None
            value = await q.get()
            converters = CONVERTERS[value.getID()]
            while True:
                channel = Channel(id=channel_id)
                # Work out which converters to call
                triggers = value.changedSet(
                    parents=True).intersection(converters)
                # Add any data that has changed
                for convert in set(converters[x] for x in triggers):
                    convert(value, channel)
                # Alarms are always published, but we only want to display it
                # if it has changed
                if channel.status:
                    if last_status == channel.status:
                        channel.status = None
                    else:
                        last_status = channel.status
                yield channel
                value = await q.get()  # type: Value
        finally:
            m.close()

    def startup(self):
        # Need asyncio, so have to do it here
        self.ioc = asyncio.create_task(run_ioc())

    def shutdown(self):
        self.ctxt.close()
