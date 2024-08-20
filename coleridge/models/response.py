"""Response model"""

from datetime import datetime
from typing import Union, TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ResultModel(BaseModel, Generic[T]):
    """Response model"""

    result: Union[T, List[T], None] = None
    started: Union[datetime, None] = None
    completed: Union[datetime, None] = None
    error: Union[Exception, None] = None

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic config"""

        arbitrary_types_allowed = True


__all__ = ("ResultModel",)
