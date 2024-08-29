"""Cron background operations"""

from typing import Callable
from datetime import datetime
from time import sleep
from threading import Thread
from croniter import croniter  # type: ignore[import-untyped]


class CronDecorator:
    """Decorate a function to be executed according to a cron expression.

    ```python
    from coleridge import CronDecorator

    @CronDecorator('*/5 * * * *')  # The function will be executed every five minutes
    def funk():
        print('Called')
    ```
    """

    _expr: str
    _cron: croniter

    def __init__(self, expr: str) -> None:
        """Initializes a new instance of the CronDecorator class.

        Args:
            expr (str): The cron expression.

        Returns:
            None
        """
        self._expr = expr
        self._cron = croniter(str(self._expr), datetime.now(), datetime)

    def __call__(self, func: Callable[[], None]) -> Callable[[], None]:
        """Decorate a function to be executed according to a cron expression.

        Args:
            func (Callable[[], None]): The function to be decorated.

        Returns:
            Callable[[], None]: The decorated function.
        """

        def _inner(cron: croniter, func: Callable[[], None]) -> None:
            _next: datetime = cron.get_next(datetime)
            while True:
                if _next > datetime.now():
                    sleep(0.5)
                    continue
                func()
                _next = cron.get_next()

        _t: Thread = Thread(target=_inner, args=(self._cron, func), daemon=True)
        _t.start()
        return func


__all__ = ("CronDecorator",)
