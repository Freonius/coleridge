from pathlib import Path
from typing import Generic, TypeVar, Type, Union, List, Callable, Literal
from pydantic import BaseModel
from .decorated import DecoratedBackgroundFunction
from .models.connection import Connection
from .rabbit import RabbitBackgroundFunction

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class ColeridgeDecorator(Generic[T, U]):
    _input_type: Type[T]
    _output_type: Type[U]
    _on_finish: Union[Callable[[Union[U, List[U]]], None], None]
    _on_error: Union[Callable[[Exception], None], None]
    _on_finish_signal: Union[Callable[[], None], None]
    _mode: Literal["rabbit", "background"]
    _connection_settings: Union[Connection, None, str, Path]
    _queue: Union[str, None]

    def __init__(
        self,
        input_type: Type[T],
        output_type: Type[U],
        *,
        mode: Literal["rabbit", "background"] = "background",
        connection_settings: Union[Connection, None, str, Path] = None,
        queue: Union[str, None] = None,
        on_finish: Union[Callable[[Union[U, List[U]]], None], None] = None,
        on_error: Union[Callable[[Exception], None], None] = None,
        on_finish_signal: Union[Callable[[], None], None] = None,
    ) -> None:
        self._input_type = input_type
        self._output_type = output_type
        self._on_finish = on_finish
        self._on_error = on_error
        self._on_finish_signal = on_finish_signal

        self._mode = mode
        self._connection_settings = connection_settings
        self._queue = queue

    def __call__(
        self,
        func: Callable[[Union[T, List[T]]], Union[U, List[U]]],
    ) -> Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]]:
        if self._mode == "rabbit":
            rabbit: RabbitBackgroundFunction[T, U] = RabbitBackgroundFunction(
                func,
                self._input_type,
                self._output_type,
                connection_settings=self._connection_settings,
                queue=self._queue,
            )
            if self._on_finish is not None:
                rabbit.on_finish = self._on_finish
            if self._on_error is not None:
                rabbit.on_error = self._on_error
            if self._on_finish_signal is not None:
                rabbit.on_finish_signal = self._on_finish_signal
            return rabbit
        dec: DecoratedBackgroundFunction[T, U] = DecoratedBackgroundFunction(
            func,  # type: ignore[arg-type]
            self._input_type,
            self._output_type,
        )
        if self._on_finish is not None:
            dec.on_finish = self._on_finish
        if self._on_error is not None:
            dec.on_error = self._on_error
        if self._on_finish_signal is not None:
            dec.on_finish_signal = self._on_finish_signal
        return dec
