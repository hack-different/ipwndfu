import subprocess
import sys
import typing
from collections import namedtuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


Patch = namedtuple("Patch", "offset data")


def apply_patches(binary: bytes, patches: typing.List[Patch]):
    for (offset, data) in patches:
        binary = binary[:offset] + data + binary[offset + len(data):]
    return binary


def aes_decrypt(data: bytes, iv: bytes, key: bytes) -> bytes:
    if len(key) == 32:
        aes = 128
    elif len(key) == 64:
        aes = 256
    else:
        raise AssertionError('ERROR: Bad AES key given to aes_decrypt. Exiting.')

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decrypter = cipher.decryptor()
    return decrypter.update(data) + decrypter.finalize()



def hex_dump(data, address):
    p = subprocess.Popen(['xxd',
                          '-o',
                          str(address)],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate(input=data)

    if p.returncode != 0 or len(stderr) > 0:
        print('ERROR: xxd failed: %s' % stderr)
        sys.exit(1)

    return stdout
