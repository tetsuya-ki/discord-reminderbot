# https://pycryptodome.readthedocs.io/en/latest/src/examples.html
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from os.path import join, dirname
import hashlib, os

class Aes_angou:
    ENC_FILE = 'encrypted.bin'
    DEC_FILE = 'reminder.db'

    ENC_FILE_PATH = join(dirname(__file__), 'files' + os.sep + ENC_FILE)
    DEC_FILE_PATH = join(dirname(__file__), 'files' + os.sep + DEC_FILE)

    def __init__(self, password:str=''):
        self.password = password

    def encode(self):
        with open(self.DEC_FILE_PATH, mode='rb') as file:
            data = file.read()

        secret_key = hashlib.sha256(self.password.encode("utf8")).digest()
        cipher = AES.new(secret_key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(data)

        with  open(self.ENC_FILE_PATH, 'wb') as file_out:
            [ file_out.write(x) for x in (cipher.nonce, tag, ciphertext) ]

    def decode(self):
        secret_key = hashlib.sha256(self.password.encode("utf8")).digest()
        with open(self.ENC_FILE_PATH, 'rb') as file_in:
            nonce, tag, ciphertext = [ file_in.read(x) for x in (16, 16, -1) ]
            cipher = AES.new(secret_key, AES.MODE_EAX, nonce)
            data = cipher.decrypt_and_verify(ciphertext, tag)

            with  open(self.DEC_FILE_PATH, 'wb') as dec_file: 
                dec_file.write(data)
