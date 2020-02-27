from coniql.deviceplugin import DevicePlugin
from device.channel.inmemory.channel import InMemoryReadOnlyChannel, \
    InMemoryReadWriteChannel
from device.motor.goniometer import Goniometer
from device.motor import Motor
from device.motor.stage3d import Stage3D


def mock_device_environment() -> DevicePlugin:
    def mock_motor(position: float = 0.0) -> Motor:
        return Motor(
            position=InMemoryReadOnlyChannel(position),
            setpoint=InMemoryReadWriteChannel(position),
            p=InMemoryReadWriteChannel(1.0),
            i=InMemoryReadWriteChannel(0.0),
            d=InMemoryReadWriteChannel(0.0),
            jog_positive=InMemoryReadWriteChannel(False),
            jog_negative=InMemoryReadWriteChannel(False),
            step_length=InMemoryReadWriteChannel(1.0),
            velocity=InMemoryReadWriteChannel(1.0),
            min=InMemoryReadWriteChannel(-1000.0),
            max=InMemoryReadWriteChannel(1000.0)
        )

    goniometer = Goniometer(
        omega=mock_motor(),
        chi=mock_motor(),
        phi=mock_motor(),
        sample=Stage3D(
            x=mock_motor(),
            y=mock_motor(),
            z=mock_motor()
        )
    )

    plugin = DevicePlugin()
    plugin.register_device(goniometer, name='goniometer')

    plugin.debug()
    return plugin

