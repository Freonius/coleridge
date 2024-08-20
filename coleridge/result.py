"""Execution result"""

from contextlib import suppress
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, Union, List, Any
from datetime import datetime
from threading import Thread
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)

if TYPE_CHECKING:  # pragma: no cover
    from .decorated import DecoratedBackgroundFunction
    from .rabbit import RabbitBackgroundFunction


class ExecutionResult(Generic[U]):
    """Execution result"""

    _dec: "Union[DecoratedBackgroundFunction[Any, U], RabbitBackgroundFunction[Any, U]]"
    _on_finish: "Callable[[Union[U, List[U]]], None]"
    _on_error: Callable[[Exception], None]
    _on_finish_signal: "Callable[[], None]"
    _started_thread: bool

    def __init__(  # noqa: D107 # pylint: disable=too-many-arguments
        self,
        uuid: str,
        dec: "Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]]",
        on_finish: "Callable[[Union[U, List[U]]], None]",
        on_error: Callable[[Exception], None],
        on_finish_signal: "Callable[[], None]",
    ) -> None:
        self._uuid = uuid
        self._dec = dec
        self._on_finish = on_finish
        self._on_error = on_error
        self._on_finish_signal = on_finish_signal
        self._started_thread = False

    _uuid: str

    @property
    def uuid(self) -> str:
        """The UUID of the execution result"""
        return self._uuid

    @property
    def result(self) -> Union[U, List[U], None]:
        """The result of the execution"""
        return self._dec[self.uuid].result

    @property
    def started(self) -> Union[datetime, None]:
        """The start time of the execution"""
        return self._dec[self.uuid].started

    @property
    def completed(self) -> Union[datetime, None]:
        """The completion time of the execution"""
        return self._dec[self.uuid].completed

    @property
    def finished(self) -> bool:
        """Whether the execution is finished"""
        return self._dec[self.uuid].completed is not None

    @property
    def error(self) -> Union[Exception, None]:
        """The error of the execution"""
        return self._dec[self.uuid].error

    @property
    def success(self) -> bool:
        """Whether the execution was successful"""
        return self._dec[self.uuid].error is None and self.finished

    def _check(
        self,
        timeout: Union[float, None] = None,  # pylint: disable=unused-argument
    ) -> None:
        """
        Check the execution result and perform the necessary actions based on the result status.

        This method continuously checks the status of the execution result. If an error is \
              present, it calls the `_on_error` callback function with the error as an \
              argument and returns. If the execution is finished, it retrieves the \
              result and checks if it is None. If it is None, it calls \
              the `_on_error` callback function with a `ValueError` indicating that\
              the result is None and returns. If the result is not None, it calls\
              the `_on_finish` callback function with the result as an argument, \
              calls the `_on_finish_signal` callback function, and returns.

        Parameters:
            timeout (Union[float, None], optional): The maximum time in seconds\
                  to wait for the execution to complete. Defaults to None.

        Returns:
            None
        """
        # TODO: timeout
        while True:
            if self.error is not None:
                self._on_error(self.error)
                return
            if self.finished:
                data = self.result
                if data is None:
                    self._on_error(ValueError("Result is None"))
                    return
                self._on_finish(data)
                self._on_finish_signal()
                return

    def connect(self) -> None:
        """Connect to the background task"""
        if self._started_thread:
            return
        t = Thread(target=self._check)
        t.start()
        self._started_thread = True

    def __del__(self) -> None:
        """Delete the result."""
        with suppress(KeyError):
            del self._dec[self.uuid]


__all__ = ("ExecutionResult", "T", "U")
