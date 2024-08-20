"""Module for RabbitMQ utilities
"""

from pathlib import Path
from datetime import datetime
from typing import (
    AnyStr,
    List,
    Union,
    Any,
    Callable,
    Type,
    Generic,
    TypeVar,
    Dict,
    cast,
)
from time import sleep
from uuid import uuid4
from pickle import dumps, loads  # nosec B403
from json import loads as json_loads
from threading import Thread
from yaml import load, SafeLoader
from pika import BlockingConnection, ConnectionParameters, PlainCredentials
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError
from pydantic import BaseModel
from .models.connection import Connection
from .models.response import ResultModel
from .result import ExecutionResult as Result

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class RabbitBackgroundFunction(Generic[T, U]):
    """Background function using RabbitMQ"""

    _data: Dict[str, ResultModel[U]]
    _input_type: Type[T]
    _output_type: Type[U]
    _on_finish: Callable[[Union[U, List[U]]], None]
    _on_error: Callable[[Exception], None]
    _on_finish_signal: Callable[[], None]
    func: Callable[[Union[T, List[T]]], Union[U, List[U]]]
    _queue: str
    _client: BlockingConnection
    _channel: BlockingChannel

    def __init__(  # noqa: C901, PLR0912, PLR0915
        self,
        func: Callable[[Union[T, List[T]]], Union[U, List[U]]],
        input_type: Type[T],
        output_type: Type[U],
        connection_settings: Union[Connection, None, str, Path] = None,
        queue: Union[str, None] = None,
    ) -> None:
        """
        Initializes a new instance of the RabbitBackgroundFunction class.

        Args:
            func (Callable[[Union[T, List[T]]], Union[U, List[U]]]): The function to be \
                executed in the background.
            input_type (Type[T]): The type of the input data.
            output_type (Type[U]): The type of the output data.
            connection_settings (Union[Connection, None, str, Path], optional): The connection \
                settings for the RabbitMQ server. Defaults to None.
            queue (Union[str, None], optional): The name of the queue to use. Defaults to None.

        Returns:
            None
        """
        _host: str
        if connection_settings is None:
            connection_settings = Connection()
        if isinstance(connection_settings, str):
            connection_settings = Path(connection_settings)
        if isinstance(connection_settings, Path):
            if not connection_settings.exists():
                raise FileNotFoundError(f"File {connection_settings} does not exist")
            with open(connection_settings, "r", encoding="utf-8") as _f:
                _settings = load(_f, Loader=SafeLoader)
                if not isinstance(_settings, dict):
                    raise TypeError(f"{_settings} is not a dict")
                _settings = cast(Dict[str, Any], _settings)
                if "rabbit" not in _settings:
                    raise ValueError(f"{_settings} does not contain 'rabbit'")
                _settings = cast(Dict[str, Any], _settings["rabbit"])
                if not isinstance(_settings, dict):
                    raise TypeError(f"{_settings} is not a dict")
                _settings = cast(Dict[str, Any], _settings)
                connection_settings = Connection.model_validate(_settings)

        _host = connection_settings.host

        if queue is None:
            # It should throw an exception, because I don't know which one to use
            queue = str(uuid4())

        _port: int = connection_settings.port

        _username: Union[str, None] = connection_settings.username
        _password: Union[str, None] = connection_settings.password
        _credentials: PlainCredentials
        if (
            _username is None
            or _username.strip() == ""
            or _password is None
            or _password.strip() == ""
        ):
            _credentials = ConnectionParameters.DEFAULT_CREDENTIALS
        else:
            _credentials = PlainCredentials(_username, _password)
        _retries: int = connection_settings.retries
        _retries = max(_retries, 1)
        _sleep_between: float = connection_settings.time_between_retries
        _sleep_between = max(_sleep_between, 0.1)
        for _i in range(_retries):
            try:
                self._client = BlockingConnection(
                    ConnectionParameters(
                        host=_host, port=_port, credentials=_credentials
                    )
                )
                break
            except AMQPConnectionError as _e:
                if (_i + 1) == _retries:
                    raise _e
                sleep(_sleep_between)
        self._queue = queue
        self._channel = self._client.channel()
        self.func = func
        self._data = {}
        self._input_type = input_type
        self._output_type = output_type

        self._on_finish = lambda x: None
        self._on_error = lambda x: None
        self._on_finish_signal = lambda: None

    @property
    def on_finish(self) -> Callable[[Union[U, List[U]]], None]:
        """Get a function to be called when the function is finished with a result"""
        return self._on_finish

    @on_finish.setter
    def on_finish(self, value: Callable[[Union[U, List[U]]], None]) -> None:
        """Set a function to be called when the function is finished with a result"""
        self._on_finish = value

    @property
    def on_error(self) -> Callable[[Exception], None]:
        """Get a function to be called when the function raises an exception"""
        return self._on_error

    @on_error.setter
    def on_error(self, value: Callable[[Exception], None]) -> None:
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

    def run(self, what: Union[T, List[T], str]) -> Result[U]:
        """Send a message to the queue"""
        uuid = str(uuid4())
        self._data[uuid] = ResultModel(started=datetime.now())

        self._channel.queue_declare(queue=self._queue)
        self._channel.basic_publish(
            exchange="", routing_key=self._queue, body=dumps(what)
        )

        def _background_task(
            func: Callable[[Union[T, List[T], str]], Union[U, List[U]]],
        ) -> None:
            """Listen for messages in a separate thread"""
            self._listen(uuid, func)
            self._start()

        _th: Thread = Thread(
            target=_background_task,
            args=(self.func,),
            daemon=True,
        )
        _th.start()

        res: Result[U] = Result(
            uuid,
            self,
            self._on_finish,
            self._on_error,
            self._on_finish_signal,
        )
        res.connect()
        return res

    def _listen(
        self,
        uuid: str,
        callback: Callable[[Union[T, List[T], str]], Union[U, List[U]]],
    ) -> None:
        """Listen for messages in a separate thread"""
        self._channel.queue_declare(queue=self._queue)

        # pylint: disable=unused-argument,invalid-name
        def _internal_callback(a: Any, b: Any, c: Any, bingpot: AnyStr) -> None:
            """Listen for messages in a separate thread"""
            # pylint: disable=unused-argument
            try:
                if isinstance(bingpot, bytes):
                    bingpot = loads(bingpot)
                if isinstance(bingpot, str):
                    bingpot = json_loads(bingpot)
                if isinstance(bingpot, list):
                    bingpot = [
                        self._input_type.model_validate(i) if isinstance(i, dict) else i
                        for i in bingpot
                    ]
                if isinstance(bingpot, dict):
                    bingpot = self._input_type.model_validate(bingpot)
                self._data[uuid].result = callback(cast("Union[T, List[T]]", bingpot))
            except Exception as ex:  # pylint: disable=broad-except
                self._data[uuid].error = ex
            finally:
                self._data[uuid].completed = datetime.now()

        # pylint: enable=unused-argument,invalid-name
        self._channel.basic_consume(
            queue=self._queue, on_message_callback=_internal_callback, auto_ack=True
        )

    _th: Union[Thread, None] = None

    def _start(self, background: bool = True) -> None:
        """Start consuming messages."""
        if background:
            if self._th is None:

                self._th = Thread(target=self._channel.start_consuming)
                self._th.start()
        else:
            self._channel.start_consuming()

    def stop(self) -> None:
        """Stop consuming. This is called while exiting the context."""
        self._channel.stop_consuming()

    def delete_queue(self) -> None:
        """Delete the queue."""
        self._channel.queue_delete(self._queue)

    def close(self) -> None:
        """Close the connection and deletes the queue."""
        self.stop()
        self.delete_queue()
        self._client.close()

    def _is_connected(self) -> bool:
        """Check if the connection is open."""
        return bool(self._client.is_open)

    @property
    def client(self) -> BlockingConnection:
        """The RabbitMQ client.

        Returns:
            BlockingConnection: The pika client
        """
        return self._client

    @property
    def channel(self) -> BlockingChannel:
        """The BlockingChannel (if you want to do something fancy with it)

        Returns:
            BlockingChannel
        """
        return self._channel

    @property
    def is_connected(self) -> bool:
        """Check if the connection is open."""
        return self._is_connected()

    def __getitem__(self, key: str) -> ResultModel[U]:
        """Get the result."""
        return self._data[key]

    def __setitem__(self, key: str, value: ResultModel[U]) -> None:
        """Set the result."""
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        """Delete the result."""
        del self._data[key]


__all__ = (
    "RabbitBackgroundFunction",
    "T",
    "U",
)
