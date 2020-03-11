from device.channel.ca.bool import CaBool
from device.channel.ca.channel import CaChannel
from device.channel.ca.enum import CaEnum
from device.adcore.protocol.hdf import HdfPlugin, Swmr
from device.adcore.plugin import PluginCallback, PluginCounters, \
    PluginProperties
from device.adcore.protocol.camera import Camera, DetectorDriver


def camera(prefix: str) -> Camera:
    return Camera(
        **detector_driver_layout(prefix),
        exposure_time=CaChannel(f'{prefix}:AcquireTime',
                                rbv_suffix='_RBV'),
        acquire_period=CaChannel(f'{prefix}:AcquirePeriod',
                                 rbv_suffix='_RBV')
    )


def detector_driver(prefix: str) -> DetectorDriver:
    return DetectorDriver(**detector_driver_layout(prefix))


def detector_driver_layout(prefix: str):
    return dict(
        exposures_per_image=CaChannel(f'{prefix}:NumExposures',
                                      rbv_suffix='_RBV'),
        number_of_images=CaChannel(f'{prefix}:NumImages',
                                   rbv_suffix='_RBV'),
        image_mode=CaEnum(f'{prefix}:ImageMode',
                          rbv_suffix='_RBV'),
        trigger_mode=CaEnum(f'{prefix}:TriggerMode',
                            rbv_suffix='_RBV'),
        acquire=CaBool(f'{prefix}:Acquire'),
        array_counter=CaChannel(f'{prefix}:ArrayCounter',
                                rbv_suffix='_RBV'),
        framerate=CaChannel(f'{prefix}:ArrayRate_RBV')
    )


def hdf_plugin(prefix: str) -> HdfPlugin:
    swmr_child = swmr(prefix)
    return HdfPlugin(
        swmr=swmr_child,

        file_path=CaChannel(f'{prefix}:FilePath', rbv_suffix='_RBV'),
        file_name=CaChannel(f'{prefix}:FileName', rbv_suffix='_RBV'),
        suffix=CaChannel(f'{prefix}:TempSuffix', rbv_suffix='_RBV'),

        next_file_number=CaChannel(f'{prefix}:FileNumber', rbv_suffix='_RBV'),
        file_name_format=CaChannel(f'{prefix}:FileTemplate', rbv_suffix='_RBV'),
        num_to_capture=CaChannel(f'{prefix}:NumCapture', rbv_suffix='_RBV'),
        num_captured=CaChannel(f'{prefix}:NumCaptured_RBV'),
        auto_increment=CaEnum(f'{prefix}:AutoIncrement', rbv_suffix='_RBV'),
        file_format=CaEnum(f'{prefix}:FileFormat', rbv_suffix='_RBV'),
        auto_save=CaEnum(f'{prefix}:AutoSave', rbv_suffix='_RBV'),

        capture_mode=CaEnum(f'{prefix}:FileWriteMode', rbv_suffix='_RBV'),
        capture=CaBool(f'{prefix}:Capture', rbv_suffix='_RBV'),
        write_status=CaBool(f'{prefix}:WriteStatus'),
        write_status_message=CaChannel(f'{prefix}:WriteMessage'),
        full_file_name=CaChannel(f'{prefix}:FullFileName_RBV'),

        num_extra_dims=CaChannel(f'{prefix}:NumExtraDims', rbv_suffix='_RBV'),
        num_chunk_rows=CaChannel(f'{prefix}:NumRowChunks', rbv_suffix='_RBV'),
        **ad_plugin_layout(prefix)
    )


def swmr(prefix: str) -> Swmr:
    return Swmr(
        mode=CaChannel(f'{prefix}:SWMRMode', rbv_suffix='_RBV'),
        active=CaBool(f'{prefix}:SWMRActive_RBV'),
        position_mode=CaEnum(f'{prefix}:PositionMode'),
        flush=CaBool(f'{prefix}:FlushNow'),
        flush_on_nth_frame=CaChannel(f'{prefix}:NumFramesFlush',
                                     rbv_suffix='_RBV'),
        nd_attribute_flush=CaChannel(f'{prefix}:NDAttributeChunk',
                                     rbv_suffix='_RBV')
    )


def ad_plugin_layout(prefix: str):
    return dict(
        array_port=CaChannel(f'{prefix}:NDArrayPort',
                             rbv_suffix='_RBV'),
        properties=plugin_properties(prefix),
        callback=plugin_callback(prefix),
        counters=plugin_counters(prefix)
    )


def plugin_callback(prefix: str) -> PluginCallback:
    return PluginCallback(
        status=CaEnum(f'{prefix}:EnableCallbacks', rbv_suffix='_RBV'),
        min_time=CaChannel(f'{prefix}:MinCallbackTime', rbv_suffix='_RBV'),
        blocking=CaEnum(f'{prefix}:BlockingCallbacks', rbv_suffix='_RBV'),
    )


def plugin_counters(prefix: str) -> PluginCounters:
    return PluginCounters(
        array_counter=CaChannel(f'{prefix}:ArrayCounter', rbv_suffix='_RBV'),
        array_rate=CaChannel(f'{prefix}:ArrayRate_RBV'),
        queue_size=CaChannel(f'{prefix}:QueueSize'),
        queue_usage=CaChannel(f'{prefix}:QueueUse'),
        dropped_arrays=CaChannel(f'{prefix}:DroppedArrays', rbv_suffix='_RBV')
    )


def plugin_properties(prefix: str) -> PluginProperties:
    return PluginProperties(
        num_dimensions=CaChannel(f'{prefix}:NDimensions_RBV'),
        dim_0_size=CaChannel(f'{prefix}:ArraySize0_RBV'),
        dim_1_size=CaChannel(f'{prefix}:ArraySize1_RBV'),
        dim_2_size=CaChannel(f'{prefix}:ArraySize2_RBV'),

        data_type=CaEnum(f'{prefix}:DataType_RBV'),
        colour_mode=CaEnum(f'{prefix}:ColorMode_RBV'),
        bayer_pattern=CaEnum(f'{prefix}:BayerPattern_RBV'),
        unique_id=CaChannel(f'{prefix}:UniqueId_RBV'),
        time_stamp=CaChannel(f'{prefix}:TimeStamp_RBV'),
    )
