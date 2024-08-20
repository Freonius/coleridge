from typing import Type, Union, Callable, List
from .decorator import ColeridgeDecorator, T, U


class Coleridge:
    @staticmethod
    def rabbit(
        func: Callable[[Union[T, List[T]]], Union[U, List[U]]],
        input_type: Type[T],
        output_type: Type[U],
        queue_name: str,
        *,
        connection_name: Union[str, None] = None,
        connection_file: Union[str, None] = None,
        timeout: Union[float, None] = None,
        on_finish: Union[Callable[[Union[U, List[U]]], None], None] = None,
        on_error: Union[Callable[[Exception], None], None] = None,
        on_finish_signal: Union[Callable[[], None], None] = None,
    ) -> ColeridgeDecorator[T, U]:
        raise NotImplementedError

    @staticmethod
    def background(
        func: Callable[[Union[T, List[T]]], Union[U, List[U]]],
        input_type: Type[T],
        output_type: Type[U],
        *,
        timeout: Union[float, None] = None,
        on_finish: Union[Callable[[Union[U, List[U]]], None], None] = None,
        on_error: Union[Callable[[Exception], None], None] = None,
        on_finish_signal: Union[Callable[[], None], None] = None,
    ) -> ColeridgeDecorator[T, U]:
        raise NotImplementedError
