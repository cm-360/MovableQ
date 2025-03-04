def api_error(message: str, status_code: int=500):
    return { "error": message }, status_code

def api_exception(e: Exception, status_code: int=500):
    return api_error(f"{type(e).__name__}: {e}", status_code)
