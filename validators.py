import hashlib
import re
import struct


id0_regex = re.compile(r'(?![0-9a-fA-F]{4}(01|00)[0-9a-fA-F]{18}00[0-9a-fA-F]{6})[0-9a-fA-F]{32}')
system_id_regex = re.compile(r'[a-fA-F0-9]{16}')


def is_job_key(value):
    if is_id0(value):
        return True
    if is_system_id(value):
        return True
    if is_friend_code(value):
        return True
    return False

def is_id0(value):
    return bool(id0_regex.fullmatch(value))

def is_system_id(value):
    return bool(system_id_regex.fullmatch(value))

# Modified from https://github.com/nh-server/Kurisu/blob/main/cogs/friendcode.py#L28
def is_friend_code(value):
    try:
        fc = int(value)
    except ValueError:
        return False
    if fc > 0x7FFFFFFFFF:
        return False
    principal_id = fc & 0xFFFFFFFF
    checksum = (fc & 0xFF00000000) >> 32
    return hashlib.sha1(struct.pack('<L', principal_id)).digest()[0] >> 1 == checksum