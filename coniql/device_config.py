import os
import re
from pathlib import Path
from typing import Dict, Iterator, Sequence, Union

from pydantic import BaseModel, Field
from ruamel.yaml import YAML

from coniql.types import Channel

from .coniql_schema import DisplayForm, Layout, Widget


def camel_to_title(name):
    """Takes a CamelCaseFieldName and returns an Title Case Field Name
    Args:
        name (str): E.g. CamelCaseFieldName
    Returns:
        str: Title Case converted name. E.g. Camel Case Field Name
    """
    split = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z0-9]|$)", name)
    ret = " ".join(split)
    ret = ret[0].upper() + ret[1:]
    return ret


class WithLabel(BaseModel):
    name: str = Field(
        ...,
        description="CamelCase name to uniquely identify this channel",
        regex=r"([A-Z][a-z0-9]*)*$",
    )
    label: str = Field(
        None,
        description="The GUI Label for this, default is name converted to Title Case",
    )

    def get_label(self) -> str:
        """If the component has a label, use that, otherwise
        return the Title Case version of its camelCase name"""
        label = self.label
        if label is None:
            label = camel_to_title(self.name)
        return label


class ChannelConfig(WithLabel):
    type: str = Field("ChannelConfig", const=True)
    read_pv: str = Field(
        None, description="The pv to get from, None means not readable (an action)",
    )
    write_pv: str = Field(
        None, description="The pv to put to, None means not writeable (a readback)",
    )
    # The following are None to allow multiple references to channels
    widget: Widget = Field(None, description="Which widget to use for the Channel")
    description: str = Field(None, description="Description of what the Channel does")
    display_form: DisplayForm = Field(
        None, description="How should numeric values be displayed",
    )


class DeviceInstance(WithLabel):
    type: str = Field("DeviceInstance", const=True)
    id: str = Field(None, description="The id of this device, None means use name")
    file: Path = Field(
        ..., description="The filename to read device definition (ending .coniql.yaml)",
    )
    macros: Dict[str, str] = Field(
        {}, description="The macros to substitute when instantiating device"
    )


Child = Union["Group", ChannelConfig, DeviceInstance]


class Group(WithLabel):
    type: str = Field("Group", const=True)
    layout: Layout = Field(
        Layout.BOX, description="The layout to arrange the children within"
    )
    children: Sequence[Child]


Group.update_forward_refs()


class DeviceConfig(BaseModel):
    _cache: Dict[str, "DeviceConfig"] = {}
    children: Sequence[Child]

    @classmethod
    def from_yaml(cls, path: Path, macros: Dict[str, str] = None) -> "DeviceConfig":
        abspath = str(path.resolve())
        try:
            device_config = cls._cache[abspath]
        except KeyError:
            device_config = cls(**YAML().load(path))
            cls._cache[abspath] = device_config
        # TODO: return a version with macros substituted
        return device_config


DeviceConfig.update_forward_refs()


def walk(tree: Sequence[Child]) -> Iterator[Child]:
    """Depth first traversal of tree"""
    for t in tree:
        yield t
        if isinstance(t, Group):
            yield from walk(t.children)


class ConfigStore(BaseModel):
    devices: Dict[str, DeviceConfig] = Field(
        {}, description="{device_id: device_config}"
    )
    channels: Dict[str, ChannelConfig] = Field({}, description="{pv: channel_config}")

    def add_device_config(self, path: Path, device_id="", macros=None):
        """Load a top level .coniql.yaml file with devices in it"""
        # Relative paths are relative to the path being loaded, so go there
        cwd = Path.cwd()
        os.chdir(path.resolve().parent)
        try:
            device_config = DeviceConfig.from_yaml(path, macros)
            if device_id:
                self.devices[device_id] = device_config
            for child in walk(device_config.children):
                if isinstance(child, ChannelConfig):
                    # TODO: selectively update channel if already exists
                    self.channels[child.write_pv or child.read_pv] = child
                elif isinstance(child, DeviceInstance):
                    # recursively load child devices
                    if child.id:
                        child_device_id = child.id
                    elif device_id:
                        child_device_id = device_id + "." + child.name
                    else:
                        child_device_id = child.name
                    self.add_device_config(child.file, child_device_id, child.macros)
        finally:
            os.chdir(cwd)
        return device_config

    def update_channel(self, channel: Channel) -> Channel:
        config = self.channels.get(channel.id, None)
        if config and channel.display:
            channel.display.description = config.description
            channel.display.form = config.display_form
            channel.display.widget = config.widget
        return channel


if __name__ == "__main__":
    print(DeviceConfig.schema_json(indent=2))
