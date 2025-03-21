import re
from datetime import timezone
from datetime import datetime


camel_case_pattern = re.compile(r"(?<!^)(?=[A-Z])")


def camel_to_kebab_case(value: str) -> str:
    """Converts a CamelCase name to kebab-case.

    This is used to convert subclass names to type identifiers.

    Based on: https://stackoverflow.com/a/1176023
    """
    return camel_case_pattern.sub("-", value).lower()


def format_timestamp(timestamp: datetime | None) -> str | None:
    if timestamp is None:
        return

    return timestamp.replace(tzinfo=timezone.utc).isoformat()
