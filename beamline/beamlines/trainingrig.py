from dataclasses import dataclass

from coniql.deviceplugin import DevicePlugin
from device.devices.addetector import AdDetector
from device.devices.adpanda import AdPandA
from device.devices.camera import Camera
from device.devices.faketriggerbox import in_memory_box, FakeTriggerBox
from device.devices.stage3d import Stage3D
from device.devices.tomostage import TomoStage
from device.epics.ad import camera
from device.epics.addets import ad_detector, ad_panda
from device.epics.motor import motor


# def adsim_device_environment():
#     beamline = adsim_environment('ws415')
#
#     plugin = DevicePlugin()
#     plugin.register_device(beamline, name='beamline')
#
#     plugin.debug()
#     return plugin


@dataclass
class TrainingRig:
    detector: AdDetector
    panda_position_detector: AdPandA
    sample_stage: TomoStage


async def p47_environment():
    return await training_rig_environment('BL47P')


async def training_rig_environment(beamline_prefix: str) -> TrainingRig:
    x = await motor(f'{beamline_prefix}-MO-MAP-01:STAGE:X')
    theta = await motor(f'{beamline_prefix}-MO-MAP-01:STAGE:A')
    sample_stage = TomoStage(x, theta)
    det = await ad_detector(f'{beamline_prefix}-EA-DET-01')
    panda_det = await ad_panda(f'{beamline_prefix}-MO-PANDA-01')
    beamline = TrainingRig(
        detector=det,
        panda_position_detector=panda_det,
        sample_stage=sample_stage
    )
    return beamline
