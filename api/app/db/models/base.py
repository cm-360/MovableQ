from dataclasses import asdict
from functools import reduce

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


class Serializable:
    """Provides flexible dictionary serialization for dataclasses."""

    def __iter__(self):
        for k, v in asdict(self).items():
            yield k, v


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


class GenericBase(MappedAsDataclass, Serializable, Superclass):
    pass
