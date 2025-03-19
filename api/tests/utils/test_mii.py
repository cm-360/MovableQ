import os
from binascii import unhexlify

from pytest import fixture

from app.utils.mii import decrypt_mii_qr_data
from app.utils.mii import get_system_id
from app.utils.mii import read_mii_qr

test_system_id = "10a76a225904ff99"


@fixture
def nk31() -> bytes:
    nk31_hex = os.getenv("SLOT_31_KEY_N")

    if not nk31_hex:
        raise RuntimeError("slot0x31KeyN not provided")

    return unhexlify(nk31_hex)


@fixture
def mii_qr(datadir) -> bytes:
    with open(f"{datadir}/mii_qr.jpg", "rb") as mii_qr_file:
        return mii_qr_file.read()


@fixture
def mii_qr_data_dec(datadir) -> bytes:
    with open(f"{datadir}/mii_data_decrypted.bin", "rb") as mii_data_file:
        return mii_data_file.read()


def test_read_mii_qr(mii_qr: bytes):
    mii_qr_data_enc = read_mii_qr(mii_qr)

    assert mii_qr_data_enc is not None
    assert 0x70 == len(mii_qr_data_enc)


def test_decrypt_mii_qr_data(mii_qr: bytes, nk31: bytes):
    mii_qr_data_enc = read_mii_qr(mii_qr)
    mii_qr_data_dec = decrypt_mii_qr_data(mii_qr_data_enc, nk31)

    assert mii_qr_data_dec is not None
    assert 0x58 == len(mii_qr_data_dec)


def test_get_system_id(mii_qr_data_dec: bytes):
    system_id = get_system_id(mii_qr_data_dec)

    assert system_id == test_system_id
