from device.core.yamltype import yaml_type

PmacMotor = yaml_type('device/motor/epicsmotor.yaml',
                      'device/motor/scannable.yaml',
                      'device/pmac/pmacaxis.yaml')
