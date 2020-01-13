from typing import TypeVar

from device.types.result import Result

T = TypeVar('T')


class MockWorkingResult(Result[T]):
    def __init__(self, value):
        self.__value = value

    def is_present(self) -> bool:
        return True

    def is_error(self) -> bool:
        return False

    def or_raise(self, err: Exception = None) -> T:
        return self.__value


class MockErrorResult(Result[T]):
    def is_present(self) -> bool:
        return False

    def is_error(self) -> bool:
        return True

    def or_raise(self, err: Exception) -> T:
        raise err
