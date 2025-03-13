import re

# splits version strings for comparison
version_split_regex = re.compile(r"[.+-]")


def enforce_client_version(
    client_types: dict, client_version_str: str, requested_types: set
) -> set[str]:
    try:
        # reject if no version provided
        if not client_version_str:
            raise ValueError("Client version not provided")
        client_type, client_version = parse_typed_version_string(client_version_str)
        # reject unrecognized clients
        if client_type not in client_types.keys():
            raise ValueError("Unrecognized client type")
        # reject outdated clients
        latest_version_str = client_types[client_type]["version"]
        latest_version = parse_version_string(latest_version_str)
        if compare_versions(client_version, latest_version) < 0:
            raise ValueError(
                f"Outdated client version, {client_version_str} < {client_type}-{latest_version_str}"
            )
        # reject illegal job type requests
        allowed_types = client_types[client_type]["allowed"]
        if requested_types and bool(requested_types - allowed_types):
            raise ValueError(f"Requested illegal job type for {client_type} clients")
        return allowed_types
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError("Error validating client version") from e


# Modified from https://stackoverflow.com/a/28568003
def parse_typed_version_string(version: str, point_max_len=10) -> tuple[str, list]:
    split = version_split_regex.split(version)
    return split[0], [p.zfill(point_max_len) for p in split[1:]]


# Modified from https://stackoverflow.com/a/28568003
def parse_version_string(version: str, point_max_len=10) -> list:
    return [p.zfill(point_max_len) for p in version_split_regex.split(version)]


def compare_versions(version_a: list, version_b: list) -> int:
    if len(version_a) != len(version_b):
        raise ValueError("Version lengths do not match")
    return compare(version_a, version_b)


# removed in Python 3 lol
def compare(a, b) -> int:
    return (a > b) - (a < b)
