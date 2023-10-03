import hashlib
import re
import struct


id0_regex = re.compile(r'(?![0-9a-fA-F]{4}(01|00)[0-9a-fA-F]{18}00[0-9a-fA-F]{6})[0-9a-fA-F]{32}')
system_id_regex = re.compile(r'[a-fA-F0-9]{16}')

# splits version strings for comparison
version_split_regex = re.compile(r'[.+-]')


def is_job_key(value: str) -> bool:
    if is_id0(value):
        return True
    if is_system_id(value):
        return True
    if is_friend_code(value):
        return True
    return False

def is_id0(value: str) -> bool:
    return bool(id0_regex.fullmatch(value))

def is_system_id(value: str) -> bool:
    return bool(system_id_regex.fullmatch(value))

# Modified from verify_3ds_fc @ friendcode.py by nh-server
# https://github.com/nh-server/Kurisu/blob/main/cogs/friendcode.py#L28-L37
def is_friend_code(value: str) -> bool:
    try:
        fc = int(value)
    except ValueError:
        return False
    if fc > 0x7FFFFFFFFF:
        return False
    principal_id = fc & 0xFFFFFFFF
    checksum = (fc & 0xFF00000000) >> 32
    return hashlib.sha1(struct.pack('<L', principal_id)).digest()[0] >> 1 == checksum

def get_key_type(key: str) -> str:
    if is_friend_code(key):
        return 'fc-lfcs'
    elif is_system_id(key):
        return 'mii-lfcs'
    elif is_id0(key):
        return 'msed'


def validate_job_result(job_type: str, result: bytes, key=None, subkey=None) -> bool:
    if 'mii-lfcs' == job_type and subkey and result is None:
        return True
    elif job_type in ['mii-lfcs', 'fc-lfcs']:
        return validate_lfcs(result)
    elif 'msed' == job_type:
        return validate_movable(result, key)
    else:
        return False

# system id -> lfcs
def validate_lfcs(lfcs: bytes) -> bool:
    # shorter than 5 bytes
    if len(lfcs) < 5:
        return False
    # first 4 bytes are 0
    if b'\0\0\0\0' in lfcs[:4]:
        return False
    #if result[4:5] != b"\x00" && result[4:5] != b"\x02":
    #    return False
    return True

# lfcs -> msed
def validate_movable(msed: bytes, id0: str) -> bool:
    if len(msed) == 320:
        # full msed file
        return validate_keyy(msed[0x110:0x120], id0)
    elif len(msed) == 16:
        # keyy only
        return validate_keyy(msed, id0)
    else:
        return False

# Modified from id0convert.py by zoogie
# https://github.com/zoogie/seedminer_toolbox/blob/master/id0convert.py#L4-L8
def validate_keyy(keyy: bytes, id0: str) -> bool:
    keyy_sha256 = hashlib.sha256(keyy).digest()[:0x10]
    keyy_id0 = (keyy_sha256[3::-1] + keyy_sha256[7:3:-1] + keyy_sha256[11:7:-1] + keyy_sha256[15:11:-1]).hex()
    return keyy_id0 == id0


def enforce_client_version(client_types: dict, client_version_str: str, requested_types: set) -> set[str]:
    try:
        # reject if no version provided
        if not client_version_str:
            raise ValueError('Client version not provided')
        client_type, client_version = parse_typed_version_string(client_version_str)
        # reject unrecognized clients
        if client_type not in client_types.keys():
            raise ValueError('Unrecognized client type')
        # reject outdated clients
        latest_version_str = client_types[client_type]['version']
        latest_version = parse_version_string(latest_version_str)
        if compare_versions(client_version, latest_version) < 0:
            raise ValueError(f'Outdated client version, {client_version_str} < {client_type}-{latest_version_str}')
        # reject illegal job type requests
        allowed_types = client_types[client_type]['allowed']
        if requested_types and bool(requested_types - allowed_types):
            raise ValueError(f'Requested illegal job type for {client_type} clients')
        return allowed_types
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError('Error validating client version') from e

# Modified from https://stackoverflow.com/a/28568003
def parse_typed_version_string(version: str, point_max_len=10) -> tuple[str, list]:
    split = version_split_regex.split(version)
    return split[0], [p.zfill(point_max_len) for p in split[1:]]

# Modified from https://stackoverflow.com/a/28568003
def parse_version_string(version: str, point_max_len=10) -> list:
    return [p.zfill(point_max_len) for p in version_split_regex.split(version)]

def compare_versions(version_a: list, version_b: list) -> int:
    if len(version_a) != len(version_b):
        raise ValueError('Version lengths do not match')
    return compare(version_a, version_b)

# removed in Python 3 lol
def compare(a, b) -> int:
    return (a > b) - (a < b)
