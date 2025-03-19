from traceback import format_exception

from quart import Blueprint
from quart import current_app
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException


def api_error(message: str, status_code: int = 500):
    return {"error": message}, status_code


def api_exception(e: Exception, status_code: int = 500):
    return api_error(f"{type(e).__name__}: {e}", status_code)


def register_error_handlers(bp: Blueprint):
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
