from typing import Any

from ._types import Channel, Function


class Plugin:
    async def read_channel(self, channel_id: str, timeout: float):
        """Read the current value and status of a channel"""
        raise NotImplementedError(self)

    async def get_channel(self, channel_id: str) -> Channel:
        """Get information about a Channel"""
        raise NotImplementedError(self)

    async def get_function(self, function_id: str, timeout: float) -> Function:
        """Get the current structure of a Function"""
        raise NotImplementedError(self)

    async def put_channel(self, channel_id: str, value, timeout: float
                          ) -> Channel:
        """Put a value to a channel, returning the value after put"""
        raise NotImplementedError(self)

    async def call_function(self, function_id: str, arguments, timeout: float
                            ) -> Any:
        """Call a function and return the result"""
        raise NotImplementedError(self)

    async def subscribe_channel(self, channel_id: str):
        """Subscribe to the structure of the value, yielding dict structures
        where only changing top level fields are filled in"""
        yield
        raise NotImplementedError(self)

    def startup(self):
        """Start any services the plugin needs. Don't block"""

    def shutdown(self):
        """Destroy the plugin and any connections it has"""
