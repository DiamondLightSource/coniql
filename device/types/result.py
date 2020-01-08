from typing import TypeVar, Generic, Iterable

T = TypeVar('T')


class Result(Generic[T]):
    """Generic wrapper for the result of interaction with a channel or error"""
    def is_present(self) -> bool:
        return NotImplemented

    def is_error(self) -> bool:
        return NotImplemented

    def or_raise(self, err: Exception) -> T:
        return NotImplemented
