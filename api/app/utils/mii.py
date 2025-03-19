import io
from binascii import hexlify

# QR decoding
from PIL import Image
from pyzbar.pyzbar import decode as qr_decode

# AES decryption
try:
    # pycryptodomex
    from Cryptodome.Cipher import AES
except ImportError:
    # pycryptodome
    from Crypto.Cipher import AES


def read_mii_qr(mii_qr: bytes) -> bytes | None:
    """Extracts the encrypted Mii data from a QR code exported from Mii Maker.

    Args:
        mii_qr (bytes): The binary data representing the Mii QR code image.

    Returns:
        bytes | None: The encrypted Mii QR data if decoding is successful;
        otherwise, returns None.
    """
    decoded = qr_decode(Image.open(io.BytesIO(mii_qr)), binary=True)

    if not decoded:
        return

    return decoded[0].data


def decrypt_mii_qr_data(encrypted: bytes, nk31: bytes) -> bytes:
    """Decrypts the data extracted from Mii QR data using the `slot0x31KeyN`.

    Args:
        encrypted (bytes): The encrypted Mii QR data. Must be 0x70 bytes.
        nk31 (bytes): The AES `slot0x31KeyN` required for decryption.

    Returns:
        bytes: The decrypted portion of the Mii QR data.

    Raises:
        ValueError: If the encrypted data has an incorrect length.
        ValueError: If the `slot0x31KeyN` (nk31) is not provided.

    Note:
        - The decryption logic is based on
            https://github.com/zoogie/seedminer/blob/5ceb4cf58f5e429781aecfc6b46a0d59311c0bac/seedminer/seedminer_launcher3.py#L126-L130.
        - For additional details on the Mii QR code format, refer to
            https://www.3dbrew.org/wiki/Mii_Maker#Mii_QR_Code_format.
        - For instructions on obtaining `slot0x31KeyN`, refer to
            https://3ds.goombi.fr/convertMii/0x31.html and
            https://github.com/PabloMK7/citra/tree/master/dist/dumpkeys.
    """
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
    """Extracts the 8-byte system ID from decrypted Mii QR data.

    Args:
        mii_qr_data (bytes): The decrypted Mii QR data.

    Returns:
        str: The system ID extracted from the Mii QR data, represented as
        a hexadecimal string.

    Note:
        For additional details on the Mii QR code format, refer to
        https://www.3dbrew.org/wiki/Mii_Maker#Mii_QR_Code_format.
    """
    return hexlify(mii_qr_data[4:12]).decode("ascii")
