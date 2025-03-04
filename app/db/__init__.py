from quart_sqlalchemy import SQLAlchemyConfig
from quart_sqlalchemy.framework import QuartSQLAlchemy

from .models import Base


db = QuartSQLAlchemy(
    config=SQLAlchemyConfig(
        model_class=Base,
        binds=dict(
            default=dict(
                engine=dict(
                    url="sqlite:///:memory:",
                    echo=True,
                    connect_args=dict(check_same_thread=False),
                ),
                session=dict(
                    expire_on_commit=False,
                ),
            )
        ),
    ),
)
