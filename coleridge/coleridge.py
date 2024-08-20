from pathlib import Path
from typing import Any, Literal, Callable, Union, List, Literal, Type
from .decorator import ColeridgeDecorator, T, U
from .decorated import DecoratedBackgroundFunction
from .models.connection import Connection
from .rabbit import RabbitBackgroundFunction
from .get_types import get_params_type


class Coleridge:
    _connection_settings: Union[Connection, None, str, Path]
    _queue: Union[str, None]
    _mode: Literal["rabbit", "background"]

    def __init__(
        self,
        connection_settings: Union[Connection, None, str, Path] = None,
        queue: Union[str, None] = None,
        mode: Literal["rabbit", "background"] = "background",
    ) -> None:
        self._connection_settings = connection_settings
        self._queue = queue
        self._mode = mode

    def magic_decorator(
        self,
        queue: Union[str, None] = None,
        on_finish: Union[Callable[[Union[U, List[U]]], None], None] = None,
        on_error: Union[Callable[[Exception], None], None] = None,
        on_finish_signal: Union[Callable[[], None], None] = None,
    ) -> Callable[
        [Callable[[Union[T, List[T]]], Union[U, List[U]]]],
        Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]],
    ]:
        def _inner(
            func: Callable[[Union[T, List[T]]], Union[U, List[U]]]
        ) -> Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]]:
            input_type, output_type = get_params_type(func)
            dec = ColeridgeDecorator(
                input_type,
                output_type,
                mode=self._mode,
                connection_settings=self._connection_settings,
                queue=self._queue if queue is None else queue,
                on_finish=on_finish,
                on_error=on_error,
                on_finish_signal=on_finish_signal,
            )
            return dec(func)

        return _inner

    def __call__(
        self, func: Callable[[Union[T, List[T]]], Union[U, List[U]]]
    ) -> Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]]:
        return self.magic_decorator()(func)
