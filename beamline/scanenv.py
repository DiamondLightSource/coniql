from dataclasses import dataclass
from typing import Optional, Dict

from device.envs import adsim_environment
from device.devices.camera import Camera
from device.devices.faketriggerbox import FakeTriggerBox
from device.devices.motor import Motor
from device.devices.positioner import PositionerWithStatus
from device.devices.stage3d import Stage3D


@dataclass
class AdSimScanEnvironment:
    trigger_box: FakeTriggerBox
    main_detector: Camera
    secondary_detector: Optional[Camera]
    sample_stage: Stage3D
    axes: Dict[str, Motor]


def make_env():
    main_env = adsim_environment()
    env = AdSimScanEnvironment(
        trigger_box=main_env.trigger_box,
        main_detector=main_env.detector,
        secondary_detector=None,
        sample_stage=main_env.stage,
        axes={
            'x': main_env.stage.x,
            'y': main_env.stage.y
        }
    )
    return env