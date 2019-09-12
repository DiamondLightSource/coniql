import traceback
from typing import Tuple

from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLNonNull,
    GraphQLString, GraphQLArgument, GraphQLFloat
)

from coniql.plugin import Plugin
from coniql._types import Channel
from coniql.util import GqlMaker


class ConiqlSchema(GraphQLSchema):
    def __init__(self):
        self.plugins = {}
        self.maker = GqlMaker()
        self.channel_type = self.maker.make_gql_type(Channel)
        self.any_type = self.maker.types["Any"]
        super(ConiqlSchema, self).__init__(
            types=list(self.maker.types.values()),
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

    def plugin_channel(self, id: str) -> Tuple[Plugin, str]:
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
        plugin, channel_id = self.plugin_channel(id)
        data = await plugin.get_channel(channel_id, timeout)
        data["id"] = id
        return data

    async def put_channel(self, root, info, id: str, value, timeout: float):
        plugin, channel_id = self.plugin_channel(id)
        data = await plugin.put_channel(channel_id, value, timeout)
        data["id"] = id
        return data

    async def subscribe_channel(self, root, info, id: str):
        try:
            plugin, channel_id = self.plugin_channel(id)
            async for data in plugin.subscribe_channel(channel_id):
                data["id"] = id
                yield dict(subscribeChannel=data)
        except Exception as e:
            # TODO: I'm sure it's possible to raise an exception from a subscription...
            message = "%s: %s" % (e.__class__.__name__, e)
            d = dict(subscribeChannel=dict(id=id, status=dict(
                quality="ALARM", message=message, mutable=False)))
            yield d
            traceback.print_exc()
            raise

    def destroy(self):
        for plugin in set(self.plugins.values()):
            plugin.destroy()
        self.plugins = None


