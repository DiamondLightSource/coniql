from typing import TypeVar, Callable, Coroutine, Any

TChannel = TypeVar('TChannel')

AsyncChannelMaker = Coroutine[Any, Any, TChannel]
Connector = Callable[[], AsyncChannelMaker]
