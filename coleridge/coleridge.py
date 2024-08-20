"""The Coleridge class"""

from pathlib import Path
from typing import Literal, Callable, Union, List, cast
from .decorator import ColeridgeDecorator, T, U
from .decorated import DecoratedBackgroundFunction
from .models.connection import Connection
from .rabbit import RabbitBackgroundFunction
from .get_types import get_params_type


class Coleridge:
    """The Coleridge class is a decorator that allows you to easily \
    create decorators that can be used to decorate functions with RabbitMQ \
    or background tasks.
    """

    _connection_settings: Union[Connection, None, str, Path]
    _queue: Union[str, None]
    _mode: Literal["rabbit", "background"]

    def __init__(
        self,
        connection_settings: Union[Connection, None, str, Path] = None,
        queue: Union[str, None] = None,
        mode: Literal["rabbit", "background"] = "background",
    ) -> None:
        """
        Initializes a Coleridge object.

        Args:
            connection_settings (Union[Connection, None, str, Path]): The connection \
                settings for the Coleridge object. Defaults to None.
            queue (Union[str, None]): The queue for the Coleridge object. Defaults to None.
            mode (Literal["rabbit", "background"]): The mode for the Coleridge object. \
              Defaults to "background".

        Returns:
            None
        """
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
        """
        A decorator function that creates a ColeridgeDecorator instance and \
        returns a decorated function.
        
        Parameters:
        queue (Union[str, None]): The queue to be used for the decorated function.
        on_finish (Union[Callable[[Union[U, List[U]]], None], None]): The callback \
        function to be executed when the decorated function finishes.
        on_error (Union[Callable[[Exception], None], None]): The callback function to be \
            executed when the decorated function encounters an error.
        on_finish_signal (Union[Callable[[], None], None]): The callback function to be \
        executed when the decorated function finishes with a signal.
        
        Returns:
        Callable[[Callable[[Union[T, List[T]]], Union[U, List[U]]]], \
            Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]]]: \
                A decorator function that takes a function as input and returns a \
                    decorated function.
        """

        def _inner(
            func: Callable[[Union[T, List[T]]], Union[U, List[U]]]
        ) -> Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]]:
            """
            Inner function of the magic decorator, responsible for creating a \
                ColeridgeDecorator instance.
            
            Parameters:
            func (Callable[[Union[T, List[T]]], Union[U, List[U]]]): The function to be decorated.
            
            Returns:
            Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]]: The \
            decorated function.
            """
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
        self,
        func: Callable[[Union[T, List[T]]], Union[U, List[U]]],
    ) -> Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]]:
        """
        Calls the magic decorator function with the provided function as an argument.

        Parameters:
        func (Callable[[Union[T, List[T]]], Union[U, List[U]]]): The function to be decorated.

        Returns:
        Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]]: \
            The decorated function.
        """
        return cast(
            Union[DecoratedBackgroundFunction[T, U], RabbitBackgroundFunction[T, U]],
            self.magic_decorator()(
                func,  # type: ignore[arg-type]
            ),
        )


__all__ = ("Coleridge",)
