import re

camel_case_pattern = re.compile(r"(?<!^)(?=[A-Z])")


def camel_to_kebab_case(value: str) -> str:
    """Converts a CamelCase name to kebab-case.

    This is used to convert subclass names to type identifiers.

    Based on: https://stackoverflow.com/a/1176023
    """
    return camel_case_pattern.sub("-", value).lower()
