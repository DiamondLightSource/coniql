import base64
from pathlib import Path
import asyncio
from concurrent.futures import TimeoutError

from graphql import build_schema, GraphQLEnumType, GraphQLResolveInfo
from p4p.client.asyncio import Value, Context

SCHEMA = Path(__file__).parent / "schema.graphql"

with open(SCHEMA) as f:
    schema = build_schema(f.read())


# Make sure that these enums have integer values that map to the ones we get
# from PVA
def patch_numeric_enum(enum_name: str):
    """Patch SDL defined enums to have 0 indexed numeric values"""
    enum_type = schema.get_type(enum_name)  # type: GraphQLEnumType
    for i, value in enumerate(enum_type.values.values()):
        value.value = i


patch_numeric_enum("AttributeQuality")
patch_numeric_enum("DisplayForm")


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
            datatype=NUMBER_TYPES[type_specifier],
            # https://stackoverflow.com/a/6485943
            base64=base64.b64encode(value.value).decode()
        )
    else:
        raise ValueError("Don't support %r at the moment" % type_specifier)
    data["value"] = v


def convert_alarm(value, data):
    alarm = value.alarm
    data["status"] = dict(
        quality=alarm.severity,
        message=alarm.message)


def convert_timestamp(value, data):
    timestamp = value.timeStamp
    data["time"] = dict(
        seconds=timestamp.secondsPastEpoch,
        nanoseconds=timestamp.nanoseconds,
        userTag=timestamp.userTag
    )


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


def label(channel_id):
    return channel_id.split(":")[-1].split(".")[0].title()


def convert_display(value, data):
    type_specifier = value.type()["value"]
    display = value.display
    meta = dict(
        description=display.description,
        tags=[],
        mutable=True,
        label=label(data["id"]),
        role="USER",
    )
    if type_specifier.startswith("a"):
        meta["array"] = True
        type_specifier = type_specifier[1:]
    else:
        meta["array"] = False
    if type_specifier in NUMBER_TYPES:
        meta["__typename"] = "NumberMeta"
        meta["datatype"] = NUMBER_TYPES[type_specifier]
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
            form=display.form.index)
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
        tags=[],
        mutable=True,
        label=label(data["id"]),
        role="USER",
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


async def subscribe_attribute(root, info: GraphQLResolveInfo, id: str):
    ctxt = info.context
    q = asyncio.Queue()
    m = ctxt.monitor(id, q.put)
    try:
        # This will hold the current version of alarm data
        last_status = None
        value = await q.get()
        converters = CONVERTERS[value.getID()]
        while True:
            data = dict(id=id)
            # Work out which converters to call
            triggers = value.changedSet(parents=True).intersection(converters)
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
            yield dict(subscribeAttribute=data)
            value = await q.get()  # type: Value
    finally:
        m.close()


async def get_attribute(root, info: GraphQLResolveInfo, id: str,
                        timeout: float):
    ctxt = info.context  # type: Context
    try:
        value = await asyncio.wait_for(ctxt.get(id), timeout)
    except TimeoutError:
        raise TimeoutError("Timeout while getting %s" % id)
    data = dict(id=id)
    converters = CONVERTERS[value.getID()]
    for convert in set(converters.values()):
        convert(value, data)
    return data


async def put_attribute(root, info: GraphQLResolveInfo, id: str, value,
                        timeout: float):
    ctxt = info.context  # type: Context
    try:
        await asyncio.wait_for(ctxt.put(id, value), timeout)
    except TimeoutError:
        raise TimeoutError("Timeout while putting to %s" % id)
    # TODO: return get?
    return value


schema.query_type.fields["getAttribute"].resolve = \
    get_attribute
schema.subscription_type.fields["subscribeAttribute"].subscribe = \
    subscribe_attribute
schema.mutation_type.fields["putAttribute"].resolve = \
    put_attribute


