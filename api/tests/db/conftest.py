from pytest import fixture

from app.db import create_db


@fixture
def db():
    db = create_db("sqlite:///:memory:", echo=True)
    db.create_all()

    return db
