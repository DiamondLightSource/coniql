import sys
from enum import Enum
import dataclasses
from typing import Type, Dict

from graphql import (
    GraphQLEnumType, GraphQLEnumValue, GraphQLField, GraphQLFloat,
    GraphQLNonNull, GraphQLList, GraphQLObjectType, GraphQLString,
    GraphQLInterfaceType, GraphQLInt, GraphQLBoolean, GraphQLOutputType)


GQL_BUILTIN_TYPES = dict(
    str=GraphQLString,
    float=GraphQLFloat,
    int=GraphQLInt,
    bool=GraphQLBoolean,
)


# https://stackoverflow.com/a/19330461
class DocEnum(Enum):
    """
    Automatically numbers enum members starting from 1.

    Includes support for a custom docstring per member.

    """
    __last_number__ = 0

    def __new__(cls, *args):
        """Ignores arguments (will be handled in __init__."""
        value = cls.__last_number__ + 1
        cls.__last_number__ = value
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, *args):
        """Can handle 0 or 1 argument; more requires a custom __init__.

        0  = auto-number w/o docstring
        1  = auto-number w/ docstring
        2+ = needs custom __init__

        """
        if len(args) == 1 and isinstance(args[0], str):
            self.__doc__ = args[0]
        elif args:
            raise TypeError('%s not dealt with: need custom __init__' % (args,))


def doc_field(docstring, default=dataclasses.MISSING,
              default_factory=dataclasses.MISSING, init=True,
              repr=True, hash=None, compare=True):
    metadata = {
            'docstring': docstring}
    return dataclasses.field(
        default=default, default_factory=default_factory, init=init,
        repr=repr, hash=hash, compare=compare, metadata=metadata)

    
def convert_fields(typ, types: Dict[str, GraphQLOutputType]):
    fields = {}
    for field in dataclasses.fields(typ):
        field_type = field.type
        wrappers = []
        if field_type.startswith("Optional["):
            field_type = field.type[9:-1]
        else:
            wrappers.append(GraphQLNonNull)
        if field_type.startswith("List["):
            field_type = field.type[5:-1]
            wrappers.append(GraphQLList)
        if field_type in GQL_BUILTIN_TYPES:
            gql_type = GQL_BUILTIN_TYPES[field_type]
        elif field_type in types:
            gql_type = types[field_type]
        else:
            # Lookup field_type in correct namespace
            # https://www.python.org/dev/peps/pep-0563
            cls_globals = vars(sys.modules[typ.__module__])
            field_type = eval(field_type, cls_globals)
            gql_type = make_gql_type(field_type, types)
        for wrapper in reversed(wrappers):
            gql_type = wrapper(gql_type)
        fields[field.name] = GraphQLField(
            gql_type, description=field.metadata["docstring"])
    return fields


def make_gql_type(typ: Type,
                  types: Dict[str, GraphQLOutputType]) -> GraphQLOutputType:
    to_process = []
    if dataclasses.is_dataclass(typ):
        # First look up the mro tree to see if any superclasses need to be
        # converted
        for supercls in typ.__mro__:
            if supercls not in (typ, object) and supercls.__name__ not in types:
                make_gql_type(supercls)
        # Now we can declare our interfaces
        interfaces = [types[cls.__name__] for cls in typ.__mro__ if
                      cls.__name__ in types]
        # Convert the type of any field
        fields = convert_fields(typ, types)
        if typ.__subclasses__():
            # We are an interface
            gql_type = GraphQLInterfaceType(typ.__name__, fields)
            # Process all the subclasses
            to_process += typ.__subclasses__()
        else:
            # We are a type
            gql_type = GraphQLObjectType(
                typ.__name__, fields, interfaces=interfaces,
                is_type_of=lambda value, _: value.__class__ == typ)
    elif isinstance(typ, type) and issubclass(typ, Enum):
        gql_type = GraphQLEnumType(typ.__name__, {
            e.name: GraphQLEnumValue(e, description=e.__doc__)
            for e in typ
        }, description=typ.__doc__)
    else:
        raise TypeError("Cannot convert %r" % typ)
    types[typ.__name__] = gql_type
    # We might have some more to do...
    for typ in to_process:
        make_gql_type(typ, types)
    return gql_type
