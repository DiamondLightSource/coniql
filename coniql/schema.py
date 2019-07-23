from graphql import (
    GraphQLObjectType,
    GraphQLArgument as A,
    GraphQLField as F,
    GraphQLNonNull as NN,
    GraphQLFloat, GraphQLString,
    GraphQLSchema)

from coniql.util import field_from_resolver
from coniql.resolvers import say_hello, subscribe_float

query_type = GraphQLObjectType('RootQueryType', dict(
    hello=field_from_resolver(say_hello)
))

float_scalar_type = GraphQLObjectType("FloatScalar", dict(
    typeid=F(NN(GraphQLString), description="Structure typeid"),
    value=F(NN(GraphQLFloat), description="The value"),
))


subscription_type = GraphQLObjectType('RootSubscriptionType', dict(
    subscribeFloatScalar=F(
        NN(float_scalar_type),
        subscribe=subscribe_float,
        args=dict(
            channel=A(NN(GraphQLString), description="The channel name")))))


schema = GraphQLSchema(query=query_type, subscription=subscription_type)
