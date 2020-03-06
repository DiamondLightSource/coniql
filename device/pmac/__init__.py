from device.core.yaml.yamltype import yaml_type

# PmacMotor = yaml_type('device/motor/epicsmotor.yaml',
#                       'device/motor/scannable.yaml',
#                       'device/pmac/pmacaxis.yaml')
PmacMotor = yaml_type('device/pmac/pmacaxis.yaml')

CsAxis = yaml_type('device/pmac/csaxis.yaml')
CsDemands = yaml_type('device/pmac/csdemands.yaml')
ProfilePart = yaml_type('device/pmac/profilepart.yaml')
Trajectory = yaml_type('device/pmac/trajectory.yaml')
Pmac = yaml_type('device/pmac/pmac.yaml')
