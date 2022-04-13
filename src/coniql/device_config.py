import re
from pathlib import Path
from typing import Dict, Iterator, Sequence, Union

from pydantic import BaseModel, Field
from ruamel.yaml import YAML

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
        return self.label or camel_to_title(self.name)


class ChannelConfig(WithLabel):
    type: str = Field("ChannelConfig", const=True)
    read_pv: str = Field(
        None,
        description="The pv to get from, None means not readable (an action)",
    )
    write_pv: str = Field(
        None,
        description="The pv to put to, None means not writeable (a readback)",
    )
    # The following are None to allow multiple references to channels
    widget: Widget = Field(None, description="Which widget to use for the Channel")
    description: str = Field(None, description="Description of what the Channel does")
    display_form: DisplayForm = Field(
        None,
        description="How should numeric values be displayed",
    )


class DeviceInstance(WithLabel):
    type: str = Field("DeviceInstance", const=True)
    id: str = Field(None, description="The id of this device, None means use name")
    file: Path = Field(
        ...,
        description="The filename to read device definition (ending .coniql.yaml)",
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
    _cache: Dict[str, str] = {}
    children: Sequence[Child]

    @classmethod
    def from_yaml(cls, path: Path, macros: Dict[str, str] = None) -> "DeviceConfig":
        abspath = str(path.resolve())
        try:
            text = cls._cache[abspath]
        except KeyError:
            text = path.read_text()
            cls._cache[abspath] = text
        if macros:
            for k, v in macros.items():
                text = text.replace(f"$({k})", v)
        device_config = cls(**YAML().load(text))
        return device_config


DeviceConfig.update_forward_refs()


def walk(tree: Sequence[Child]) -> Iterator[Child]:
    """Depth first traversal of tree"""
    for t in tree:
        yield t
        if isinstance(t, Group):
            yield from walk(t.children)


if __name__ == "__main__":
    print(DeviceConfig.schema_json(indent=2))
