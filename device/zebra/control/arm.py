from device.zebra.protocol.zebra import Zebra


async def arm(zebra: Zebra):
    """Arms Zebra, returns only when arming confirmed"""
    await zebra.system_reset_process.put(True)
    await zebra.position_capture.arm.put(True)
    # TODO: Do we need to explicitly wait for arm_status to be true?


async def disarm(zebra: Zebra):
    """Disarms zebra"""
    await zebra.position_capture.disarm.put(True)
