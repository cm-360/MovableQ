from __future__ import annotations

from dataclasses import asdict
from dataclasses import fields
from dataclasses import is_dataclass
from functools import reduce
from typing import Any
from typing import Type

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import MappedAsDataclass

from app.utils.strings import camel_to_kebab_case


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for declarative ORM mapping with SQLAlchemy."""

    @classmethod
    def primary_key_matches(cls, keys: dict):
        primary_key_columns = inspect(cls).primary_key

        clauses = [c == keys[c.name] for c in primary_key_columns]
        joined_clauses = reduce(lambda c1, c2: c1 & c2, clauses)

        return joined_clauses


class Serializable(MappedAsDataclass):
    """Dataclass with flexible dictionary serialization and ."""

    def __iter__(self):
        for k, v in asdict(self).items():
            yield k, v

    @classmethod
    def from_dict(cls, data: dict) -> Serializable:
        """Unpacks a dictionary into a new instance of a dataclass.

        Args:
            data (dict): A dictionary of data to unpack from.

        Returns:
            Serializable: A dataclass instance populated with the given data.

        Raises:
            ValueError: If no value is specified for a required field.

        Note:
            The instantiation functionality is based on
            https://medium.com/@emirhalici/unlocking-the-power-of-python-data-classes-w-json-serialization-3e5a24d98e84.
        """
        required_fields = [
            f.name for f in fields(cls) if not isinstance(f.type, type(Any | None))
        ]
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        field_names = [f.name for f in fields(cls)]
        kwargs = {k: data.get(k) for k in field_names}

        return cls(**kwargs)


class Superclass:
    @classmethod
    def get_all_subclasses(cls):
        """Finds all subclasses of this class.

        From: https://stackoverflow.com/a/17246726
        """
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(subclass.get_all_subclasses())

        return all_subclasses

    @classmethod
    def subclass_id(cls) -> str:
        for base_class in cls.__bases__:
            if issubclass(base_class, Superclass) and base_class is not Superclass:
                superclass_name = base_class.__name__
                return camel_to_kebab_case(cls.__name__.removesuffix(superclass_name))

    @classmethod
    def get_subclass(cls, subclass_id: str) -> type | None:
        for subclass in cls.get_all_subclasses():
            if subclass.subclass_id() == subclass_id:
                return subclass


class GenericBase(Serializable, Superclass):
    pass
