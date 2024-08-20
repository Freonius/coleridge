"""Connection model"""

from typing import Union
from pydantic import BaseModel


class Connection(BaseModel):
    """Connection model"""

    # name: str
    host: str = "127.0.0.1"
    port: int = 5672
    username: Union[str, None] = None
    password: Union[str, None] = None
    retries: int = 20
    time_between_retries: float = 5.0


__all__ = ("Connection",)
