from device.pmac.protocol.pmac import Pmac

async def servo_frequency(pmac: Pmac) -> float:
    i10 = await pmac.i10.get()
    return 8388608000.0 / i10
