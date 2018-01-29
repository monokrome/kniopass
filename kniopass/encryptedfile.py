import os
import logging

import cryptography.hazmat
import cryptography.hazmat.backends
import cryptography.hazmat.primitives.kdf.pbkdf2
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.padding

BACKEND = cryptography.hazmat.backends.default_backend()

LOG = logging.getLogger()

class EncryptedFile(object):
    DATA_MAGIC = b'kniopass'
    KEY_SALT = b'kniopass890123456'
    KEY_ITERATIONS = (1 << 19)
    ALGORITHMS = [
        (32, cryptography.hazmat.primitives.ciphers.algorithms.AES),
        (32, cryptography.hazmat.primitives.ciphers.algorithms.Camellia),
        (16, cryptography.hazmat.primitives.ciphers.algorithms.CAST5),
        (16, cryptography.hazmat.primitives.ciphers.algorithms.SEED),
    ]
    KEY_LENGTH = sum(l for l, a in ALGORITHMS)

    def __init__(self, filename, password):
        self.filename = filename
        self.key = self.compute_key(password)

    @classmethod
    def compute_key(cls, password):
        keygen = cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC(
            backend=BACKEND,
            algorithm=cryptography.hazmat.primitives.hashes.SHA256(),
            length=cls.KEY_LENGTH,
            salt=cls.KEY_SALT,
            iterations=cls.KEY_ITERATIONS
        )
        return keygen.derive(password.encode('utf-8'))

    @classmethod
    def decrypt_data(cls, key, data):
        key_offset = sum(i[0] for i in cls.ALGORITHMS)
        nonce = data[:cls.KEY_LENGTH]
        data = data[cls.KEY_LENGTH:]
        for key_size, alg in reversed(cls.ALGORITHMS):
            key_offset -= key_size
            k = key[key_offset : key_offset + key_size]
            a = alg(k)
            n = nonce[key_offset : key_offset + a.block_size // 8]
            p = cryptography.hazmat.primitives.padding.PKCS7(a.block_size).unpadder()
            cipher = cryptography.hazmat.primitives.ciphers.Cipher(
                a,
                cryptography.hazmat.primitives.ciphers.modes.CBC(n),
                backend=BACKEND
            )
            decryptor = cipher.decryptor()
            data = decryptor.update(data) + decryptor.finalize()
            data = p.update(data) + p.finalize()
        return data

    @classmethod
    def encrypt_data(cls, key, data):
        key_offset = 0
        nonce = os.urandom(cls.KEY_LENGTH)
        for key_size, alg in cls.ALGORITHMS:
            k = key[key_offset : key_offset + key_size]
            a = alg(k)
            n = nonce[key_offset : key_offset + a.block_size // 8]
            key_offset += key_size
            p = cryptography.hazmat.primitives.padding.PKCS7(a.block_size).padder()
            data = p.update(data) + p.finalize()
            cipher = cryptography.hazmat.primitives.ciphers.Cipher(
                a,
                cryptography.hazmat.primitives.ciphers.modes.CBC(n),
                backend=BACKEND
            )
            encryptor = cipher.encryptor()
            data = encryptor.update(data) + encryptor.finalize()
        return nonce + data

    def load_file(self):
        LOG.info('Loading %s', self.filename)
        data = open(self.filename, 'rb').read()
        data = self.decrypt_data(self.key, data)
        if not data[0:8] == self.DATA_MAGIC:
            raise Exception('Wrong password')
        data = data[8:].decode('utf-8')
        return data

    def save_file(self, data):
        data = self.DATA_MAGIC + data.encode('utf-8')
        data = self.encrypt_data(self.key, data)
        LOG.info('Saving to %s', self.filename)
        open(self.filename, 'wb').write(data)
