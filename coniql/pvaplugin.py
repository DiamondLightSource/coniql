import asyncio
import base64

from p4p.client.asyncio import Context, Value

from .plugin import Plugin


# https://mdavidsaver.github.io/p4p/values.html
NUMBER_TYPES = {
    'b': "INT8",
    'B': 'UINT8',
    'h': "INT16",
    'H': 'UINT16',
    'i': "INT32",
    'I': 'UINT32',
    'l': "INT64",
    'L': 'UINT64',
    'f': "FLOAT32",
    'd': 'FLOAT64',
}

OTHER_TYPES = {
    "?": "Boolean",
    "s": "String"
}

# Map from alarm.severity to ChannelQuality string
CHANNEL_QUALITY_MAP = ["VALID", "WARNING", "ALARM", "INVALID", "UNDEFINED"]


def label(channel_id):
    return channel_id.split(":")[-1].split(".")[0].title()


def convert_value(value, data):
    type_specifier = value.type()["value"]
    scalar_types = list(NUMBER_TYPES) + list(OTHER_TYPES)
    assert type_specifier in scalar_types, \
        "Expected a scalar type, got %r" % type_specifier
    if type_specifier in ("l", "L"):
        # 64-bit signed and unsigned numbers in javascript can overflow, use
        # a string conversion
        v = str(value.value)
    else:
        # Native type is fine
        v = value.value
    data["value"] = v


def convert_value_array(value, data):
    type_specifier = value.type()["value"]
    assert type_specifier[0] == "a", \
        "Expected an array type, got %r" % type_specifier
    type_specifier = type_specifier[1:]
    if type_specifier in NUMBER_TYPES:
        v = dict(
            numberType=NUMBER_TYPES[type_specifier],
            # https://stackoverflow.com/a/6485943
            base64=base64.b64encode(value.value).decode()
        )
    else:
        raise ValueError("Don't support %r at the moment" % type_specifier)
    data["value"] = v


def convert_alarm(value, data):
    alarm = value.alarm
    data["status"] = dict(
        quality=CHANNEL_QUALITY_MAP[alarm.severity],
        message=alarm.message,
        mutable=True
    )


def convert_timestamp(value, data):
    timestamp = value.timeStamp
    nanoseconds = timestamp.nanoseconds
    data["time"] = dict(
        seconds=timestamp.secondsPastEpoch + nanoseconds * 1e-9,
        nanoseconds=nanoseconds,
        userTag=timestamp.userTag
    )


def convert_display(value, data):
    type_specifier = value.type()["value"]
    display = value.display
    meta = dict(
        description=display.description,
        label=label(data["id"])
    )
    if type_specifier.startswith("a"):
        meta["tags"] = ["widget:table", "role:user"]
        meta["array"] = True
        type_specifier = type_specifier[1:]
    else:
        meta["tags"] = ["widget:textinput", "role:user"]
        meta["array"] = False
    if type_specifier in NUMBER_TYPES:
        meta["__typename"] = "NumberMeta"
        meta["numberType"] = NUMBER_TYPES[type_specifier]
        control = value.control
        value_alarm = value.valueAlarm
        meta["display"] = dict(
            controlRange=dict(
                min=control.limitLow,
                max=control.limitHigh),
            displayRange=dict(
                min=display.limitLow,
                max=display.limitHigh),
            alarmRange=dict(
                min=value_alarm.lowAlarmLimit,
                max=value_alarm.highAlarmLimit),
            warningRange=dict(
                min=value_alarm.lowWarningLimit,
                max=value_alarm.highWarningLimit),
            units=display.units,
            precision=display.precision,
            form=display.form.choices[display.form.index].upper())
    elif type_specifier in OTHER_TYPES:
        meta["__typename"] = "ObjectMeta"
        meta["type"] = OTHER_TYPES[type_specifier]
    else:
        raise ValueError("Can't deal with type specifier %r" % type_specifier)
    data["meta"] = meta


def convert_enum_value(value, data):
    data["value"] = value["value.choices"][value["value.index"]]


def convert_enum_choices(value, data):
    data["meta"] = dict(
        __typename="ChoiceMeta",
        description=data["id"],
        tags=["widget:combo", "role:user"],
        label=label(data["id"]),
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
        "value.value": convert_enum_value,
        "value.choices": convert_enum_choices,
        "alarm": convert_alarm,
        "timeStamp": convert_timestamp
    }
}


class PVAPlugin(Plugin):
    def __init__(self):
        self.ctxt = Context("pva", unwrap={})

    async def get_channel(self, channel_id: str, timeout: float):
        try:
            value = await asyncio.wait_for(self.ctxt.get(channel_id), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while getting %s" % channel_id)
        data = dict(id=channel_id)
        converters = CONVERTERS[value.getID()]
        for convert in set(converters.values()):
            convert(value, data)
        return data

    async def put_channel(self, channel_id: str, value, timeout: float):
        try:
            await asyncio.wait_for(self.ctxt.put(channel_id, value), timeout)
        except TimeoutError:
            raise TimeoutError("Timeout while putting to %s" % channel_id)
        value = await asyncio.wait_for(self.ctxt.get(channel_id), timeout)
        return value.value

    async def subscribe_channel(self, channel_id: str):
        q = asyncio.Queue()
        m = self.ctxt.monitor(channel_id, q.put)
        print(channel_id)
        try:
            # This will hold the current version of alarm data
            last_status = None
            value = await q.get()
            converters = CONVERTERS[value.getID()]
            while True:
                data = dict(id=channel_id)
                # Work out which converters to call
                triggers = value.changedSet(
                    parents=True).intersection(converters)
                # Add any data that has changed
                for convert in set(converters[x] for x in triggers):
                    convert(value, data)
                # Alarms are always published, but we only want to display it
                # if it has changed
                if "status" in data:
                    if last_status == data["status"]:
                        del data["status"]
                    else:
                        last_status = data["status"]
                yield data
                value = await q.get()  # type: Value
        finally:
            m.close()

    def destroy(self):
        self.ctxt.close()
