from device.util import asyncio_gather_values


async def device_from_layout(layout, device_cls):
    channels = await connect_channels(layout)
    return device_cls(**channels)


async def connect_channels(layout):
    return await asyncio_gather_values(connections(layout))


def connections(layout):
    return {
        name: channel_def.create_channel()
        for name, channel_def in layout.items()
    }
