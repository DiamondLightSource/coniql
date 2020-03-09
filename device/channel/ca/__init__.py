from device.channel.ca.bool import CaBool
from device.channel.ca.channel import CaChannel
from device.channel.ca.enum import CaEnum
from device.channel.ca.string import CaString


# TODO: These should all become their own classes that return Python types
#        rather than aioca types
CaFloat = CaChannel
CaInt = CaChannel
CaIntArray = CaChannel
CaFloatArray = CaChannel
