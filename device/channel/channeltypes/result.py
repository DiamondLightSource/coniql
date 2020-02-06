from dataclasses import dataclass
from typing import TypeVar, Generic, Iterable, Optional

from coniql._types import Time, ChannelStatus, Readback as GqlReadback, \
    ChannelQuality
from coniql.util import doc_field

T = TypeVar('T')


@dataclass
class Readback(Generic[T]):
    """A single value from a channel with associated time and status.
    These values can be Null so that in a subscription they are only updated
    on change"""
    value: Optional[T] = doc_field(
        "The current value",
        None)

    time: Optional[Time] = doc_field(
        "When the value was last updated",
        None)
    status: Optional[ChannelStatus] = doc_field(
        "Status of the connection, whether is is mutable, and alarm info",
        None)

    @classmethod
    def ok(cls, value: T, mutable: bool = False):
        return Readback(value, Time.now(), ChannelStatus.ok(mutable))

    @classmethod
    def not_connected(cls):
        status = ChannelStatus(ChannelQuality.UNDEFINED, 'disconnected', False)
        return Readback(None, None, status)

    def to_gql_readback(self):
        """Converts to a genericless version of this structure that can be
        passed over GraphQL, consider this a temporary solution"""
        return GqlReadback(self.value, self.time, self.status)
