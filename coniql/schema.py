import asyncio

import graphql

from coniql.util import field_from_resolver
from coniql.resolvers import say_hello

query_type = graphql.GraphQLObjectType('RootQueryType', dict(
    hello=field_from_resolver(say_hello)
))

async def subscribe_time(root, info):
    for i in range(10):
        yield dict(time=str(i))
        await asyncio.sleep(1)

subscription_type = graphql.GraphQLObjectType('RootSubscriptionType', dict(
    time=graphql.GraphQLField(
graphql.GraphQLNonNull(graphql.GraphQLString), subscribe=subscribe_time
)))

schema = graphql.GraphQLSchema(query=query_type, subscription=subscription_type)
