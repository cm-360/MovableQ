from pytest import fixture

from app.db import create_db


@fixture
def db():
    db = create_db("sqlite:///:memory:", echo=False)
    db.create_all()

    return db
