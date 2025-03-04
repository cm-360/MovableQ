from traceback import format_exception

from quart import Blueprint
from quart import current_app

from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from .utils import api_exception


bp = Blueprint("API", __name__)


@bp.errorhandler(Exception)
def handle_exception(e: Exception):
    # Pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    # Log exception and traceback
    current_app.logger.error("Uncaught exception")
    for line in format_exception(type(e), e, e.__traceback__):
        current_app.logger.error(line.rstrip("\n"))

    return api_exception(e)


@bp.errorhandler(IntegrityError)
def handle_integrity_error(e: IntegrityError):
    return api_exception(e.orig)
