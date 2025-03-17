from pytest import fixture

from app import create_app


@fixture()
def app():
    return create_app()


@fixture()
def client(app):
    return app.test_client()
