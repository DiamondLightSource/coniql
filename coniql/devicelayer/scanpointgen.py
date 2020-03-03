from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Sequence

from graphql import (GraphQLInputObjectType, GraphQLInputField, GraphQLNonNull,
                     GraphQLString, GraphQLInt, GraphQLFloat, GraphQLList,
                     GraphQLBoolean, Thunk, GraphQLInputFieldMap,
                     InputObjectTypeDefinitionNode,
                     InputObjectTypeExtensionNode)
from graphql.type.definition import GraphQLInputFieldOutType
from scanpointgenerator import LineGenerator, CompoundGenerator

from coniql.util import doc_field
from device.pmac.control.trajectorymodel import TrajectoryModel


class GraphQLLineGenerator(GraphQLInputObjectType):
    name = 'GraphQLLineGenerator'
    fields = {
        'axes': GraphQLInputField(GraphQLList(GraphQLString)),
        'units': GraphQLInputField(GraphQLList(GraphQLString)),
        'start': GraphQLInputField(GraphQLFloat),
        'stop': GraphQLInputField(GraphQLFloat),
        'size': GraphQLInputField(GraphQLInt),
        'alternate': GraphQLInputField(GraphQLBoolean)
    }
    out_type = LineGenerator.from_dict

    def __init__(self) -> None:
        super().__init__(self.name, self.fields, out_type=self.out_type)


class GraphQLCompoundGenerator(GraphQLInputObjectType):
    name = 'GraphQLCompoundGenerator'
    fields = {
        'generators': GraphQLInputField(GraphQLList(GraphQLLineGenerator())),
        'duration': GraphQLInputField(GraphQLFloat, default_value=-1),
        'continuous': GraphQLInputField(GraphQLBoolean, default_value=True)
    }
    out_type = CompoundGenerator.from_dict

    def __init__(self) -> None:
        super().__init__(self.name, self.fields, out_type=self.out_type)


class GraphQLTrajectoryModel(GraphQLInputObjectType):
    name = 'GraphQLTrajectoryModel'
    fields = {
        'generator': GraphQLInputField(GraphQLCompoundGenerator()),
        'start_index': GraphQLInputField(GraphQLInt, default_value=0),
        'end_index': GraphQLInputField(GraphQLInt, default_value=-1)
    }
    out_type = TrajectoryModel.from_dict

    def __init__(self) -> None:
        super().__init__(self.name, self.fields, out_type=self.out_type)
