from device.core.yamltype import yaml_type

PmacMotor = yaml_type('protocol/motor/epicsmotor.yaml',
                      'protocol/motor/scannable.yaml',
                      'protocol/pmac/pmacaxis.yaml')

CsAxis = yaml_type('protocol/pmac/csaxis.yaml')
CsDemands = yaml_type('protocol/pmac/csdemands.yaml')
ProfilePart = yaml_type('protocol/pmac/profilepart.yaml')
Trajectory = yaml_type('protocol/pmac/trajectory.yaml')
Pmac = yaml_type('protocol/pmac/pmac.yaml')
