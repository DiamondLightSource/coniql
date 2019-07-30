from enum import Enum
import asyncio

from graphql import (
    GraphQLObjectType,
    GraphQLArgument as A,
    GraphQLField as F,
    GraphQLNonNull as NN,
    GraphQLEnumType as E,
    GraphQLFloat, GraphQLString,
    GraphQLSchema, GraphQLInt)
from p4p.client.asyncio import Context, Value

from coniql.util import field_from_resolver
from coniql.resolvers import say_hello


query_type = GraphQLObjectType('RootQueryType', dict(
    hello=field_from_resolver(say_hello)
))


class AlarmSeverity(Enum):
    NO_ALARM, MINOR_ALARM, MAJOR_ALARM, INVALID_ALARM, UNDEFINED_ALARM = \
        range(5)


class AlarmStatus(Enum):
    """An alarm status"""
    NO_STATUS, DEVICE_STATUS, DRIVER_STATUS, RECORD_STATUS, DB_STATUS, \
        CONF_STATUS, UNDEFINED_STATUS, CLIENT_STATUS = \
        range(8)

class DisplayForm(Enum):
    DEFAULT, STRING, BINARY, DECIMAL, HEX, EXPONENTIAL, ENGINEERING = \
        range(7)


alarm_status_type = E('AlarmStatus', AlarmStatus)
alarm_severity_type = E('AlarmSeverity', AlarmSeverity)
alarm_type = GraphQLObjectType('Alarm', dict(
    severity=F(alarm_severity_type, description="How bad is the alarm"),
    status=F(alarm_status_type, description="What type of alarm is it"),
    message=F(GraphQLString, description="More info about the alarm"),
))

time_type = GraphQLObjectType('Time', dict(
    secondsPastEpoch=F(
        GraphQLFloat, description=
        "Seconds since Jan 1, 1970 00:00:00 UTC"),
    nanoseconds=F(
        GraphQLInt, description=
        "Nanoseconds relative to the secondsPastEpoch field"),
    userTag=F(
        GraphQLInt, description=
        "An integer value whose interpretation is deliberately undefined"),
))

float_scalar_type = GraphQLObjectType("FloatScalar", dict(
    typeid=F(NN(GraphQLString), description="Structure typeid"),
    value=F(GraphQLFloat, description="The value"),
    timeStamp=F(time_type, description="When value last updated"),
    alarm=F(alarm_type, description="The alarm value")
))

float_leaves = set()


def add_leaves(node, path=()):
    # type: (GraphQLObjectType) -> None
    for name, field in node.fields.items():
        if isinstance(field.type, GraphQLObjectType):
            add_leaves(field.type, path + (name,))
        else:
            float_leaves.add(".".join(path + (name,)))


add_leaves(float_scalar_type)


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
                d[k] = v
                cd[k] = v
            yield dict(subscribeFloatScalar=data)

subscription_type = GraphQLObjectType('RootSubscriptionType', dict(
    subscribeFloatScalar=F(
        NN(float_scalar_type),
        subscribe=subscribe_float,
        args=dict(
            channel=A(NN(GraphQLString), description="The channel name")))))


schema = GraphQLSchema(query=query_type, subscription=subscription_type)
