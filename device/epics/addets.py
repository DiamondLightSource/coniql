from device.devices.addetector import AdDetector
from device.devices.adpanda import AdPandA
from device.epics.ad import detector_driver, hdf_plugin, camera


def ad_panda(prefix: str) -> AdPandA:
    driver = detector_driver(f'{prefix}:DRV')
    hdf = hdf_plugin(f'{prefix}:HDF5')
    return AdPandA(driver=driver, hdf=hdf)


def ad_detector(prefix: str, cam_prefix: str = 'CAM') -> AdDetector:
    cam = camera(f'{prefix}:{cam_prefix}')
    hdf = hdf_plugin(f'{prefix}:HDF5')
    return AdDetector(camera=cam, hdf=hdf)
