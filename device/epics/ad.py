from device.channel.ca.cabool import CaBool
from device.channel.ca.caenum import CaEnum
from device.channel.ca.channel import CaField
from device.devices.adcore.hdf import HdfPlugin, Swmr
from device.devices.adcore.plugin import PluginCallback, PluginCounters, \
    PluginProperties
from device.devices.adcore.pos import PosPlugin
from device.devices.camera import Camera, DetectorDriver
from device.epics.util import device_from_layout, connect_channels


async def camera(prefix: str) -> Camera:
    layout = camera_channels(prefix)
    return await device_from_layout(layout, Camera)


def camera_channels(prefix: str):
    return dict(
        **detector_driver_layout(prefix),
        exposure_time=CaField(f'{prefix}:AcquireTime',
                              rbv_suffix='_RBV'),
        acquire_period=CaField(f'{prefix}:AcquirePeriod',
                               rbv_suffix='_RBV')
    )


async def detector_driver(prefix: str) -> DetectorDriver:
    layout = detector_driver_layout(prefix)
    return await device_from_layout(layout, DetectorDriver)


def detector_driver_layout(prefix: str):
    return dict(
        exposures_per_image=CaField(f'{prefix}:NumExposures',
                                    rbv_suffix='_RBV'),
        number_of_images=CaField(f'{prefix}:NumImages',
                                 rbv_suffix='_RBV'),
        image_mode=CaEnum(f'{prefix}:ImageMode',
                          rbv_suffix='_RBV'),
        trigger_mode=CaEnum(f'{prefix}:TriggerMode',
                            rbv_suffix='_RBV'),
        acquire=CaBool(f'{prefix}:Acquire'),
        array_counter=CaField(f'{prefix}:ArrayCounter',
                              rbv_suffix='_RBV'),
        framerate=CaField(f'{prefix}:ArrayRate_RBV')
    )


async def hdf_plugin(prefix: str) -> HdfPlugin:
    properties = plugin_properties(prefix)
    callback = plugin_callback(prefix)
    counters = plugin_counters(prefix)

    hdf = await connect_channels(hdf_plugin_layout(prefix))
    swmr_child = await swmr(prefix)
    return HdfPlugin(swmr=swmr_child, properties=properties, callback=callback,
                     counters=counters, **hdf)


def hdf_plugin_layout(prefix: str):
    return dict(
        file_path=CaField(f'{prefix}:FilePath', rbv_suffix='_RBV'),
        file_name=CaField(f'{prefix}:FileName', rbv_suffix='_RBV'),
        suffix=CaField(f'{prefix}:TempSuffix', rbv_suffix='_RBV'),

        next_file_number=CaField(f'{prefix}:FileNumber', rbv_suffix='_RBV'),
        file_name_format=CaField(f'{prefix}:FileTemplate', rbv_suffix='_RBV'),
        num_to_capture=CaField(f'{prefix}:NumCapture', rbv_suffix='_RBV'),
        num_captured=CaField(f'{prefix}:NumCaptured_RBV'),
        auto_increment=CaEnum(f'{prefix}:AutoIncrement', rbv_suffix='_RBV'),
        file_format=CaEnum(f'{prefix}:FileFormat', rbv_suffix='_RBV'),
        auto_save=CaEnum(f'{prefix}:AutoSave', rbv_suffix='_RBV'),

        capture_mode=CaEnum(f'{prefix}:FileWriteMode', rbv_suffix='_RBV'),
        capture=CaBool(f'{prefix}:Capture', rbv_suffix='_RBV'),
        write_status=CaBool(f'{prefix}:WriteStatus'),
        write_status_message=CaField(f'{prefix}:WriteMessage'),
        full_file_name=CaField(f'{prefix}:FullFileName_RBV'),

        num_extra_dims=CaField(f'{prefix}:NumExtraDims', rbv_suffix='_RBV'),
        num_chunk_rows=CaField(f'{prefix}:NumRowChunks', rbv_suffix='_RBV'),
    )


async def swmr(prefix: str) -> Swmr:
    layout = swmr_layout(prefix)
    return await device_from_layout(layout, Swmr)


def swmr_layout(prefix: str):
    return dict(
        mode=CaField(f'{prefix}:SWMRMode', rbv_suffix='_RBV'),
        active=CaBool(f'{prefix}:SWMRActive_RBV'),
        position_mode=CaEnum(f'{prefix}:PositionMode'),
        flush=CaBool(f'{prefix}:FlushNow'),
        flush_on_nth_frame=CaField(f'{prefix}:NumFramesFlush',
                                   rbv_suffix='_RBV'),
        nd_attribute_flush=CaField(f'{prefix}:NDAttributeChunk',
                                   rbv_suffix='_RBV')
    )


def ad_plugin_layout(prefix: str):
    return dict(
        array_port=CaField(f'{prefix}:NDArrayPort',
                           rbv_suffix='_RBV')
    )


async def plugin_callback(prefix: str) -> PluginCallback:
    layout = plugin_callback_layout(prefix)
    return await device_from_layout(layout, PluginCallback)


def plugin_callback_layout(prefix: str):
    return dict(
        status=CaEnum(f'{prefix}:EnableCallbacks', rbv_suffix='_RBV'),
        min_time=CaField(f'{prefix}:MinCallbackTime', rbv_suffix='_RBV'),
        blocking=CaEnum(f'{prefix}:BlockingCallbacks', rbv_suffix='_RBV'),
    )


async def plugin_counters(prefix: str) -> PluginCounters:
    layout = plugin_callback_layout(prefix)
    return await device_from_layout(layout, PluginCounters)


def plugin_counters_layout(prefix: str):
    return dict(
        array_counter=CaField(f'{prefix}:ArrayCounter', rbv_suffix='_RBV'),
        array_rate=CaField(f'{prefix}:ArrayRate_RBV'),
        queue_size=CaField(f'{prefix}:QueueSize'),
        queue_usage=CaField(f'{prefix}:QueueUse'),
        dropped_arrays=CaField(f'{prefix}:DroppedArrays', rbv_suffix='_RBV')
    )


async def plugin_properties(prefix: str) -> PluginProperties:
    layout = plugin_properties_layout(prefix)
    return await device_from_layout(layout, PluginProperties)


def plugin_properties_layout(prefix: str):
    return dict(
        num_dimensions=CaField(f'{prefix}:NDimensions_RBV'),
        dim_0_size=CaField(f'{prefix}:ArraySize0_RBV'),
        dim_1_size=CaField(f'{prefix}:ArraySize1_RBV'),
        dim_2_size=CaField(f'{prefix}:ArraySize2_RBV'),

        data_type=CaEnum(f'{prefix}:DataType_RBV'),
        colour_mode=CaEnum(f'{prefix}:ColorMode_RBV'),
        bayer_pattern=CaEnum(f'{prefix}:BayerPattern_RBV'),
        unique_id=CaField(f'{prefix}:UniqueId_RBV'),
        time_stamp=CaField(f'{prefix}:TimeStamp_RBV'),
    )