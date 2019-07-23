from typing import Dict

from annotypes import WithCallTypes, NO_DEFAULT
from graphql import (
    GraphQLField, GraphQLString, GraphQLOutputType, GraphQLNonNull,
    GraphQLArgument, INVALID)

field_lookup = {
    str: GraphQLString
}  # type: Dict[type, GraphQLOutputType]


def field_from_resolver(resolver: WithCallTypes) -> GraphQLField:
    # Make a graphql field by parsing the call types decorated function
    args = {}
    for k, anno in resolver.call_types.items():
        typ = field_lookup[anno.typ]
        if anno.default is NO_DEFAULT:
            typ = GraphQLNonNull(typ)
            default = INVALID
        else:
            default = anno.default
        args[k] = GraphQLArgument(typ, default, anno.description)
    return_typ = field_lookup[resolver.return_type.typ]

    def resolve_func(root, info, **kwargs):
        return resolver(**kwargs)

    field = GraphQLField(
        return_typ, description=resolver.__doc__, args=args,
        resolve=resolve_func)
    return field
