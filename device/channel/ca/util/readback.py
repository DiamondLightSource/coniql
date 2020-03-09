from typing import Any

from aioca import _dbr as dbr

from coniql._types import NumberType, ChannelQuality, Range, NumberDisplay, \
    DisplayForm, Time, ChannelStatus, Readback

NUMBER_TYPES = {
    dbr.DBR_CHAR: NumberType.INT8,
    dbr.DBR_SHORT: NumberType.INT16,
    dbr.DBR_LONG: NumberType.INT64,
    dbr.DBR_FLOAT: NumberType.FLOAT32,
    dbr.DBR_DOUBLE: NumberType.FLOAT64
}

OTHER_TYPES = {
    dbr.DBR_ENUM: "Enum",
    dbr.DBR_STRING: "String"
}

CHANNEL_QUALITY_MAP = [
    ChannelQuality.VALID,
    ChannelQuality.WARNING,
    ChannelQuality.ALARM,
    ChannelQuality.INVALID,
    ChannelQuality.UNDEFINED,
]

EMPTY_RANGE = Range(0, 0)
EMPTY_DISPLAY = NumberDisplay(EMPTY_RANGE, EMPTY_RANGE, EMPTY_RANGE,
                              EMPTY_RANGE, "", 4, DisplayForm.DEFAULT)


def ca_value_to_readback(value: Any, ca_value) -> Readback:
    """Converts a value from aioca to a Coniql Readback object."""
    return Readback(
        value=value,
        time=time_from_ca_timestamp(ca_value.timestamp),
        status=status_from_ca_value(ca_value)
    )


def time_from_ca_timestamp(timestamp: float) -> Time:
    """Creates a Coniql Time from an aioca timestamp"""
    return Time(
        seconds=int(timestamp),
        nanoseconds=int((timestamp % 1) * 1e9),
        userTag=0
    )


def status_from_ca_value(ca_value) -> ChannelStatus:
    """Creates a Coniql ChannelStatus from an aioca value"""
    return ChannelStatus(
        quality=CHANNEL_QUALITY_MAP[ca_value.severity],
        message="alarm",
        mutable=True
    )
