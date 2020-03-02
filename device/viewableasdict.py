from typing_extensions import Protocol, runtime_checkable


@runtime_checkable
class ViewableAsDict(Protocol):
    def dict_view(self):
        return NotImplemented
