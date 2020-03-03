import asyncio

from dataclasses import dataclass

from coniql.devicelayer.deviceplugin import DeviceLayer
from device.channel.setup import setup
from device.adcore.addetector import AdDetector
from device.panda.adpanda import AdPandA
from device.pmac.protocol.pmac import Pmac, PmacMotors
from device.motor.tomostage import TomoStage
from device.epics.addets import ad_detector, ad_panda
from device.epics.motor import pmac_motor
from device.epics.pmac import pmac
from device.beamline.beamlines.htssrig import HtssRig
from coniql.deviceplugin import DevicePlugin


def htss_environment(beamline_prefix: str):
    beamline = training_rig_environment(beamline_prefix)
    layer = DeviceLayer.from_tree(beamline)
    return layer


@dataclass
class TrainingRig:
    detector: AdDetector
    panda_position_detector: AdPandA
    sample_stage: TomoStage
    pmac: Pmac


def training_rig_environment(beamline_prefix: str) -> TrainingRig:
    # x = pmac_motor(f'{beamline_prefix}-MO-MAP-01:STAGE:X', 'x')
    # theta = pmac_motor(f'{beamline_prefix}-MO-MAP-01:STAGE:A', 'a')
    # sample_stage = TomoStage(x, theta)
    # det = ad_detector(f'{beamline_prefix}-EA-DET-01', cam_prefix='DET')
    # panda_det = ad_panda(f'{beamline_prefix}-MO-PANDA-01')
    # motors = PmacMotors(x, theta)
    # pmc = pmac(f'{beamline_prefix}-MO-BRICK-01', motors)
    # beamline = TrainingRig(
    #     detector=det,
    #     panda_position_detector=panda_det,
    #     sample_stage=sample_stage,
    #     pmac=pmc
    # )
    beamline = HtssRig(rig=beamline_prefix)
    asyncio.get_event_loop().create_task(setup(beamline))
    return beamline
