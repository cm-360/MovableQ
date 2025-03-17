import io
from binascii import hexlify

# QR decoding
from pyzbar.pyzbar import decode as qr_decode
from PIL import Image

# AES decryption
try:
    # pycryptodomex
    from Cryptodome.Cipher import AES
except ImportError:
    # pycryptodome
    from Crypto.Cipher import AES


# Returns encrypted Mii data
def read_mii_qr(mii_qr: bytes) -> bytes | None:
    decoded = qr_decode(Image.open(io.BytesIO(mii_qr)), binary=True)

    if not decoded:
        return

    return decoded[0].data


# Modified from seedminer_launcher3.py by zoogie
# https://github.com/zoogie/seedminer/blob/master/seedminer/seedminer_launcher3.py#L126-L130
def decrypt_mii_qr_data(encrypted: bytes, nk31: bytes) -> bytes:
    if 0x70 != len(encrypted):
        raise ValueError("Incorrect Mii QR data length")
    if not nk31:
        raise ValueError("slot0x31KeyN not provided")

    nonce = encrypted[:0x8] + (b"\x00" * 4)
    cipher = AES.new(nk31, AES.MODE_CCM, nonce)
    decrypted = cipher.decrypt(encrypted[0x8:0x60])

    # TODO verify checksum?

    return decrypted


def get_system_id(mii_qr_data: bytes) -> str:
    return hexlify(mii_qr_data[4:12]).decode("ascii")
