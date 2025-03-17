import hashlib
import re
import struct


id0_pattern = re.compile(
    r"(?![0-9a-fA-F]{4}(01|00)[0-9a-fA-F]{18}00[0-9a-fA-F]{6})[0-9a-fA-F]{32}"
)

system_id_pattern = re.compile(r"[0-9a-fA-F]{16}")


def is_valid_id0(value: str) -> bool:
    return bool(id0_pattern.fullmatch(value))


def is_valid_system_id(value: str) -> bool:
    value = value.split("-")[0]
    return bool(system_id_pattern.fullmatch(value))


def is_valid_friend_code(friend_code: str) -> bool:
    """Determines if the provided friend code is valid.

    The validation process is as follows:
    1. Remove all dashes from the friend code and convert it to an integer.
    2. Assert that it is less than 0x7FFFFFFFFF, higher values are invalid.
    3. Obtain the principal ID using the lower 32 bits.
    4. Compute the SHA-1 hash of the principal ID.
    5. Use the first byte of the hash, shifted right by one, as the checksum.
    6. Compare this value to the upper 32 bits of the friend code (1 byte),
        the expected checksum.

    Args:
        friend_code (str): The 12-digit friend code to check.

    Returns:
        bool: True if the friend code is valid, False otherwise.

    Note:
        - The checksum calculation is based on
            https://github.com/nh-server/Kurisu/blob/eac33dbd17918e28e73e662c20182df6df71febd/cogs/friendcode.py#L28-L37.
        - For more information on friend code validation, refer to
            https://3dbrew.org/wiki/FRDU:IsValidFriendCode,
            https://3dbrew.org/wiki/FRDU:PrincipalIdToFriendCode, and
            https://www.reddit.com/r/3dshacks/comments/5h6zpo/comment/day1bk3.
    """
    try:
        friend_code_int = int(friend_code.replace("-", ""))
    except ValueError:
        return False

    if friend_code_int > 0x7FFFFFFFFF:
        return False

    principal_id = friend_code_int & 0xFFFFFFFF
    principal_id_bytes = struct.pack("<L", principal_id)
    principal_id_hash = hashlib.sha1(principal_id_bytes).digest()

    checksum = principal_id_hash[0] >> 1
    expected_checksum = (friend_code_int & 0xFF00000000) >> 32

    return checksum == expected_checksum


# Used during system id -> lfcs jobs
def is_valid_lfcs(lfcs: bytes) -> bool:
    """Determines if the provided LocalFriendCodeSeed is valid.

    A LFCS is only considered valid if it meets the following requirements:
    - It contains at least the five required bytes.
    - The first four bytes are not all null.
    - The fifth byte's bitflag corresponds to either a new/old 3DS origin.

    This is used to validate the results of LFCS jobs.

    Args:
        lfcs (bytes): The LocalFriendCodeSeed to verify, as a byte sequence.

    Returns:
        bool: True if valid, False otherwise.
    """
    # Shorter than 5 bytes
    if len(lfcs) < 5:
        return False

    # First 4 bytes are 0
    if b"\0\0\0\0" in lfcs[:4]:
        return False

    # Invalid bit flag
    if lfcs[4:5] != b"\x00" and lfcs[4:5] != b"\x02":
        return False

    return True


def validate_movable(msed: bytes, expected_id0: str) -> bool:
    """Validates whether the provided `movable.sed`'s KeyY matches an ID0.

    Either a full `movable.sed` file (320 bytes) or a KeyY by itself (16 bytes)
    can be provided. This is used to validate the results of msed jobs.

    Args:
        keyy (bytes): The `movable.sed` file to validate as a byte sequence.
        expected_id0 (str): The expected ID0 value as a hexadecimal string.

    Returns:
        bool: True if the `movable.sed`'s KeyY and ID0 match, otherwise False.

    Raises:
        ValueError: If the `movable.sed` data is of an unrecognized length.
    """
    if 320 == len(msed):
        # Full msed file
        keyy = msed[0x110:0x120]
    elif 16 == len(msed):
        # KeyY only
        keyy = msed
    else:
        raise ValueError("Invalid msed data length")

    return validate_keyy(keyy, expected_id0)


def validate_keyy(keyy: bytes, expected_id0: str) -> bool:
    """Validates whether the provided KeyY matches the specified ID0.

    This calculates the SHA-256 hash of the provided KeyY and compares it to
    the provided ID0 to determine if they match. The ID0 is the first half of
    the KeyY's SHA-256 hash.

    Args:
        keyy (bytes): The KeyY to validate as a byte sequence.
        expected_id0 (str): The expected ID0 value as a hexadecimal string.

    Returns:
        bool: True if the provided KeyY and ID0 match, otherwise False.

    Note:
        - The ID0 calculation is based on
            https://github.com/zoogie/seedminer_toolbox/blob/936b10c08a85aec7634436def613beadbdb32486/id0convert.py.
        - For more information about KeyY and the `movable.sed` file, refer to
            https://wiki.hacks.guide/wiki/3DS:System_files,
            https://zoogie.github.io/web/34%E2%85%95c3, and
            https://www.3dbrew.org/wiki/Nand/private/movable.sed.
    """
    keyy_sha256 = hashlib.sha256(keyy).digest()[:0x10]

    # Reverses each 4-byte block in the KeyY's SHA-256 hash
    keyy_id0 = (
        keyy_sha256[3::-1]
        + keyy_sha256[7:3:-1]
        + keyy_sha256[11:7:-1]
        + keyy_sha256[15:11:-1]
    ).hex()

    return keyy_id0 == expected_id0
