import base64
import traceback
import dataclasses
from typing import Tuple, Dict

from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLNonNull,
    GraphQLString, GraphQLArgument, GraphQLFloat, GraphQLScalarType,
    GraphQLOutputType
)

from coniql.plugin import Plugin
from coniql._types import Channel, ArrayWrapper, Function, Readback, Time
from coniql.util import make_gql_type


def serialize_any(value):
    if isinstance(value, ArrayWrapper):
        return dict(
            numberType=value.array.dtype.name.upper(),
            # https://stackoverflow.com/a/6485943
            base64=base64.b64encode(value.array).decode()
        )
    elif dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    else:
        return value


class ConiqlSchema(GraphQLSchema):
    def __init__(self):
        self.any_type = GraphQLScalarType("Any", serialize=serialize_any)
        self.types: Dict[str, GraphQLOutputType] = dict(Any=self.any_type)
        self.readback_type = make_gql_type(Readback, self.types)
        self.channel_type = make_gql_type(Channel, self.types)
        self.function_type = make_gql_type(Function, self.types)
        self.plugins: Dict[str, Plugin] = {}
        super(ConiqlSchema, self).__init__(
            types=list(self.types.values()),
            query=GraphQLObjectType('QueryType', self._query_fields),
            mutation=GraphQLObjectType('MutationType', self._mutation_fields),
            subscription=GraphQLObjectType(
                'SubscriptionType', self._subscription_fields))

    def _query_fields(self):
        return dict(
            readChannel=GraphQLField(self.readback_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Channel to connect to"),
                timeout=GraphQLArgument(
                    GraphQLFloat, 5,
                    description="How long to wait, negative is forever")
            ), resolve=self.read_channel),
            getChannel=GraphQLField(self.channel_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Channel to connect to")
            ), resolve=self.get_channel),
            getFunction=GraphQLField(self.function_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Function to inspect"),
                timeout=GraphQLArgument(
                    GraphQLFloat, 5,
                    description="How long to wait, negative is forever"),
            ), resolve=self.get_function),

        )

    def _mutation_fields(self):
        return dict(
            putChannel=GraphQLField(self.channel_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Channel to connect to"),
                value=GraphQLArgument(
                    GraphQLNonNull(self.any_type),
                    description="The value to put to the Channel"),
                timeout=GraphQLArgument(
                    GraphQLFloat, 5,
                    description="How long to wait, negative is forever"),
            ), resolve=self.put_channel),
            callFunction=GraphQLField(self.any_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Function to call"),
                arguments=GraphQLArgument(
                    GraphQLNonNull(self.any_type),
                    description="The arguments to pass to the Function"),
                timeout=GraphQLArgument(
                    GraphQLFloat, 5,
                    description="How long to wait, negative is forever"),
            ), resolve=self.call_function),
        )

    def _subscription_fields(self):
        return dict(
            subscribeChannel=GraphQLField(self.readback_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Channel to connect to"),
            ), subscribe=self.subscribe_channel),
        )

    def _plugin_object_id(self, id: str) -> Tuple[Plugin, str]:
        split = id.split("://", 1)
        if len(split) == 1:
            scheme, object_id = "", id
        else:
            scheme, object_id = split
        try:
            plugin = self.plugins[scheme]
        except KeyError:
            raise ValueError("No plugin registered for scheme '%s'" % scheme)
        return plugin, object_id

    def add_plugin(self, name: str, plugin: Plugin, set_default=False):
        self.plugins[name] = plugin
        if set_default:
            self.plugins[""] = plugin

    async def read_channel(self, root, info, id: str, timeout: float):
        plugin, channel_id = self._plugin_object_id(id)
        data = await plugin.read_channel(channel_id, timeout)
        # data.id = id
        return data

    async def get_channel(self, root, info, id: str):
        plugin, channel_id = self._plugin_object_id(id)
        data = await plugin.get_channel(channel_id)
        data.id = id
        return data

    async def get_function(self, root, info, id: str, timeout: float):
        plugin, function_id = self._plugin_object_id(id)
        data = await plugin.get_function(function_id, timeout)
        data.id = id
        return data

    async def put_channel(self, root, info, id: str, value, timeout: float):
        plugin, channel_id = self._plugin_object_id(id)
        data = await plugin.put_channel(channel_id, value, timeout)
        data.id = id
        return data

    async def call_function(self, root, info, id: str, arguments,
                            timeout: float):
        plugin, function_id = self._plugin_object_id(id)
        data = await plugin.call_function(function_id, arguments, timeout)
        return data

    async def subscribe_channel(self, root, info, id: str):
        try:
            plugin, channel_id = self._plugin_object_id(id)
            async for data in plugin.subscribe_channel(channel_id):
                data.id = id
                yield dict(subscribeChannel=data)
        except Exception as e:
            # TODO: I'm sure it's possible to raise an exception from a subscription...
            message = "%s: %s" % (e.__class__.__name__, e)
            d = dict(subscribeChannel=dict(id=id, status=dict(
                quality="ALARM", message=message, mutable=False)))
            yield d
            traceback.print_exc()
            raise

    async def startup(self, app):
        for plugin in set(self.plugins.values()):
            plugin.startup()

    async def shutdown(self, app):
        for plugin in set(self.plugins.values()):
            plugin.shutdown()
        self.plugins = None


