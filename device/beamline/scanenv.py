from dataclasses import dataclass
from typing import Dict

from device.beamline.beamlines import adsim_environment
from device.adcore.addetector import AdDetector
from device.motor import Motor
from device.motor.stage3d import Stage3D


@dataclass
class AdSimScanEnvironment:
    # trigger_box: FakeTriggerBox
    main_detector: AdDetector
    sample_stage: Stage3D
    axes: Dict[str, Motor]


async def make_env():
    main_env = await adsim_environment('ws415')
    env = AdSimScanEnvironment(
        # trigger_box=main_env.trigger_box,
        main_detector=main_env.detector,
        sample_stage=main_env.stage,
        axes={
            'x': main_env.stage.x,
            'y': main_env.stage.y
        }
    )
    return env
