import base64
import traceback
from typing import Tuple, Dict

from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLNonNull,
    GraphQLString, GraphQLArgument, GraphQLFloat, GraphQLScalarType,
    GraphQLOutputType
)

from coniql.plugin import Plugin
from coniql._types import Channel, ArrayWrapper
from coniql.util import make_gql_type


def serialize_any(value):
    if isinstance(value, ArrayWrapper):
        return dict(
            numberType=value.array.dtype.name.upper(),
            # https://stackoverflow.com/a/6485943
            base64=base64.b64encode(value.array).decode()
        )
    else:
        return value


class ConiqlSchema(GraphQLSchema):
    def __init__(self):
        self.any_type = GraphQLScalarType("Any", serialize=serialize_any)
        self.types: Dict[str, GraphQLOutputType] = dict(Any=self.any_type)
        self.channel_type = make_gql_type(Channel, self.types)
        self.plugins: Dict[str, Plugin] = {}
        super(ConiqlSchema, self).__init__(
            types=list(self.types.values()),
            query=GraphQLObjectType('QueryType', self._query_fields),
            mutation=GraphQLObjectType('MutationType', self._mutation_fields),
            subscription=GraphQLObjectType(
                'SubscriptionType', self._subscription_fields))

    def _query_fields(self):
        return dict(
            getChannel=GraphQLField(self.channel_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Channel to connect to"),
                timeout=GraphQLArgument(
                    GraphQLFloat, 5,
                    description="How long to wait, negative is forever"),
            ), resolve=self.get_channel),
        )

    def _mutation_fields(self):
        return dict(
            putChannel=GraphQLField(self.channel_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Channel to connect to"),
                value=GraphQLArgument(
                    GraphQLNonNull(self.any_type),
                    description="The ID of the Channel to connect to"),
                timeout=GraphQLArgument(
                    GraphQLFloat, 5,
                    description="How long to wait, negative is forever"),
            ), resolve=self.put_channel),
        )

    def _subscription_fields(self):
        return dict(
            subscribeChannel=GraphQLField(self.channel_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Channel to connect to"),
            ), subscribe=self.subscribe_channel),
        )

    def _plugin_channel(self, id: str) -> Tuple[Plugin, str]:
        split = id.split("://", 1)
        if len(split) == 1:
            scheme, channel_id = "", id
        else:
            scheme, channel_id = split
        try:
            plugin = self.plugins[scheme]
        except KeyError:
            raise ValueError("No plugin registered for scheme '%s'" % scheme)
        return plugin, channel_id

    def add_plugin(self, name: str, plugin: Plugin, set_default=False):
        self.plugins[name] = plugin
        if set_default:
            self.plugins[""] = plugin

    async def get_channel(self, root, info, id: str, timeout: float):
        plugin, channel_id = self._plugin_channel(id)
        data = await plugin.get_channel(channel_id, timeout)
        data.id = id
        return data

    async def put_channel(self, root, info, id: str, value, timeout: float):
        plugin, channel_id = self._plugin_channel(id)
        data = await plugin.put_channel(channel_id, value, timeout)
        data.id = id
        return data

    async def subscribe_channel(self, root, info, id: str):
        try:
            plugin, channel_id = self._plugin_channel(id)
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


