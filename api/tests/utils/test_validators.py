from app.utils.validators import is_valid_friend_code
from app.utils.validators import is_valid_id0
from app.utils.validators import is_valid_lfcs
from app.utils.validators import is_valid_system_id
from app.utils.validators import validate_keyy
from app.utils.validators import validate_movable

test_id0 = "969dbbb25e8f636c391ed29432e2af53"
fake_id0 = "fef0fef0fef0fef0fef0fef0fef0fef0"
zero_id0 = "00000000000000000000000000000000"

test_system_id = "10a76a225904ff99"

test_friend_code = "044770074962"
fake_friend_code = "123456789012"

zero_keyy = b"\x00" * 16


def test_is_valid_id0():
    assert is_valid_id0(test_id0)

    assert not is_valid_id0(zero_id0)


def test_is_valid_system_id():
    assert is_valid_system_id(test_system_id)


def test_is_valid_friend_code():
    assert is_valid_friend_code(test_friend_code)

    assert not is_valid_friend_code(fake_friend_code)


def test_is_valid_lfcs(datadir):
    with open(f"{datadir}/{test_friend_code}.lfcs.bin", "rb") as lfcs_file:
        lfcs = lfcs_file.read()
        assert is_valid_lfcs(lfcs)


def test_validate_movable(datadir):
    with open(f"{datadir}/{test_id0}.keyy.bin", "rb") as keyy_file:
        keyy = keyy_file.read()
        assert validate_movable(keyy, test_id0)


def test_validate_keyy(datadir):
    with open(f"{datadir}/{test_id0}.keyy.bin", "rb") as keyy_file:
        keyy = keyy_file.read()
        assert validate_keyy(keyy, test_id0)

        # Incorrect ID0
        assert not validate_keyy(keyy, fake_id0)

    # Incorrect KeyY
    assert not validate_keyy(zero_keyy, test_id0)
