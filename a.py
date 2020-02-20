from typing_extensions import Protocol

class DetectorID(gql.ScalarType):
	pass

class ADetector(Protocol):
	id_type = DetectorID
	async def arm():
		pass
	exposure_time: RWChannel[float]

##############################
def device_proxy(id_:str, protocol: T) -> T:
	t = device(id_)
	for f in protocol.__dict__:
		assert f in t.__dict__
	return t

@gql_exposed
async def configure_detector(detectorID: str):
	detector = device_proxy(detectorID, ADetector)
	await detector.exposure_time.put(1.3)
	await arm_detector(detectorID)

@gql_exposed
async def arm_detector(detectorID: str):
	detector = device_proxy(detectorID, ADetector)
	await detector.arm()

#################################
@gql_exposed
async def configure_detector(detector: ADetector):
	await detector.exposure_time.put(1.3)
	await arm_detector(detector)

@gql_exposed
async def arm_detector(detector: ADetector):
	await detector.arm()


################################


class DetectorDriver(Protocol):
	exposure_time: RWChannel[float]
	arm: RWChannel[bool]
```
implements:
	- DetectorDriver

exposure_time:
	pv: $(prefix):sdfsdf
 	type: float
```

@dataclass
class Eiger:
	shutter_delay: RWChannel[float]

def foo(a: DetectorDriver):
	pass
