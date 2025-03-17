from dataclasses import asdict
from dataclasses import fields
from dataclasses import is_dataclass
from typing import Type
from typing import TypeVar


class Serializable:
    """Makes serializing dataclasses as dictionaries more flexible."""

    def __iter__(self):
        for k, v in asdict(self).items():
            yield k, v


T = TypeVar("T")


def from_dict(target_class: Type[T], data: dict) -> T:
    """Unpacks a dictionary into a new instance of the specified dataclass.

    Args:
        target_class (Type[T]): The dataclass type to instantiate.
        data (dict): A dictionary of data to unpack from.

    Returns:
        T: An instance of the target dataclass populated with the given data.

    Raises:
        ValueError: If the target class is not a dataclass.

    Note:
        The functionality is based on
        https://medium.com/@emirhalici/unlocking-the-power-of-python-data-classes-w-json-serialization-3e5a24d98e84.
    """
    if not is_dataclass(target_class):
        raise ValueError(f"{target_class.__name__} is not a dataclass")

    field_names = [field.name for field in fields(target_class)]
    kwargs = {k: v for k, v in data.items() if k in field_names}

    return target_class(**kwargs)
