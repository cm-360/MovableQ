def api_error(message: str, status_code: int=500):
    response = {
        "error": message,
        "message": message
    }
    return response, status_code

def api_exception(error: Exception, status_code: int=500):
    return api_error(f"{type(error).__name__}: {error}", status_code)
