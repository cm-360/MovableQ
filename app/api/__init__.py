from quart import Blueprint

from sqlalchemy.exc import IntegrityError

from .utils import api_error
from .utils import api_exception


bp = Blueprint("API", __name__)

from . import jobs

@bp.errorhandler(IntegrityError)
def handle_integrity_error(error: IntegrityError):
    return api_exception(error.orig)
