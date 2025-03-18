from quart_sqlalchemy import SQLAlchemyConfig
from quart_sqlalchemy.framework import QuartSQLAlchemy

from .models import Base


def create_db(url: str, echo: bool = False) -> QuartSQLAlchemy:
    return QuartSQLAlchemy(
        config=SQLAlchemyConfig(
            model_class=Base,
            binds=dict(
                default=dict(
                    engine=dict(
                        url=url,
                        echo=echo,
                        connect_args=dict(check_same_thread=False),
                    ),
                    session=dict(
                        expire_on_commit=False,
                    ),
                )
            ),
        ),
    )
