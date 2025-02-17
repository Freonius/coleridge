"""Decorated background function"""

from datetime import datetime
from uuid import uuid4
from threading import Thread
from typing import TypeVar, Generic, Callable, Union, Dict, Type
from pydantic import BaseModel
from .models.response import ResultModel
from .result import ExecutionResult as Result

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class DecoratedBackgroundFunction(Generic[T, U]):
    """Decorated background function"""

    _data: Dict[str, ResultModel[U]]
    _input_type: Type[T]
    _output_type: Type[U]
    _on_finish: Callable[[U], None]
    _on_error: Callable[[T, Exception], None]
    _on_finish_signal: Callable[[], None]
    func: Callable[[T], U]

    def __init__(
        self,
        func: Callable[[T], U],
        input_type: Type[T],
        output_type: Type[U],
    ) -> None:
        """
        Initializes a new instance of the DecoratedBackgroundFunction class.

        Args:
            func: A callable function that takes a single argument of type T or a list of T \
                and returns a single value of type U or a list of U.
            input_type: The type of the input argument.
            output_type: The type of the output value.

        Returns:
            None
        """
        self.func = func
        self._data = {}
        self._input_type = input_type
        self._output_type = output_type

        self._on_finish = lambda x: None
        self._on_error = lambda _, x: None
        self._on_finish_signal = lambda: None

    @property
    def on_finish(self) -> Callable[[U], None]:
        """Get a function to be called when the function is finished with a result"""
        return self._on_finish

    @on_finish.setter
    def on_finish(self, value: Callable[[U], None]) -> None:
        """Set a function to be called when the function is finished with a result"""
        self._on_finish = value

    @property
    def on_error(self) -> Callable[[T, Exception], None]:
        """Get a function to be called when the function raises an exception"""
        return self._on_error

    @on_error.setter
    def on_error(self, value: Callable[[T, Exception], None]) -> None:
        """Set a function to be called when the function raises an exception"""
        self._on_error = value

    @property
    def on_finish_signal(self) -> Callable[[], None]:
        """Get a function to be called when a message is received"""
        return self._on_finish_signal

    @on_finish_signal.setter
    def on_finish_signal(self, value: Callable[[], None]) -> None:
        """Set a function to be called when a message is received"""
        self._on_finish_signal = value

    def _run_background(
        self,
        input_value: T,
        uuid: str,
    ) -> None:
        """
        Runs the decorated function in the background with the provided input value and uuid.

        Args:
            input_value: The input value to be passed to the decorated function. It can be a \
                  string, a list, or a dictionary.
            uuid: A unique identifier for the background task.

        Returns:
            None
        """
        try:
            self._data[uuid].result = self.func(input_value)
        except Exception as ex:  # pylint: disable=broad-except
            self._data[uuid].error = ex
        finally:
            self._data[uuid].completed = datetime.now()

    def run(  # noqa: D102
        self,
        input_value: T,
        timeout: Union[float, None] = None,  # pylint: disable=unused-argument
    ) -> Result[T, U]:
        """
        Run a background task with the given input value and optional timeout.

        Args:
            input_value: The input value to be processed by the background task.
            timeout: The maximum time in seconds to wait for the task to complete.

        Returns:
            A Result object representing the outcome of the background task.
        """
        uuid = str(uuid4())
        self._data[uuid] = ResultModel(started=datetime.now())

        t = Thread(target=self._run_background, args=(input_value, uuid))
        t.start()
        res: Result[T, U] = Result(
            uuid,
            self,
            self._on_finish,
            self._on_error,
            self._on_finish_signal,
            input_value,
        )
        res.connect()
        return res

    def __getitem__(self, key: str) -> ResultModel[U]:
        """Get the result."""
        return self._data[key]

    def __setitem__(self, key: str, value: ResultModel[U]) -> None:
        """Set the result."""
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        """Delete the result."""
        del self._data[key]
