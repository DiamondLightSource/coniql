from device.devices.addetector import AdDetector
from device.devices.adpanda import AdPandA
from device.epics.ad import detector_driver, hdf_plugin, camera


async def ad_panda(prefix: str) -> AdPandA:
    driver = await detector_driver(f'{prefix}:DRV')
    hdf_plugin = await hdf_plugin(f'{prefix}:HDF')
    return AdPandA(driver=driver, hdf=hdf_plugin)


async def ad_detector(prefix: str) -> AdDetector:
    camera = await camera(f'{prefix}:CAM')
    hdf_plugin = await hdf_plugin(f'{prefix}:HDF')
    return AdDetector(camera=camera, hdf=hdf_plugin)