from quart import Blueprint

from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from .utils import api_exception


bp = Blueprint("API", __name__)


@bp.errorhandler(Exception)
def handle_exception(e: Exception):
    # Pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    return api_exception(e)


@bp.errorhandler(IntegrityError)
def handle_integrity_error(e: IntegrityError):
    return api_exception(e.orig)
