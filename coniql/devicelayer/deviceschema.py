import base64
import traceback
import dataclasses
from typing import Tuple, Dict

from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLNonNull,
    GraphQLString, GraphQLArgument, GraphQLFloat, GraphQLScalarType,
    GraphQLOutputType, GraphQLBoolean
)

from coniql.devicelayer.deviceplugin import DeviceLayer
from coniql.devicelayer.scanpointgen import GraphQLTrajectoryModel
from coniql.plugin import Plugin
from coniql._types import Channel, ArrayWrapper, Function, Readback
from coniql.util import make_gql_type
from device.pmac.control.trajectorymodel import TrajectoryModel


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
    def __init__(self, device_layer: DeviceLayer):
        self.any_type = GraphQLScalarType("Any", serialize=serialize_any)
        self.types: Dict[str, GraphQLOutputType] = dict(Any=self.any_type)
        self.readback_type = make_gql_type(Readback, self.types)
        self.channel_type = make_gql_type(Channel, self.types)
        self.device_layer = device_layer
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

        )

    def _mutation_fields(self):
        return dict(
            putChannel=GraphQLField(GraphQLBoolean, args=dict(
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
            scanPoints=GraphQLField(GraphQLBoolean, args=dict(
                pmac_id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description='ID of the pmac to scan'),
                model=GraphQLArgument(
                    GraphQLNonNull(GraphQLTrajectoryModel()),
                    description='Model of the trajectory to follow')
            ), resolve=self.scan_points)
        )

    def _subscription_fields(self):
        return dict(
            subscribeChannel=GraphQLField(self.readback_type, args=dict(
                id=GraphQLArgument(
                    GraphQLNonNull(GraphQLString),
                    description="The ID of the Channel to connect to"),
            ), subscribe=self.subscribe_channel),
        )

    async def read_channel(self, root, info, id: str, timeout: float):
        data = await self.device_layer.read_channel(id)
        # data.id = id
        return data

    async def get_channel(self, root, info, id: str):
        data = await self.device_layer.get_channel(id)
        # data.id = id
        return data

    async def put_channel(self, root, info, id: str, value, timeout: float):
        data = await self.device_layer.put_channel(id, value)
        # data.id = id
        return data

    async def subscribe_channel(self, root, info, id: str):
        try:
            async for data in self.device_layer.subscribe_channel(id):
                # data.id = id
                yield dict(subscribeChannel=data)
        except Exception as e:
            # TODO: I'm sure it's possible to raise an exception from a subscription...
            message = "%s: %s" % (e.__class__.__name__, e)
            d = dict(subscribeChannel=dict(id=id, status=dict(
                quality="ALARM", message=message, mutable=False)))
            yield d
            traceback.print_exc()
            raise

    async def scan_points(self, root, info, pmac_id: str,
                          model: TrajectoryModel):
        return await self.device_layer.scan_points(pmac_id, model)

    async def startup(self, app):
        self.device_layer.startup()

    async def shutdown(self, app):
        self.device_layer.shutdown()
