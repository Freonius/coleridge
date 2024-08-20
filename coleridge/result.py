from contextlib import suppress
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, Union, List
from datetime import datetime
from threading import Thread
from pydantic import BaseModel

U = TypeVar("U", bound=BaseModel)

if TYPE_CHECKING:  # pragma: no cover
    from .decorated import DecoratedBackgroundFunction


class ExecutionResult(Generic[U]):
    _dec: "DecoratedBackgroundFunction"
    _on_finish: "Callable[[Union[U, List[U]]], None]"
    _on_error: Callable[[Exception], None]
    _on_finish_signal: "Callable[[], None]"
    _started_thread: bool

    def __init__(
        self,
        uuid: str,
        dec: "DecoratedBackgroundFunction",
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
        return self._uuid

    @property
    def result(self) -> Union[U, List[U], None]:
        return self._dec[self.uuid].result

    @property
    def started(self) -> Union[datetime, None]:
        return self._dec[self.uuid].started

    @property
    def completed(self) -> Union[datetime, None]:
        return self._dec[self.uuid].completed

    @property
    def finished(self) -> bool:
        return self._dec[self.uuid].completed is not None

    @property
    def error(self) -> Union[Exception, None]:
        return self._dec[self.uuid].error

    @property
    def success(self) -> bool:
        return self._dec[self.uuid].error is None and self.finished

    def _check(
        self,
        timeout: Union[float, None] = None,
    ) -> None:
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
        if self._started_thread:
            return
        t = Thread(target=self._check)
        t.start()
        self._started_thread = True

    def __del__(self) -> None:
        with suppress(KeyError):
            del self._dec[self.uuid]
