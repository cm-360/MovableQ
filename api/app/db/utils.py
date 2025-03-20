from dataclasses import fields
from dataclasses import is_dataclass
from datetime import timezone
from typing import Any
from typing import Type
from typing import TypeVar

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
        ValueError: If no value is specified for a required field.

    Note:
        The instantiation functionality is based on
        https://medium.com/@emirhalici/unlocking-the-power-of-python-data-classes-w-json-serialization-3e5a24d98e84.
    """
    if not is_dataclass(target_class):
        raise ValueError(f"{target_class.__name__} is not a dataclass")

    required_fields = [
        f.name for f in fields(target_class) if not isinstance(f.type, type(Any | None))
    ]
    missing_fields = [f for f in required_fields if f not in data]

    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    field_names = [f.name for f in fields(target_class)]
    kwargs = {k: data.get(k) for k in field_names}

    return target_class(**kwargs)


def format_timestamp(timestamp: str | None) -> str | None:
    if timestamp is None:
        return

    return timestamp.replace(tzinfo=timezone.utc).isoformat()
