"""Response model"""

from datetime import datetime
from typing import Union, TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Response(BaseModel, Generic[T]):
    """Response model"""

    data: Union[T, List[T], None] = None
    error: Union[Exception, None]
    started: Union[datetime, None] = None
    completed: Union[datetime, None] = None
