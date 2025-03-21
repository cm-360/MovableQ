from datetime import timezone


def format_timestamp(timestamp: str | None) -> str | None:
    if timestamp is None:
        return

    return timestamp.replace(tzinfo=timezone.utc).isoformat()
