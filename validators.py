import hashlib
import re
import struct


id0_regex = re.compile(r'(?![0-9a-fA-F]{4}(01|00)[0-9a-fA-F]{18}00[0-9a-fA-F]{6})[0-9a-fA-F]{32}')
system_id_regex = re.compile(r'[a-fA-F0-9]{16}')


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

# Modified from https://github.com/nh-server/Kurisu/blob/main/cogs/friendcode.py#L28
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


def validate_job_result(job_type: str, result: bytes, key=None) -> bool:
    if job_type in ['mii', 'fc']:
        return validate_lfcs(result)
    elif 'part1' == job_type:
        return validate_movable(result, key)
    else:
        return False

# system id -> lfcs
def validate_lfcs(lfcs: bytes) -> bool:
    # shorter than 5 bytes
    if len(lfcs) < 5:
        return False
    # first 4 bytes are 0
    if b"\0\0\0\0" in lfcs[:4]:
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

# Modified from https://github.com/zoogie/seedminer_toolbox/blob/master/id0convert.py#L4-L8
def validate_keyy(keyy: bytes, id0: str) -> bool:
    keyy_sha256 = hashlib.sha256(keyy).digest()[:0x10]
    keyy_id0 = (keyy_sha256[3::-1] + keyy_sha256[7:3:-1] + keyy_sha256[11:7:-1] + keyy_sha256[15:11:-1]).hex()
    return keyy_id0 == id0
