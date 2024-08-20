from datetime import datetime
from uuid import uuid4
from threading import Thread
from json import loads
from typing import TypeVar, Generic, Callable, Union, List, Dict, Type, cast
from pydantic import BaseModel
from .models.response import ResultModel
from .result import ExecutionResult as Result

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class DecoratedBackgroundFunction(Generic[T, U]):
    _data: Dict[str, ResultModel]
    _input_type: Type[T]
    _output_type: Type[U]
    _on_finish: Callable[[Union[U, List[U]]], None]
    _on_error: Callable[[Exception], None]
    _on_finish_signal: Callable[[], None]
    func: Callable[[Union[T, List[T]]], U]

    def __init__(
        self,
        func: Callable[[Union[T, List[T]]], Union[U, List[U]]],
        input_type: Type[T],
        output_type: Type[U],
    ) -> None:
        self.func = func
        self._data = {}
        self._input_type = input_type
        self._output_type = output_type

        self._on_finish = lambda x: None
        self._on_error = lambda x: None
        self._on_finish_signal = lambda: None

    @property
    def on_finish(self) -> Callable[[Union[U, List[U]]], None]:
        return self._on_finish

    @on_finish.setter
    def on_finish(self, value: Callable[[Union[U, List[U]]], None]) -> None:
        self._on_finish = value

    @property
    def on_error(self) -> Callable[[Exception], None]:
        return self._on_error

    @on_error.setter
    def on_error(self, value: Callable[[Exception], None]) -> None:
        self._on_error = value

    @property
    def on_finish_signal(self) -> Callable[[], None]:
        return self._on_finish_signal

    @on_finish_signal.setter
    def on_finish_signal(self, value: Callable[[], None]) -> None:
        self._on_finish_signal = value

    def _run_background(self, input_value: Union[T, List[T], str], uuid: str) -> None:
        try:
            if isinstance(input_value, str):
                input_value = loads(input_value)
            if isinstance(input_value, list):
                input_value = [
                    self._input_type.model_validate(i) if isinstance(i, dict) else i
                    for i in input_value
                ]
            if isinstance(input_value, dict):
                input_value = self._input_type.model_validate(input_value)
            self._data[uuid].result = self.func(cast("Union[T, List[T]]", input_value))
        except Exception as ex:
            self._data[uuid].error = ex
        finally:
            self._data[uuid].completed = datetime.now()

    def run(
        self, input_value: Union[T, List[T], str], timeout: Union[float, None] = None
    ) -> Result[U]:
        uuid = str(uuid4())
        self._data[uuid] = ResultModel(started=datetime.now())

        t = Thread(target=self._run_background, args=(input_value, uuid))
        t.start()
        res: Result[U] = Result(
            uuid,
            self,
            self._on_finish,
            self._on_error,
            self._on_finish_signal,
        )
        res.connect()
        return res

    def __getitem__(self, key: str) -> ResultModel:
        return self._data[key]

    def __setitem__(self, key: str, value: ResultModel) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]
