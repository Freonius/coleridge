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
from pickle import dumps, loads
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
    """ """

    _data: Dict[str, ResultModel]
    _input_type: Type[T]
    _output_type: Type[U]
    _on_finish: Callable[[Union[U, List[U]]], None]
    _on_error: Callable[[Exception], None]
    _on_finish_signal: Callable[[], None]
    func: Callable[[Union[T, List[T]]], Union[U, List[U]]]
    _queue: str
    _client: BlockingConnection
    _channel: BlockingChannel

    def __init__(
        self,
        func: Callable[[Union[T, List[T]]], Union[U, List[U]]],
        input_type: Type[T],
        output_type: Type[U],
        connection_settings: Union[Connection, None, str, Path] = None,
        queue: Union[str, None] = None,
    ) -> None:
        """ """
        _host: str
        if connection_settings is None:
            connection_settings = Connection()
        if isinstance(connection_settings, str):
            connection_settings = Path(connection_settings)
        if isinstance(connection_settings, Path):
            if not connection_settings.exists():
                raise Exception(f"File {connection_settings} does not exist")
            with open(connection_settings, "r", encoding="utf-8") as _f:
                _settings = load(_f, Loader=SafeLoader)
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

    def run(self, what: Union[T, List[T], str]) -> Result[U]:
        uuid = str(uuid4())
        self._data[uuid] = ResultModel(started=datetime.now())

        self._channel.queue_declare(queue=self._queue)
        self._channel.basic_publish(
            exchange="", routing_key=self._queue, body=dumps(what)
        )

        def _background_task(
            func: Callable[[Union[T, List[T], str]], Union[U, List[U]]],
        ):
            self._listen(uuid, func)
            self._start()

        _th: Thread = Thread(
            target=_background_task,
            args=(cast("Callable[[Union[T, List[T]]], Union[U, List[U]]]", self.func),),
            daemon=True,
        )
        _th.start()

        res: Result[U] = Result(
            uuid,
            self,  # type: ignore[arg-type]
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
        """ """
        self._channel.queue_declare(queue=self._queue)

        # pylint: disable=unused-argument,invalid-name
        def _internal_callback(a: Any, b: Any, c: Any, bingpot: AnyStr) -> None:
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
            except Exception as ex:
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
        """Close the connection and deletes the queue. (This function is called
        when used in the `with` context.)
        """
        self.stop()
        self.delete_queue()
        self._client.close()

    def _is_connected(self) -> bool:
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
        """
        Property indicating whether the client is connected to the database.
        """
        return self._is_connected()

    def __getitem__(self, key: str) -> ResultModel:
        return self._data[key]

    def __setitem__(self, key: str, value: ResultModel) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]
