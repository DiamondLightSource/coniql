import asyncio
from pathlib import Path
from typing import List, Tuple

from graphql import (
    GraphQLObjectType, build_schema,
    GraphQLArgument as A,
    GraphQLField as F,
    GraphQLNonNull as NN,
    GraphQLFloat, GraphQLString,
    GraphQLSchema, GraphQLInt, GraphQLEnumType)
from p4p.client.asyncio import Context, Value

from coniql.util import field_from_resolver
from coniql.resolvers import say_hello


SCHEMA = Path(__file__).parent / "schema.graphql"

with open(SCHEMA) as f:
    schema = build_schema(f.read())


float_scalar_type = schema.get_type("FloatScalar")
assert isinstance(float_scalar_type, GraphQLObjectType)

float_leaves = set()


def add_leaves(node, path=()):
    # type: (GraphQLObjectType, Tuple[str, ...]) -> None
    for name, field in node.fields.items():
        if isinstance(field.type, GraphQLObjectType):
            add_leaves(field.type, path + (name,))
        else:
            float_leaves.add(".".join(path + (name,)))


def patch_numeric_enum(enum_name: str):
    """Patch SDL defined enums to have 0 indexed numeric values"""
    enum_type = schema.get_type(enum_name)  # type: GraphQLEnumType
    for i, value in enumerate(enum_type.values.values()):
        value.value = i


add_leaves(float_scalar_type)
patch_numeric_enum("AlarmSeverity")
patch_numeric_enum("AlarmStatus")
patch_numeric_enum("DisplayForm")


async def subscribe_float(root, info, channel: str):
    with Context("pva", unwrap={}) as ctxt:
        q = asyncio.Queue()
        ctxt.monitor(channel, q.put)
        # This will hold the current version of everything
        cached_data = {}
        while True:
            value = await q.get()  # type: Value
            data = dict(typeid=value.getID())
            # Add any data that has changed
            for changed in value.changedSet():
                # Special case DisplayForm
                if changed == "display.form.index":
                    changed = "display.form"
                # If we don't want to publish it, drop it
                if changed not in float_leaves:
                    continue
                # Changed is something like display.form.choices
                split = changed.split(".")
                # Alarms are always published, but we only want to display it
                # if it has changed
                if split[0] == "alarm":
                    alarm = cached_data.get("alarm", {})
                    if alarm.get(split[1]) == getattr(value.alarm, split[1]):
                        # Same as cached value, no need to change
                        continue
                d = data
                cd = cached_data
                v = value
                # Walk down to N-1 level
                for k in split[:-1]:
                    d = d.setdefault(k, {})
                    cd = cd.setdefault(k, {})
                    v = getattr(v, k)
                # For the last level, set it on the structure directly
                k = split[-1]
                v = getattr(v, split[-1])
                # Special case DisplayForm
                if changed == "display.form":
                    v = v.index
                d[k] = v
                cd[k] = v
            yield dict(subscribeFloatScalar=data)

subscription_type = GraphQLObjectType('RootSubscriptionType', dict(
    subscribeFloatScalar=F(
        NN(float_scalar_type),
        subscribe=subscribe_float,
        args=dict(
            channel=A(NN(GraphQLString), description="The channel name")))))


query_type = GraphQLObjectType('RootQueryType', dict(
    hello=field_from_resolver(say_hello)
))


schema = GraphQLSchema(query=query_type, subscription=subscription_type)
