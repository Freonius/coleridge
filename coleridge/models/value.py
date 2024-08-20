"""Value model"""

from typing import Any, Union
from pydantic import BaseModel


class Value(BaseModel):
    """Value model"""

    value: Union[Any, None]

    class Config:
        """Config"""

        arbitrary_types_allowed = True


__all__ = ("Value",)
