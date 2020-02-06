from typing import Any, Callable, List, Iterable, TypeVar, Generic, Dict

import numpy as np

from dataclasses import dataclass
from typing import Any

T = TypeVar('T')
_INT_VALUES = List[int]
_TABLE_CONSTRUCTOR = Callable[[_INT_VALUES], T]
_DTYPES = Dict[str, int]


@dataclass
class PandATableSerDes(Generic[T]):
    field_data: Any
    ints_per_row: int
    table_constructor: _TABLE_CONSTRUCTOR
    columns: _DTYPES

    def list_from_table(self, table: T) -> _INT_VALUES:
        # Create a bit array we can contribute to
        nrows = len(table[list(self.field_data)[0]])
        int_matrix = np.zeros((nrows, self.ints_per_row), dtype=np.uint32)
        # For each row, or the right bits of the int values
        for column_name, field_data in self.field_data.items():
            column_value = table[column_name]
            if field_data.labels:
                # Choice, lookup indexes of the label values
                indexes = [field_data.labels.index(v) for v in column_value]
                column_value = np.array(indexes, dtype=np.uint32)
            else:
                # Array, unwrap to get the numpy array
                column_value = column_value.seq
            # Left shift the value so it is aligned with the int columns
            _, mask = get_nbits_mask(field_data)
            shifted_column = (column_value & mask) << field_data.bits_lo % 32
            # Or it with what we currently have
            column_index = get_column_index(field_data)
            int_matrix[..., column_index] |= shifted_column.astype(np.uint32)
        # Flatten it to a list of uints
        int_values = int_matrix.reshape((nrows * self.ints_per_row,))
        return int_values

    def table_from_list(self, int_values: _INT_VALUES) -> T:
        columns = {}
        nrows = len(int_values) // self.ints_per_row
        # Convert to a 1D uint32 array
        u32 = np.array([int(x) for x in int_values], dtype=np.uint32)
        # Reshape to a 2D array
        int_matrix = u32.reshape((nrows, self.ints_per_row))
        # Create the data for each column
        for column_name, field_data in self.field_data.items():
            # Find the right int to operate on
            column_index = get_column_index(field_data)
            int_column = int_matrix[..., column_index]
            # Right shift data, and mask it
            nbits, mask = get_nbits_mask(field_data)
            shifted_column = (int_column >> field_data.bits_lo % 32) & mask
            # If we wanted labels, convert to values here
            if field_data.labels:
                column_value = [field_data.labels[i] for i in shifted_column]
            elif nbits == 1:
                column_value = shifted_column.astype(np.bool)
            else:
                # View as the correct type
                dtype = self.columns[column_name]
                column_value = shifted_column.astype(dtype)
            columns[column_name] = column_value
        # Create a table from it
        table = self.table_constructor(**columns)
        # table = self.meta.validate(self.meta.table_cls(**columns))
        return table


def get_dtype(nbits, signed):
    if nbits <= 8:
        dtype = "int8"
    elif nbits <= 16:
        dtype = "int16"
    elif nbits <= 32:
        dtype = "int32"
    elif nbits <= 64:
        dtype = "int64"
    else:
        raise ValueError("Bad number of bits %s" % nbits)
    if not signed:
        dtype = "u" + dtype
    return dtype


def get_column_index(field_data):
    column_index = field_data.bits_lo // 32
    assert field_data.bits_hi // 32 == column_index, \
        "Column %s spans multiple uint32 values" % (field_data,)
    return column_index


def get_nbits_mask(field_data):
    nbits = field_data.bits_hi - field_data.bits_lo + 1
    mask = 2 ** nbits - 1
    return nbits, mask
