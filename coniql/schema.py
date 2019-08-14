from pathlib import Path
import asyncio
from concurrent.futures import TimeoutError
from typing import Tuple, Dict, Callable

from graphql import build_schema, GraphQLObjectType, GraphQLEnumType, \
    GraphQLResolveInfo
from p4p.client.asyncio import Value, Context

SCHEMA = Path(__file__).parent / "schema.graphql"

with open(SCHEMA) as f:
    schema = build_schema(f.read())


float_scalar_type = schema.get_type("FloatScalar")
assert isinstance(float_scalar_type, GraphQLObjectType)


# Make sure that these enums have integer values that map to the ones we get
# from PVA
def patch_numeric_enum(enum_name: str):
    """Patch SDL defined enums to have 0 indexed numeric values"""
    enum_type = schema.get_type(enum_name)  # type: GraphQLEnumType
    for i, value in enumerate(enum_type.values.values()):
        value.value = i


patch_numeric_enum("AlarmSeverity")
patch_numeric_enum("AlarmStatus")
patch_numeric_enum("DisplayForm")


# These are the converters from PVA Value to what GraphQL wants
float_field_set_data = {}  # type: Dict[str, Callable]


def add_set_data(node, path=()):
    # type: (GraphQLObjectType, Tuple[str, ...]) -> None
    for name, field in node.fields.items():
        if isinstance(field.type, GraphQLObjectType):
            # Is node
            add_set_data(field.type, path + (name,))
        else:
            # Is leaf
            str_path = ".".join(path + (name,))
            if str_path == "display.form":
                # Special case display form index
                def converter(current, data):
                    data.setdefault("display", {})["form"] = current
                float_field_set_data["display.form.index"] = converter
            else:
                def converter(current, data, n=name):
                    for p in path:
                        data = data.setdefault(p, {})
                    data[n] = current
                float_field_set_data[str_path] = converter


add_set_data(float_scalar_type)


async def subscribe_float(root, info: GraphQLResolveInfo, channel: str):
    ctxt = info.context
    q = asyncio.Queue()
    ctxt.monitor(channel, q.put)
    # This will hold the current version of alarm data
    last_alarm = {}
    while True:
        value = await q.get()  # type: Value
        data = dict(typeid=value.getID())
        # Add any data that has changed
        for changed in value.changedSet():
            set_data = float_field_set_data.get(changed, None)
            if set_data is None:
                continue
            split = changed.split(".")
            current = value[changed]
            # Alarms are always published, but we only want to display it
            # if it has changed
            if split[0] == "alarm":
                if last_alarm.get(changed, None) == current:
                    continue
                last_alarm[changed] = current
            # Add the value to data
            set_data(current, data)
        yield dict(subscribeFloatScalar=data)


async def get_float(root, info: GraphQLResolveInfo, channel: str,
                    timeout: float):
    ctxt = info.context  # type: Context
    try:
        value = await asyncio.wait_for(ctxt.get(channel), timeout)
    except TimeoutError:
        raise TimeoutError("Timeout while getting %s" % channel)
    data = dict(typeid=value.getID())
    for changed in value.changedSet():
        set_data = float_field_set_data.get(changed, None)
        if set_data:
            set_data(value[changed], data)
    return data


async def put_float(root, info: GraphQLResolveInfo, channel: str, value: float,
                    timeout: float):
    ctxt = info.context  # type: Context
    try:
        await asyncio.wait_for(ctxt.put(channel, value), timeout)
    except TimeoutError:
        raise TimeoutError("Timeout while putting to %s" % channel)


schema.query_type.fields["getFloatScalar"].resolve = \
    get_float
schema.subscription_type.fields["subscribeFloatScalar"].subscribe = \
    subscribe_float
schema.mutation_type.fields["putFloatScalar"].resolve = \
    put_float


