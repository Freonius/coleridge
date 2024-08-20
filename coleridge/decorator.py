from typing import Generic, TypeVar, Type, Union, List, Callable
from pydantic import BaseModel
from .decorated import DecoratedBackgroundFunction

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class ColeridgeDecorator(Generic[T, U]):
    _input_type: Type[T]
    _output_type: Type[U]
    _on_finish: Union[Callable[[Union[U, List[U]]], None], None]
    _on_error: Union[Callable[[Exception], None], None]
    _on_finish_signal: Union[Callable[[], None], None]

    def __init__(
        self,
        input_type: Type[T],
        output_type: Type[U],
        *,
        on_finish: Union[Callable[[Union[U, List[U]]], None], None] = None,
        on_error: Union[Callable[[Exception], None], None] = None,
        on_finish_signal: Union[Callable[[], None], None] = None,
    ) -> None:
        self._input_type = input_type
        self._output_type = output_type
        self._on_finish = on_finish
        self._on_error = on_error
        self._on_finish_signal = on_finish_signal

    def __call__(
        self, func: Callable[[Union[T, List[T]]], Union[U, List[U]]]
    ) -> DecoratedBackgroundFunction[T, U]:
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
