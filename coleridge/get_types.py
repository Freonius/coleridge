"""Get the types of the parameters and return values of a function."""

from typing import Tuple, Callable, Type, Union, List, TypeVar
from inspect import signature
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


def get_params_type(
    func: Callable[[Union[T, List[T]]], Union[U, List[U]]]
) -> Tuple[Type[T], Type[U]]:
    """Get the types of the parameters and return values of a function."""
    sig = signature(func)
    key = list(sig.parameters.keys())[0]
    first_param_type = sig.parameters[key].annotation
    return_type = sig.return_annotation
    if first_param_type is Union:
        first_param_type = first_param_type.__args__[0]
    elif first_param_type is List:
        first_param_type = first_param_type.__args__[0]
    if return_type is Union:
        return_type = return_type.__args__[0]
    elif return_type is List:
        return_type = return_type.__args__[0]
    if not issubclass(first_param_type, BaseModel):
        raise TypeError(f"{first_param_type} is not a BaseModel")
    if not issubclass(return_type, BaseModel):
        raise TypeError(f"{return_type} is not a BaseModel")
    return first_param_type, return_type


__all__ = ("get_params_type",)
