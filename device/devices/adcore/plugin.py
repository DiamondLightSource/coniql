from dataclasses import dataclass

from device.channel.channeltypes.channel import ReadWriteChannel, \
    ReadOnlyChannel


@dataclass
class PluginCallback:
    enabled: ReadWriteChannel[str]
    min_time: ReadWriteChannel[float]
    blocking: ReadWriteChannel[str]


@dataclass
class PluginCounters:
    arrays: ReadWriteChannel[int]
    array_rate: ReadOnlyChannel[float]
    queue_size: ReadOnlyChannel[int]
    queue_usage: ReadOnlyChannel[int]
    dropped_arrays: ReadOnlyChannel[int]


@dataclass
class PluginProperties:
    num_dimensions: ReadOnlyChannel[int]
    dim_0_size: ReadOnlyChannel[int]
    dim_1_size: ReadOnlyChannel[int]
    dim_2_size: ReadOnlyChannel[int]

    data_type: ReadOnlyChannel[str]
    colour_mode: ReadOnlyChannel[str]
    bayer_pattern: ReadOnlyChannel[str]
    unique_id: ReadOnlyChannel[int]
    time_stamp: ReadOnlyChannel[float]


@dataclass
class AdPlugin:
    array_port: ReadWriteChannel[str]
    callback: PluginCallback
    counters: PluginCounters
