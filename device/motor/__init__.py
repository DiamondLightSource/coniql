from device.core.yamltype import yaml_type

EpicsMotor = yaml_type('protocol/motor/epicsmotor.yaml')
ScannableMotor = yaml_type('protocol/motor/epicsmotor.yaml',
                           'protocol/motor/scannable.yaml')
