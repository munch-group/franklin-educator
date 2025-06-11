
# python encrypt_module.py password.py mysecretpassword

import sys
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

_, input_file, password = sys.argv
output_file = Path(input_file).with_suffix('.enc')
assert len(password) == 16, "Password must be exactly 16 bytes long."

sixteen_byte_key = password.encode('utf-8')  # Ensure key is 16 bytes long

cipher = AES.new(sixteen_byte_key, AES.MODE_CBC)
with open(input_file, 'rb') as f:
    plaintext = f.read()

ciphertext = cipher.iv + cipher.encrypt(pad(plaintext, AES.block_size))
with open(output_file, 'wb') as f:
    f.write(ciphertext)



############




