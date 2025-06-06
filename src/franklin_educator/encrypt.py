import base64
import os
import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

def derive_key(password: str, salt: bytes, iterations: int = 100_000) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_token(api_token: str, password: str) -> bytes:
    salt = os.urandom(16)
    key = derive_key(password, salt)
    f = Fernet(key)
    token_encrypted = f.encrypt(api_token.encode())
    return salt + token_encrypted  # store salt + ciphertext

def decrypt_token(token_encrypted_with_salt: bytes, password: str) -> str:
    salt = token_encrypted_with_salt[:16]
    ciphertext = token_encrypted_with_salt[16:]
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.decrypt(ciphertext).decode()

# --- Encrypt once and store ---
def store_encrypted_token(token_path: str, api_token: str, admin_password: str):
    # api_token = getpass.getpass("Enter GitLab API token: ")
    # admin_password = getpass.getpass("Enter admin password to encrypt: ")
    encrypted = encrypt_token(api_token, admin_password)
    with open(token_path, "wb") as f:
        f.write(encrypted)
    print("Token encrypted and stored.")
