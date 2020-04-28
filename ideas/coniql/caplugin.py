import asyncio
from coniql.pvaplugin import NUMBER_TYPES
import sys
from .plugin import Plugin
from ._types import Channel, ChannelStatus, ChannelQuality, DisplayForm, EnumMeta, NumberDisplay, NumberMeta, NumberType, ObjectMeta, Range, Time
sys.path.append('/home/hgs15624/code/python/cothread')
from cothread.aioca import caget, caput, camonitor, FORMAT_CTRL, FORMAT_TIME
from cothread import dbr


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

# Map from alarm.severity to ChannelQuality string
CHANNEL_QUALITY_MAP = [
    ChannelQuality.VALID,
    ChannelQuality.WARNING,
    ChannelQuality.ALARM,
    ChannelQuality.INVALID,
    ChannelQuality.UNDEFINED,
]

EMPTY_RANGE = Range(0, 0)
EMPTY_DISPLAY = NumberDisplay(EMPTY_RANGE, EMPTY_RANGE, EMPTY_RANGE, EMPTY_RANGE, "", 4, DisplayForm.DEFAULT)

def display_from_ca_value(ca_value):
    return NumberDisplay(
        controlRange=Range(
            min=ca_value.lower_ctrl_limit,
            max=ca_value.upper_ctrl_limit),
        displayRange=Range(
            min=ca_value.lower_disp_limit,
            max=ca_value.upper_disp_limit),
        alarmRange=Range(
            min=ca_value.lower_alarm_limit,
            max=ca_value.upper_alarm_limit),
        warningRange=Range(
            min=ca_value.lower_warning_limit,
            max=ca_value.upper_warning_limit),
        units=ca_value.units,
        precision=ca_value.precision,
        form=DisplayForm.DEFAULT
    )

def convert_value(value, channel: Channel, meta_value=None):
    meta_args = {
        "description": "ca value",
        "label": channel.id,
        "tags": [],
        "array": False
    }
    type_specifier = value.datatype
    scalar_types = list(NUMBER_TYPES) + list(OTHER_TYPES)
    assert type_specifier in scalar_types, \
        "Expected a scalar type, got %r" % type_specifier
    # Native type is fine
    channel.value = value
    if type_specifier in NUMBER_TYPES:
        display = display_from_ca_value(meta_value)
        channel.meta = NumberMeta(
            numberType=NUMBER_TYPES[type_specifier], display=display, **meta_args)
    elif type_specifier == dbr.DBR_ENUM:
        options = meta_value.enums
        channel.meta = EnumMeta(choices=options, **meta_args)
    elif type_specifier in OTHER_TYPES:
        channel.meta = ObjectMeta(type=OTHER_TYPES[type_specifier], **meta_args)

    timestamp = value.timestamp
    channel.time = Time(
        seconds=int(timestamp),
        nanoseconds=int((timestamp % 1) * 1e9),
        userTag=0
    )
    channel.status = ChannelStatus(
        quality=CHANNEL_QUALITY_MAP[value.severity],
        message="alarm",
        mutable=True
    )


class CAPlugin(Plugin):

    async def get_channel(self, channel_id: str, timeout: float) -> Channel:
        value = await caget(channel_id, format=FORMAT_TIME, timeout=timeout)
        # Put in channel id so converters can see it
        channel = Channel(id=channel_id)
        convert_value(value, channel)
        return channel

    async def put_channel(self, channel_id: str, value, timeout: float):
        await caput(channel_id, value, timeout=timeout)
        channel = await self.get_channel(channel_id, timeout)
        return channel

    async def subscribe_channel(self, channel_id: str):
        q = asyncio.Queue()

        # get metadata
        meta_value = await caget(channel_id, format=FORMAT_CTRL)

        def queue_callback(value):
            asyncio.create_task(q.put(value))

        m = await camonitor(channel_id, queue_callback, format=FORMAT_TIME)
        try:
            # This will hold the current version of alarm data
            last_status = None
            value = await q.get()
            while True:
                channel = Channel(id=channel_id)
                convert_value(value, channel, meta_value)
                # Alarms are always published, but we only want to display it
                # if it has changed
                if channel.status:
                    if last_status == channel.status:
                        channel.status = None
                    else:
                        last_status = channel.status
                yield channel
                value = await q.get()
        finally:
            m.close()
