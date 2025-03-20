from dataclasses import asdict
from functools import reduce

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import MappedAsDataclass


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for declarative ORM mapping with SQLAlchemy."""

    @classmethod
    def primary_key_matches(cls, keys: dict):
        primary_key_columns = inspect(cls).primary_key

        clauses = [c == keys[c.name] for c in primary_key_columns]
        joined_clauses = reduce(lambda c1, c2: c1 & c2, clauses)

        return joined_clauses


class GenericBase(MappedAsDataclass):
    """Model dataclass base with flexible dictionary serialization."""

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

    def __iter__(self):
        for k, v in asdict(self).items():
            yield k, v
