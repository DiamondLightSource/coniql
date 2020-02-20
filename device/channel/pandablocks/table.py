from typing import List, TypeVar

from device.channel.pandablocks.channel import PandAFieldChannel
from device.channel.pandablocks.pandablocksclient import PandABlocksClient
from device.channel.pandablocks.ptable import PandATableSerDes

_INT_VALUES = List[int]

TTable = TypeVar('TTable')


class PandATableChannel(PandAFieldChannel[TTable]):
    def __init__(self, client: PandABlocksClient, block_name: str,
                 field_name: str, serdes: PandATableSerDes[TTable]):
        super().__init__(client, block_name, field_name)
        self.serdes = serdes

    async def put(self, value: TTable) -> bool:
        int_values = self.serdes.list_from_table(value)
        return await self.client.set_table(self.block_name,
                                           self.field_name, int_values)

    async def get(self) -> TTable:
        int_values = await self.client.get_table_fields(self.block_name,
                                                        self.field_name)
        value = self.serdes.table_from_list(int_values)
        return value
