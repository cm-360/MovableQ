def allowed_job_types(*job_types: str):
    def decorator(cls):
        cls._allowed_job_types = [*getattr(cls, "_allowed_job_types", []), *job_types]
        return cls

    return decorator
