# # import os
# # import json
# # from base64 import b64encode, b64decode
# # from typing import Dict
# # from Crypto.Cipher import AES
# # from Crypto.Protocol.KDF import PBKDF2
# # from Crypto.Hash import HMAC, SHA256
# # from Crypto.Random import get_random_bytes
# # from Crypto.Util.Padding import pad, unpad

# # # Constants
# # KEY_LEN = 32
# # IV_LEN = 16
# # SALT_LEN = 16
# # PBKDF2_ITERATIONS = 100_000
# # HASH_ITERATIONS = 100_000

# # # === Key Derivation and Hashing ===
# # def derive_key(password: str, salt: bytes) -> bytes:
# #     return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=PBKDF2_ITERATIONS, hmac_hash_module=SHA256)

# # def hash_password(password: str, salt: bytes) -> bytes:
# #     return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=HASH_ITERATIONS)

# # # === Auth-Only User Management ===
# # def create_user(username: str, password: str, authfile: str, role: str = "user"):
# #     salt = get_random_bytes(SALT_LEN)
# #     pw_hash = hash_password(password, salt)
# #     try:
# #         with open(authfile, "r") as f:
# #             db = json.load(f)
# #     except FileNotFoundError:
# #         db = {}
# #     db[username] = {
# #         "salt": b64encode(salt).decode(),
# #         "password_hash": b64encode(pw_hash).decode(),
# #         "role": role
# #     }
# #     with open(authfile, "w") as f:
# #         json.dump(db, f)

# # def get_user_role(username: str, authfile: str) -> str:
# #     with open(authfile, "r") as f:
# #         db = json.load(f)
# #     if username not in db:
# #         raise ValueError("User not found")
# #     return db[username].get("role", "user")

# # def change_user_auth_password(username: str, old_password: str, new_password: str, authfile: str):
# #     with open(authfile, "r") as f:
# #         db = json.load(f)
# #     if username not in db:
# #         raise ValueError("User not found")
# #     entry = db[username]
# #     salt = b64decode(entry["salt"])
# #     stored_hash = b64decode(entry["password_hash"])
# #     if hash_password(old_password, salt) != stored_hash:
# #         raise ValueError("Incorrect old password")
# #     new_salt = get_random_bytes(SALT_LEN)
# #     new_hash = hash_password(new_password, new_salt)
# #     db[username] = {
# #         "salt": b64encode(new_salt).decode(),
# #         "password_hash": b64encode(new_hash).decode()
# #     }
# #     with open(authfile, "w") as f:
# #         json.dump(db, f)

# # def admin_reset_user_password(username: str, new_password: str, authfile: str):
# #     with open(authfile, "r") as f:
# #         db = json.load(f)
# #     if username not in db:
# #         raise ValueError("User not found")
# #     new_salt = get_random_bytes(SALT_LEN)
# #     new_hash = hash_password(new_password, new_salt)
# #     db[username] = {
# #         "salt": b64encode(new_salt).decode(),
# #         "password_hash": b64encode(new_hash).decode()
# #     }
# #     with open(authfile, "w") as f:
# #         json.dump(db, f)

# # # === Shared Secret Encryption ===
# # def encrypt_for_admins(password: str, admin_passwords: Dict[str, str], outfile: str):
# #     iv = get_random_bytes(IV_LEN)
# #     dek = get_random_bytes(KEY_LEN)
# #     cipher = AES.new(dek, AES.MODE_CBC, iv)
# #     ciphertext = cipher.encrypt(pad(password.encode(), AES.block_size))
# #     wrapped_keys = {}
# #     for admin, admin_pw in admin_passwords.items():
# #         salt = get_random_bytes(SALT_LEN)
# #         admin_key = derive_key(admin_pw, salt)
# #         wrapper_iv = get_random_bytes(IV_LEN)
# #         wrapper = AES.new(admin_key, AES.MODE_CBC, wrapper_iv)
# #         encrypted_dek = wrapper.encrypt(pad(dek, AES.block_size))
# #         wrapped_keys[admin] = {
# #             "salt": b64encode(salt).decode(),
# #             "iv": b64encode(wrapper_iv).decode(),
# #             "wrapped_dek": b64encode(encrypted_dek).decode()
# #         }
# #     output = {
# #         "ciphertext": b64encode(ciphertext).decode(),
# #         "iv": b64encode(iv).decode(),
# #         "wrapped_keys": wrapped_keys
# #     }
# #     with open(outfile, "w") as f:
# #         json.dump(output, f)

# # def decrypt_with_admin(admin: str, admin_pw: str, infile: str) -> str:
# #     with open(infile, "r") as f:
# #         blob = json.load(f)
# #     ciphertext = b64decode(blob["ciphertext"])
# #     iv = b64decode(blob["iv"])
# #     wrapped = blob["wrapped_keys"][admin]
# #     salt = b64decode(wrapped["salt"])
# #     wrapper_iv = b64decode(wrapped["iv"])
# #     encrypted_dek = b64decode(wrapped["wrapped_dek"])
# #     admin_key = derive_key(admin_pw, salt)
# #     wrapper = AES.new(admin_key, AES.MODE_CBC, wrapper_iv)
# #     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
# #     cipher = AES.new(dek, AES.MODE_CBC, iv)
# #     plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
# #     return plaintext.decode()

# # def change_admin_password(admin_name: str, old_password: str, new_password: str, infile: str):
# #     with open(infile, "r") as f:
# #         blob = json.load(f)
# #     entry = blob["wrapped_keys"][admin_name]
# #     salt = b64decode(entry["salt"])
# #     iv = b64decode(entry["iv"])
# #     wrapped_dek = b64decode(entry["wrapped_dek"])
# #     old_key = derive_key(old_password, salt)
# #     cipher = AES.new(old_key, AES.MODE_CBC, iv)
# #     dek = unpad(cipher.decrypt(wrapped_dek), AES.block_size)
# #     new_salt = get_random_bytes(SALT_LEN)
# #     new_iv = get_random_bytes(IV_LEN)
# #     new_key = derive_key(new_password, new_salt)
# #     new_cipher = AES.new(new_key, AES.MODE_CBC, new_iv)
# #     new_wrapped_dek = new_cipher.encrypt(pad(dek, AES.block_size))
# #     blob["wrapped_keys"][admin_name] = {
# #         "salt": b64encode(new_salt).decode(),
# #         "iv": b64encode(new_iv).decode(),
# #         "wrapped_dek": b64encode(new_wrapped_dek).decode()
# #     }
# #     with open(infile, "w") as f:
# #         json.dump(blob, f)

# # def add_admin(admin_name: str, admin_password: str, infile: str, existing_admin: str, existing_admin_pw: str):
# #     with open(infile, "r") as f:
# #         blob = json.load(f)
# #     existing = blob["wrapped_keys"][existing_admin]
# #     salt = b64decode(existing["salt"])
# #     wrapper_iv = b64decode(existing["iv"])
# #     encrypted_dek = b64decode(existing["wrapped_dek"])
# #     admin_key = derive_key(existing_admin_pw, salt)
# #     wrapper = AES.new(admin_key, AES.MODE_CBC, wrapper_iv)
# #     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
# #     new_salt = get_random_bytes(SALT_LEN)
# #     new_iv = get_random_bytes(IV_LEN)
# #     new_key = derive_key(admin_password, new_salt)
# #     new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
# #     new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
# #     blob["wrapped_keys"][admin_name] = {
# #         "salt": b64encode(new_salt).decode(),
# #         "iv": b64encode(new_iv).decode(),
# #         "wrapped_dek": b64encode(new_wrapped_dek).decode()
# #     }
# #     with open(infile, "w") as f:
# #         json.dump(blob, f)

# # def remove_admin(admin_name: str, infile: str):
# #     with open(infile, "r") as f:
# #         blob = json.load(f)
# #     if admin_name in blob["wrapped_keys"]:
# #         del blob["wrapped_keys"][admin_name]
# #     with open(infile, "w") as f:
# #         json.dump(blob, f)

# # def admin_reset_wrapped_password(target_user: str, new_password: str, infile: str, admin: str, admin_pw: str):
# #     with open(infile, "r") as f:
# #         blob = json.load(f)
# #     if target_user not in blob["wrapped_keys"]:
# #         raise ValueError(f"User '{target_user}' not found")
# #     wrapped = blob["wrapped_keys"][admin]
# #     salt = b64decode(wrapped["salt"])
# #     wrapper_iv = b64decode(wrapped["iv"])
# #     encrypted_dek = b64decode(wrapped["wrapped_dek"])
# #     admin_key = derive_key(admin_pw, salt)
# #     wrapper = AES.new(admin_key, AES.MODE_CBC, wrapper_iv)
# #     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
# #     new_salt = get_random_bytes(SALT_LEN)
# #     new_iv = get_random_bytes(IV_LEN)
# #     new_key = derive_key(new_password, new_salt)
# #     new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
# #     new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
# #     blob["wrapped_keys"][target_user] = {
# #         "salt": b64encode(new_salt).decode(),
# #         "iv": b64encode(new_iv).decode(),
# #         "wrapped_dek": b64encode(new_wrapped_dek).decode()
# #     }
# #     with open(infile, "w") as f:
# #         json.dump(blob, f)


# # # === Example Workflow ===
# # if __name__ == "__main__":
# #     # Create authentication-only users
# #     create_user("carol", "carol_password", "auth_db.json")
# #     create_user("dave", "dave_password", "auth_db.json")

# #     # Create users with roles
# #     create_user("alice", "alice_pw", "auth_db.json", role="admin")
# #     create_user("bob", "bob_pw", "auth_db.json", role="admin")

# #     # Change Carol's password
# #     change_user_auth_password("carol", "carol_password", "new_carol_pw", "auth_db.json")

# #     # Admin resets Dave's password
# #     admin_reset_user_password("dave", "reset_dave_pw", "auth_db.json")

# #     # Encrypt a shared secret for Alice and Bob
# #     encrypt_for_admins("TopSecret!", {"alice": "alice_pw", "bob": "bob_pw"}, "secret.json")

# #     # Decrypt the secret as Alice
# #     print(decrypt_with_admin("alice", "alice_pw", "secret.json"))

# #     # Change Alice's password
# #     change_admin_password("alice", "alice_pw", "new_alice_pw", "secret.json")
# #     print(decrypt_with_admin("alice", "new_alice_pw", "secret.json"))

# #     # Add Charlie as a new admin
# #     add_admin("charlie", "charlie_pw", "secret.json", "bob", "bob_pw")
# #     print(decrypt_with_admin("charlie", "charlie_pw", "secret.json"))

# #     # Admin resets Charlie's password
# #     admin_reset_wrapped_password("charlie", "reset_charlie_pw", "secret.json", "alice", "new_alice_pw")
# #     print(decrypt_with_admin("charlie", "reset_charlie_pw", "secret.json"))

# #     # Remove Bob
# #     remove_admin("bob", "secret.json")

# #     # Print user roles
# #     print(get_user_role("alice", "auth_db.json"))
# #     print(get_user_role("carol", "auth_db.json"))



# # """
# # FRANKLIN ADMIN TOKEN SET <TOKEN>
# # initialize the auth db with the admin users 
# # encrypt_for_admins(ADMIN_API_TOKEN, {"kasper": "banana"}, "secret.json")

# # FRNAKLIN GRANT TA <USER>
# # add a user to a course with the appropriate role:
# # franklin grant etc..

# # FRANKLIN ADMIN ADD <USER>
# # create a franklin user/passwords set for the user: create_user
# # create an api token for the user: create_impersonation_token
# # encrypt the token as secrete shared with admins: encrypt_for_admins


# # store the token as a secret shared by the user and admins
# # encrypt_for_admins




# # user can use api through franklin by authenticating to descrypt stored api token.



# #  """




# import os
# import json
# from base64 import b64encode, b64decode
# from typing import Dict
# from Crypto.Cipher import AES
# from Crypto.Protocol.KDF import PBKDF2
# from Crypto.Hash import HMAC, SHA256
# from Crypto.Random import get_random_bytes
# from Crypto.Util.Padding import pad, unpad

# # Constants
# KEY_LEN = 32
# IV_LEN = 16
# SALT_LEN = 16
# PBKDF2_ITERATIONS = 100_000
# HASH_ITERATIONS = 100_000

# # === Key Derivation and Hashing ===
# def derive_key(password: str, salt: bytes) -> bytes:
#     return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=PBKDF2_ITERATIONS, hmac_hash_module=SHA256)

# def hash_password(password: str, salt: bytes) -> bytes:
#     return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=HASH_ITERATIONS)

# # === Auth-Only User Management ===
# def create_user(username: str, password: str, authfile: str, role: str = "user"):
#     salt = get_random_bytes(SALT_LEN)
#     pw_hash = hash_password(password, salt)
#     try:
#         with open(authfile, "r") as f:
#             db = json.load(f)
#     except FileNotFoundError:
#         db = {}
#     db[username] = {
#         "salt": b64encode(salt).decode(),
#         "password_hash": b64encode(pw_hash).decode(),
#         "role": role
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)

# def get_user_role(username: str, authfile: str) -> str:
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     return db[username].get("role", "user")

# def change_user_auth_password(username: str, old_password: str, new_password: str, authfile: str):
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     entry = db[username]
#     salt = b64decode(entry["salt"])
#     stored_hash = b64decode(entry["password_hash"])
#     if hash_password(old_password, salt) != stored_hash:
#         raise ValueError("Incorrect old password")
#     new_salt = get_random_bytes(SALT_LEN)
#     new_hash = hash_password(new_password, new_salt)
#     db[username] = {
#         "salt": b64encode(new_salt).decode(),
#         "password_hash": b64encode(new_hash).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)

# def admin_reset_user_password(username: str, new_password: str, authfile: str):
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     entry = db[username]
#     new_salt = get_random_bytes(SALT_LEN)
#     new_hash = hash_password(new_password, new_salt)
#     db[username] = {
#         "salt": b64encode(new_salt).decode(),
#         "password_hash": b64encode(new_hash).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)

# # === Shared Secret Encryption ===
# def encrypt_for_users(secret: str, user_passwords: Dict[str, str], authfile: str, outfile: str):
#     iv = get_random_bytes(IV_LEN)
#     dek = get_random_bytes(KEY_LEN)
#     cipher = AES.new(dek, AES.MODE_CBC, iv)
#     ciphertext = cipher.encrypt(pad(secret.encode(), AES.block_size))
#     wrapped_keys = {}
#     with open(authfile, "r") as f:
#         auth_db = json.load(f)
#     for user, user_pw in user_passwords.items():
#         salt = get_random_bytes(SALT_LEN)
#         user_key = derive_key(user_pw, salt)
#         wrapper_iv = get_random_bytes(IV_LEN)
#         wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
#         encrypted_dek = wrapper.encrypt(pad(dek, AES.block_size))
#         role = auth_db[user].get("role", "user")
#         wrapped_keys[user] = {
#             "salt": b64encode(salt).decode(),
#             "iv": b64encode(wrapper_iv).decode(),
#             "wrapped_dek": b64encode(encrypted_dek).decode(),
#             "role": role
#         }
#     output = {
#         "ciphertext": b64encode(ciphertext).decode(),
#         "iv": b64encode(iv).decode(),
#         "wrapped_keys": wrapped_keys
#     }
#     with open(outfile, "w") as f:
#         json.dump(output, f)

# def decrypt_with_user(user: str, user_pw: str, infile: str) -> str:
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     ciphertext = b64decode(blob["ciphertext"])
#     iv = b64decode(blob["iv"])
#     wrapped = blob["wrapped_keys"][user]
#     salt = b64decode(wrapped["salt"])
#     wrapper_iv = b64decode(wrapped["iv"])
#     encrypted_dek = b64decode(wrapped["wrapped_dek"])
#     user_key = derive_key(user_pw, salt)
#     wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
#     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
#     cipher = AES.new(dek, AES.MODE_CBC, iv)
#     plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
#     return plaintext.decode()

# def change_user_password(user_name: str, old_password: str, new_password: str, infile: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     entry = blob["wrapped_keys"][user_name]
#     salt = b64decode(entry["salt"])
#     iv = b64decode(entry["iv"])
#     wrapped_dek = b64decode(entry["wrapped_dek"])
#     old_key = derive_key(old_password, salt)
#     cipher = AES.new(old_key, AES.MODE_CBC, iv)
#     dek = unpad(cipher.decrypt(wrapped_dek), AES.block_size)
#     new_salt = get_random_bytes(SALT_LEN)
#     new_iv = get_random_bytes(IV_LEN)
#     new_key = derive_key(new_password, new_salt)
#     new_cipher = AES.new(new_key, AES.MODE_CBC, new_iv)
#     new_wrapped_dek = new_cipher.encrypt(pad(dek, AES.block_size))
#     blob["wrapped_keys"][user_name] = {
#         "salt": b64encode(new_salt).decode(),
#         "iv": b64encode(new_iv).decode(),
#         "wrapped_dek": b64encode(new_wrapped_dek).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# def add_user_to_secret(user_name: str, user_password: str, infile: str, authfile: str, existing_user: str, existing_user_pw: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     existing = blob["wrapped_keys"][existing_user]
#     salt = b64decode(existing["salt"])
#     wrapper_iv = b64decode(existing["iv"])
#     encrypted_dek = b64decode(existing["wrapped_dek"])
#     user_key = derive_key(existing_user_pw, salt)
#     wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
#     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
#     new_salt = get_random_bytes(SALT_LEN)
#     new_iv = get_random_bytes(IV_LEN)
#     new_key = derive_key(user_password, new_salt)
#     new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
#     new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
#     with open(authfile, "r") as f:
#         auth_db = json.load(f)
#     role = auth_db[user_name].get("role", "user")
#     blob["wrapped_keys"][user_name] = {
#         "salt": b64encode(new_salt).decode(),
#         "iv": b64encode(new_iv).decode(),
#         "wrapped_dek": b64encode(new_wrapped_dek).decode(),
#         "role": role
#     }
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# def remove_user_from_secret(user_name: str, infile: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     if user_name in blob["wrapped_keys"]:
#         del blob["wrapped_keys"][user_name]
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# def admin_reset_wrapped_password(target_user: str, new_password: str, infile: str, admin: str, admin_pw: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     if target_user not in blob["wrapped_keys"]:
#         raise ValueError(f"User '{target_user}' not found")
#     wrapped = blob["wrapped_keys"][admin]
#     salt = b64decode(wrapped["salt"])
#     wrapper_iv = b64decode(wrapped["iv"])
#     encrypted_dek = b64decode(wrapped["wrapped_dek"])
#     admin_key = derive_key(admin_pw, salt)
#     wrapper = AES.new(admin_key, AES.MODE_CBC, wrapper_iv)
#     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
#     new_salt = get_random_bytes(SALT_LEN)
#     new_iv = get_random_bytes(IV_LEN)
#     new_key = derive_key(new_password, new_salt)
#     new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
#     new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
#     entry = blob["wrapped_keys"][target_user]
#     blob["wrapped_keys"][target_user] = {
#         "salt": b64encode(new_salt).decode(),
#         "iv": b64encode(new_iv).decode(),
#         "wrapped_dek": b64encode(new_wrapped_dek).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(infile, "w") as f:
#         json.dump(blob, f)



# import click
# # ...existing code...

# @click.group()
# def cli():
#     """Franklin Educator User & Secret Management CLI"""
#     pass

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("authfile")
# @click.option("--role", default="user", help="Role for the user (default: user)")
# def create_user(username, password, authfile, role):
#     """Create a user with a role."""
#     create_user(username, password, authfile, role)
#     click.echo(f"User '{username}' created with role '{role}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("authfile")
# def get_role(username, authfile):
#     """Get a user's role."""
#     role = get_user_role(username, authfile)
#     click.echo(f"User '{username}' has role '{role}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("old_password")
# @click.argument("new_password")
# @click.argument("authfile")
# def change_password(username, old_password, new_password, authfile):
#     """Change your own password."""
#     change_user_auth_password(username, old_password, new_password, authfile)
#     click.echo(f"Password changed for '{username}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("new_password")
# @click.argument("authfile")
# def admin_reset_password(username, new_password, authfile):
#     """Admin: reset a user's password."""
#     admin_reset_user_password(username, new_password, authfile)
#     click.echo(f"Password reset for '{username}'.")

# @cli.command()
# @click.argument("secret")
# @click.argument("user_passwords", nargs=-1)
# @click.argument("authfile")
# @click.argument("outfile")
# def encrypt_secret(secret, user_passwords, authfile, outfile):
#     """
#     Encrypt a secret for users.
#     USER_PASSWORDS: username=password pairs, e.g. alice=alice_pw bob=bob_pw
#     """
#     upw = {}
#     for pair in user_passwords:
#         if "=" not in pair:
#             raise click.UsageError("Each user_password must be in username=password format.")
#         user, pw = pair.split("=", 1)
#         upw[user] = pw
#     encrypt_for_users(secret, upw, authfile, outfile)
#     click.echo(f"Secret encrypted for users: {', '.join(upw.keys())}")

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("infile")
# def decrypt_secret(username, password, infile):
#     """Decrypt a secret as a user."""
#     secret = decrypt_with_user(username, password, infile)
#     click.echo(f"Decrypted secret: {secret}")

# @cli.command()
# @click.argument("username")
# @click.argument("old_password")
# @click.argument("new_password")
# @click.argument("infile")
# def change_secret_password(username, old_password, new_password, infile):
#     """Change your password for secret access."""
#     change_user_password(username, old_password, new_password, infile)
#     click.echo(f"Secret password changed for '{username}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("infile")
# @click.argument("authfile")
# @click.argument("existing_user")
# @click.argument("existing_user_pw")
# def add_user_secret(username, password, infile, authfile, existing_user, existing_user_pw):
#     """Add a user to a secret (requires existing user credentials)."""
#     add_user_to_secret(username, password, infile, authfile, existing_user, existing_user_pw)
#     click.echo(f"User '{username}' added to secret.")

# @cli.command()
# @click.argument("username")
# @click.argument("infile")
# def remove_user_secret(username, infile):
#     """Remove a user from a secret."""
#     remove_user_from_secret(username, infile)
#     click.echo(f"User '{username}' removed from secret.")

# @cli.command()
# @click.argument("target_user")
# @click.argument("new_password")
# @click.argument("infile")
# @click.argument("admin")
# @click.argument("admin_pw")
# def admin_reset_secret_password(target_user, new_password, infile, admin, admin_pw):
#     """Admin: reset a user's secret password."""
#     admin_reset_wrapped_password(target_user, new_password, infile, admin, admin_pw)
#     click.echo(f"Secret password reset for '{target_user}'.")

# if __name__ == "__main__":
#     cli()    

# # # === Example Workflow ===
# # if __name__ == "__main__":
# #     # Create authentication-only users
# #     create_user("carol", "carol_password", "auth_db.json")
# #     create_user("dave", "dave_password", "auth_db.json")

# #     # Create users with roles
# #     create_user("alice", "alice_pw", "auth_db.json", role="admin")
# #     create_user("bob", "bob_pw", "auth_db.json", role="admin")
# #     create_user("eve", "eve_pw", "auth_db.json", role="user")

# #     # Change Carol's password
# #     change_user_auth_password("carol", "carol_password", "new_carol_pw", "auth_db.json")

# #     # Admin resets Dave's password
# #     admin_reset_user_password("dave", "reset_dave_pw", "auth_db.json")

# #     # Encrypt a shared secret for Alice, Bob (admins) and Eve (user)
# #     encrypt_for_users(
# #         "TopSecret!",
# #         {"alice": "alice_pw", "bob": "bob_pw", "eve": "eve_pw"},
# #         "auth_db.json",
# #         "secret.json"
# #     )

# #     # Decrypt the secret as Alice (admin)
# #     print(decrypt_with_user("alice", "alice_pw", "secret.json"))

# #     # Decrypt the secret as Eve (user)
# #     print(decrypt_with_user("eve", "eve_pw", "secret.json"))

# #     # Change Alice's password
# #     change_user_password("alice", "alice_pw", "new_alice_pw", "secret.json")
# #     print(decrypt_with_user("alice", "new_alice_pw", "secret.json"))

# #     # Add Charlie as a new admin
# #     create_user("charlie", "charlie_pw", "auth_db.json", role="admin")
# #     add_user_to_secret("charlie", "charlie_pw", "secret.json", "auth_db.json", "bob", "bob_pw")
# #     print(decrypt_with_user("charlie", "charlie_pw", "secret.json"))

# #     # Admin resets Charlie's password
# #     admin_reset_wrapped_password("charlie", "reset_charlie_pw", "secret.json", "alice", "new_alice_pw")
# #     print(decrypt_with_user("charlie", "reset_charlie_pw", "secret.json"))

# #     # Remove Bob
# #     remove_user_from_secret("bob", "secret.json")

# #     # Print user roles
# #     print(get_user_role("alice", "auth_db.json"))
# #     print(get_user_role("carol", "auth_db.json"))
# #     print(get_user_role("eve", "auth_db.json"))

# '''
# # 1. Create users (admins and non-admins)
# python encrypt.py create-user alice alice_pw auth_db.json --role=admin
# python encrypt.py create-user bob bob_pw auth_db.json --role=admin
# python encrypt.py create-user carol carol_pw auth_db.json --role=user
# python encrypt.py create-user dave dave_pw auth_db.json --role=user

# # 2. Check a user's role
# python encrypt.py get-role alice auth_db.json
# # Output: User 'alice' has role 'admin'.

# # 3. Change your own password (non-admin or admin)
# python encrypt.py change-password carol carol_pw new_carol_pw auth_db.json

# # 4. Admin resets another user's password
# python encrypt.py admin-reset-password dave reset_dave_pw auth_db.json

# # 5. Encrypt a secret for a group (admins and users)
# python encrypt.py encrypt-secret "TopSecret!" alice=alice_pw bob=bob_pw carol=new_carol_pw auth_db.json secret.json

# # 6. Decrypt the secret as a user
# python encrypt.py decrypt-secret alice alice_pw secret.json
# # Output: Decrypted secret: TopSecret!

# python encrypt.py decrypt-secret carol new_carol_pw secret.json
# # Output: Decrypted secret: TopSecret!

# # 7. Change your password for secret access
# python encrypt.py change-secret-password alice alice_pw new_alice_pw secret.json

# # 8. Add a new user to the secret (requires an existing user's credentials)
# python encrypt.py create-user eve eve_pw auth_db.json --role=user
# python encrypt.py add-user-secret eve eve_pw secret.json auth_db.json alice new_alice_pw

# # 9. Remove a user from the secret
# python encrypt.py remove-user-secret bob secret.json

# # 10. Admin resets a user's secret password (for secret access)
# python encrypt.py admin-reset-secret-password eve reset_eve_pw secret.json alice new_alice_pw

# # 11. Decrypt the secret as the user with the reset password
# python encrypt.py decrypt-secret eve reset_eve_pw secret.json
# # Output: Decrypted secret: TopSecret!
# '''

##############################################################

# import os
# import json
# from base64 import b64encode, b64decode
# from typing import Dict
# from Crypto.Cipher import AES
# from Crypto.Protocol.KDF import PBKDF2
# from Crypto.Hash import SHA256
# from Crypto.Random import get_random_bytes
# from Crypto.Util.Padding import pad, unpad
# import click

# # Constants
# KEY_LEN = 32
# IV_LEN = 16
# SALT_LEN = 16
# PBKDF2_ITERATIONS = 100_000
# HASH_ITERATIONS = 100_000

# # === Key Derivation and Hashing ===
# def derive_key(password: str, salt: bytes) -> bytes:
#     return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=PBKDF2_ITERATIONS, hmac_hash_module=SHA256)

# def hash_password(password: str, salt: bytes) -> bytes:
#     return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=HASH_ITERATIONS)

# # === Auth-Only User Management ===
# def create_user(username: str, password: str, authfile: str, role: str = "user"):
#     salt = get_random_bytes(SALT_LEN)
#     pw_hash = hash_password(password, salt)
#     try:
#         with open(authfile, "r") as f:
#             db = json.load(f)
#     except FileNotFoundError:
#         db = {}
#     db[username] = {
#         "salt": b64encode(salt).decode(),
#         "password_hash": b64encode(pw_hash).decode(),
#         "role": role
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)

# def get_user_role(username: str, authfile: str) -> str:
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     return db[username].get("role", "user")

# def change_user_auth_password(username: str, old_password: str, new_password: str, authfile: str):
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     entry = db[username]
#     salt = b64decode(entry["salt"])
#     stored_hash = b64decode(entry["password_hash"])
#     if hash_password(old_password, salt) != stored_hash:
#         raise ValueError("Incorrect old password")
#     new_salt = get_random_bytes(SALT_LEN)
#     new_hash = hash_password(new_password, new_salt)
#     db[username] = {
#         "salt": b64encode(new_salt).decode(),
#         "password_hash": b64encode(new_hash).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)

# def admin_reset_user_password(username: str, new_password: str, authfile: str):
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     entry = db[username]
#     new_salt = get_random_bytes(SALT_LEN)
#     new_hash = hash_password(new_password, new_salt)
#     db[username] = {
#         "salt": b64encode(new_salt).decode(),
#         "password_hash": b64encode(new_hash).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)

# # === Shared Secret Encryption ===
# def encrypt_for_users(secret: str, user_passwords: Dict[str, str], authfile: str, outfile: str):
#     iv = get_random_bytes(IV_LEN)
#     dek = get_random_bytes(KEY_LEN)
#     cipher = AES.new(dek, AES.MODE_CBC, iv)
#     ciphertext = cipher.encrypt(pad(secret.encode(), AES.block_size))
#     wrapped_keys = {}
#     with open(authfile, "r") as f:
#         auth_db = json.load(f)
#     for user, user_pw in user_passwords.items():
#         salt = get_random_bytes(SALT_LEN)
#         user_key = derive_key(user_pw, salt)
#         wrapper_iv = get_random_bytes(IV_LEN)
#         wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
#         encrypted_dek = wrapper.encrypt(pad(dek, AES.block_size))
#         role = auth_db[user].get("role", "user")
#         wrapped_keys[user] = {
#             "salt": b64encode(salt).decode(),
#             "iv": b64encode(wrapper_iv).decode(),
#             "wrapped_dek": b64encode(encrypted_dek).decode(),
#             "role": role
#         }
#     output = {
#         "ciphertext": b64encode(ciphertext).decode(),
#         "iv": b64encode(iv).decode(),
#         "wrapped_keys": wrapped_keys
#     }
#     with open(outfile, "w") as f:
#         json.dump(output, f)

# def decrypt_with_user(user: str, user_pw: str, infile: str) -> str:
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     ciphertext = b64decode(blob["ciphertext"])
#     iv = b64decode(blob["iv"])
#     wrapped = blob["wrapped_keys"][user]
#     salt = b64decode(wrapped["salt"])
#     wrapper_iv = b64decode(wrapped["iv"])
#     encrypted_dek = b64decode(wrapped["wrapped_dek"])
#     user_key = derive_key(user_pw, salt)
#     wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
#     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
#     cipher = AES.new(dek, AES.MODE_CBC, iv)
#     plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
#     return plaintext.decode()

# def change_user_password(user_name: str, old_password: str, new_password: str, infile: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     entry = blob["wrapped_keys"][user_name]
#     salt = b64decode(entry["salt"])
#     iv = b64decode(entry["iv"])
#     wrapped_dek = b64decode(entry["wrapped_dek"])
#     old_key = derive_key(old_password, salt)
#     cipher = AES.new(old_key, AES.MODE_CBC, iv)
#     dek = unpad(cipher.decrypt(wrapped_dek), AES.block_size)
#     new_salt = get_random_bytes(SALT_LEN)
#     new_iv = get_random_bytes(IV_LEN)
#     new_key = derive_key(new_password, new_salt)
#     new_cipher = AES.new(new_key, AES.MODE_CBC, new_iv)
#     new_wrapped_dek = new_cipher.encrypt(pad(dek, AES.block_size))
#     blob["wrapped_keys"][user_name] = {
#         "salt": b64encode(new_salt).decode(),
#         "iv": b64encode(new_iv).decode(),
#         "wrapped_dek": b64encode(new_wrapped_dek).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# def add_user_to_secret(user_name: str, user_password: str, infile: str, authfile: str, existing_user: str, existing_user_pw: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     existing = blob["wrapped_keys"][existing_user]
#     salt = b64decode(existing["salt"])
#     wrapper_iv = b64decode(existing["iv"])
#     encrypted_dek = b64decode(existing["wrapped_dek"])
#     user_key = derive_key(existing_user_pw, salt)
#     wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
#     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
#     new_salt = get_random_bytes(SALT_LEN)
#     new_iv = get_random_bytes(IV_LEN)
#     new_key = derive_key(user_password, new_salt)
#     new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
#     new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
#     with open(authfile, "r") as f:
#         auth_db = json.load(f)
#     role = auth_db[user_name].get("role", "user")
#     blob["wrapped_keys"][user_name] = {
#         "salt": b64encode(new_salt).decode(),
#         "iv": b64encode(new_iv).decode(),
#         "wrapped_dek": b64encode(new_wrapped_dek).decode(),
#         "role": role
#     }
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# def remove_user_from_secret(user_name: str, infile: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     if user_name in blob["wrapped_keys"]:
#         del blob["wrapped_keys"][user_name]
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# def admin_reset_wrapped_password(target_user: str, new_password: str, infile: str, admin: str, admin_pw: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     if target_user not in blob["wrapped_keys"]:
#         raise ValueError(f"User '{target_user}' not found")
#     wrapped = blob["wrapped_keys"][admin]
#     salt = b64decode(wrapped["salt"])
#     wrapper_iv = b64decode(wrapped["iv"])
#     encrypted_dek = b64decode(wrapped["wrapped_dek"])
#     admin_key = derive_key(admin_pw, salt)
#     wrapper = AES.new(admin_key, AES.MODE_CBC, wrapper_iv)
#     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
#     new_salt = get_random_bytes(SALT_LEN)
#     new_iv = get_random_bytes(IV_LEN)
#     new_key = derive_key(new_password, new_salt)
#     new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
#     new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
#     entry = blob["wrapped_keys"][target_user]
#     blob["wrapped_keys"][target_user] = {
#         "salt": b64encode(new_salt).decode(),
#         "iv": b64encode(new_iv).decode(),
#         "wrapped_dek": b64encode(new_wrapped_dek).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# # === CLI ===

# @click.group()
# def cli():
#     """Franklin Educator User & Secret Management CLI"""
#     pass

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("authfile")
# @click.option("--role", default="user", help="Role for the user (default: user)")
# def create_user_cmd(username, password, authfile, role):
#     """Create a user with a role."""
#     create_user(username, password, authfile, role)
#     click.echo(f"User '{username}' created with role '{role}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("authfile")
# def get_role(username, authfile):
#     """Get a user's role."""
#     role = get_user_role(username, authfile)
#     click.echo(f"User '{username}' has role '{role}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("old_password")
# @click.argument("new_password")
# @click.argument("authfile")
# def change_password(username, old_password, new_password, authfile):
#     """Change your own password."""
#     change_user_auth_password(username, old_password, new_password, authfile)
#     click.echo(f"Password changed for '{username}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("new_password")
# @click.argument("authfile")
# def admin_reset_password(username, new_password, authfile):
#     """Admin: reset a user's password."""
#     admin_reset_user_password(username, new_password, authfile)
#     click.echo(f"Password reset for '{username}'.")

# @cli.command()
# @click.argument("secret")
# @click.argument("user_passwords", nargs=-1)
# @click.argument("authfile")
# @click.argument("outfile")
# def encrypt_secret(secret, user_passwords, authfile, outfile):
#     """
#     Encrypt a secret for users.
#     USER_PASSWORDS: username=password pairs, e.g. alice=alice_pw bob=bob_pw
#     """
#     upw = {}
#     for pair in user_passwords:
#         if "=" not in pair:
#             raise click.UsageError("Each user_password must be in username=password format.")
#         user, pw = pair.split("=", 1)
#         upw[user] = pw
#     encrypt_for_users(secret, upw, authfile, outfile)
#     click.echo(f"Secret encrypted for users: {', '.join(upw.keys())}")

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("infile")
# def decrypt_secret(username, password, infile):
#     """Decrypt a secret as a user."""
#     secret = decrypt_with_user(username, password, infile)
#     click.echo(f"Decrypted secret: {secret}")

# @cli.command()
# @click.argument("username")
# @click.argument("old_password")
# @click.argument("new_password")
# @click.argument("infile")
# def change_secret_password(username, old_password, new_password, infile):
#     """Change your password for secret access."""
#     change_user_password(username, old_password, new_password, infile)
#     click.echo(f"Secret password changed for '{username}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("infile")
# @click.argument("authfile")
# @click.argument("existing_user")
# @click.argument("existing_user_pw")
# def add_user_secret(username, password, infile, authfile, existing_user, existing_user_pw):
#     """Add a user to a secret (requires existing user credentials)."""
#     add_user_to_secret(username, password, infile, authfile, existing_user, existing_user_pw)
#     click.echo(f"User '{username}' added to secret.")

# @cli.command()
# @click.argument("username")
# @click.argument("infile")
# def remove_user_secret(username, infile):
#     """Remove a user from a secret."""
#     remove_user_from_secret(username, infile)
#     click.echo(f"User '{username}' removed from secret.")

# @cli.command()
# @click.argument("target_user")
# @click.argument("new_password")
# @click.argument("infile")
# @click.argument("admin")
# @click.argument("admin_pw")
# def admin_reset_secret_password(target_user, new_password, infile, admin, admin_pw):
#     """Admin: reset a user's secret password."""
#     admin_reset_wrapped_password(target_user, new_password, infile, admin, admin_pw)
#     click.echo(f"Secret password reset for '{target_user}'.")

# if __name__ == "__main__":
#     cli()

# '''
# # 1. Create users (admins and non-admins)
# python encrypt.py create-user alice alice_pw auth_db.json --role=admin
# python encrypt.py create-user bob bob_pw auth_db.json --role=admin
# python encrypt.py create-user carol carol_pw auth_db.json --role=user
# python encrypt.py create-user dave dave_pw auth_db.json --role=user

# # 2. Check a user's role
# python encrypt.py get-role alice auth_db.json
# # Output: User 'alice' has role 'admin'.

# # 3. Change your own password (non-admin or admin)
# python encrypt.py change-password carol carol_pw new_carol_pw auth_db.json

# # 4. Admin resets another user's password
# python encrypt.py admin-reset-password dave reset_dave_pw auth_db.json

# # 5. Encrypt a secret for a group (admins and users)
# python encrypt.py encrypt-secret "TopSecret!" alice=alice_pw bob=bob_pw carol=new_carol_pw auth_db.json secret.json

# # 6. Decrypt the secret as a user
# python encrypt.py decrypt-secret alice alice_pw secret.json
# # Output: Decrypted secret: TopSecret!

# python encrypt.py decrypt-secret carol new_carol_pw secret.json
# # Output: Decrypted secret: TopSecret!

# # 7. Change your password for secret access
# python encrypt.py change-secret-password alice alice_pw new_alice_pw secret.json

# # 8. Add a new user to the secret (requires an existing user's credentials)
# python encrypt.py create-user eve eve_pw auth_db.json --role=user
# python encrypt.py add-user-secret eve eve_pw secret.json auth_db.json alice new_alice_pw

# # 9. Remove a user from the secret
# python encrypt.py remove-user-secret bob secret.json

# # 10. Admin resets a user's secret password (for secret access)
# python encrypt.py admin-reset-secret-password eve reset_eve_pw secret.json alice new_alice_pw

# # 11. Decrypt the secret as the user with the reset password
# python encrypt.py decrypt-secret eve reset_eve_pw secret.json
# # Output: Decrypted secret: TopSecret!
# '''


##############################################################

# import os
# import json
# from base64 import b64encode, b64decode
# from typing import Dict, List
# from Crypto.Cipher import AES
# from Crypto.Protocol.KDF import PBKDF2
# from Crypto.Hash import SHA256
# from Crypto.Random import get_random_bytes
# from Crypto.Util.Padding import pad, unpad
# import click

# # Constants
# KEY_LEN = 32
# IV_LEN = 16
# SALT_LEN = 16
# PBKDF2_ITERATIONS = 100_000
# HASH_ITERATIONS = 100_000

# # === Key Derivation and Hashing ===
# def derive_key(password: str, salt: bytes) -> bytes:
#     return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=PBKDF2_ITERATIONS, hmac_hash_module=SHA256)

# def hash_password(password: str, salt: bytes) -> bytes:
#     return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=HASH_ITERATIONS)

# # === Auth-Only User Management ===
# def create_user(username: str, password: str, authfile: str, role: str = "user"):
#     salt = get_random_bytes(SALT_LEN)
#     pw_hash = hash_password(password, salt)
#     try:
#         with open(authfile, "r") as f:
#             db = json.load(f)
#     except FileNotFoundError:
#         db = {}
#     db[username] = {
#         "salt": b64encode(salt).decode(),
#         "password_hash": b64encode(pw_hash).decode(),
#         "role": role
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)

# def get_user_role(username: str, authfile: str) -> str:
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     return db[username].get("role", "user")

# def verify_user_password(username: str, password: str, authfile: str) -> bool:
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         return False
#     entry = db[username]
#     salt = b64decode(entry["salt"])
#     stored_hash = b64decode(entry["password_hash"])
#     return hash_password(password, salt) == stored_hash

# def change_user_password_everywhere(username: str, old_password: str, new_password: str, authfile: str, secret_files: List[str]):
#     # Change in auth DB
#     change_user_auth_password(username, old_password, new_password, authfile)
#     # Change in all secret files
#     for secretfile in secret_files:
#         try:
#             change_user_secret_password(username, old_password, new_password, secretfile)
#         except Exception as e:
#             print(f"Warning: Could not update secret file {secretfile}: {e}")

# def change_user_auth_password(username: str, old_password: str, new_password: str, authfile: str):
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     entry = db[username]
#     salt = b64decode(entry["salt"])
#     stored_hash = b64decode(entry["password_hash"])
#     if hash_password(old_password, salt) != stored_hash:
#         raise ValueError("Incorrect old password")
#     new_salt = get_random_bytes(SALT_LEN)
#     new_hash = hash_password(new_password, new_salt)
#     db[username] = {
#         "salt": b64encode(new_salt).decode(),
#         "password_hash": b64encode(new_hash).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)

# def admin_reset_user_password(username: str, new_password: str, authfile: str, secret_files: List[str]):
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     entry = db[username]
#     new_salt = get_random_bytes(SALT_LEN)
#     new_hash = hash_password(new_password, new_salt)
#     db[username] = {
#         "salt": b64encode(new_salt).decode(),
#         "password_hash": b64encode(new_hash).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)
#     # Also update all secret files
#     for secretfile in secret_files:
#         try:
#             admin_reset_wrapped_password(username, new_password, secretfile, username, new_password)
#         except Exception as e:
#             print(f"Warning: Could not update secret file {secretfile}: {e}")

# # === Shared Secret Encryption ===
# def encrypt_for_users(secret: str, usernames: List[str], authfile: str, outfile: str, password_lookup: Dict[str, str]):
#     iv = get_random_bytes(IV_LEN)
#     dek = get_random_bytes(KEY_LEN)
#     cipher = AES.new(dek, AES.MODE_CBC, iv)
#     ciphertext = cipher.encrypt(pad(secret.encode(), AES.block_size))
#     wrapped_keys = {}
#     with open(authfile, "r") as f:
#         auth_db = json.load(f)
#     for user in usernames:
#         user_pw = password_lookup[user]
#         salt = get_random_bytes(SALT_LEN)
#         user_key = derive_key(user_pw, salt)
#         wrapper_iv = get_random_bytes(IV_LEN)
#         wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
#         encrypted_dek = wrapper.encrypt(pad(dek, AES.block_size))
#         role = auth_db[user].get("role", "user")
#         wrapped_keys[user] = {
#             "salt": b64encode(salt).decode(),
#             "iv": b64encode(wrapper_iv).decode(),
#             "wrapped_dek": b64encode(encrypted_dek).decode(),
#             "role": role
#         }
#     output = {
#         "ciphertext": b64encode(ciphertext).decode(),
#         "iv": b64encode(iv).decode(),
#         "wrapped_keys": wrapped_keys
#     }
#     with open(outfile, "w") as f:
#         json.dump(output, f)

# def decrypt_with_user(user: str, user_pw: str, infile: str) -> str:
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     ciphertext = b64decode(blob["ciphertext"])
#     iv = b64decode(blob["iv"])
#     wrapped = blob["wrapped_keys"][user]
#     salt = b64decode(wrapped["salt"])
#     wrapper_iv = b64decode(wrapped["iv"])
#     encrypted_dek = b64decode(wrapped["wrapped_dek"])
#     user_key = derive_key(user_pw, salt)
#     wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
#     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
#     cipher = AES.new(dek, AES.MODE_CBC, iv)
#     plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
#     return plaintext.decode()

# def change_user_secret_password(user_name: str, old_password: str, new_password: str, infile: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     entry = blob["wrapped_keys"][user_name]
#     salt = b64decode(entry["salt"])
#     iv = b64decode(entry["iv"])
#     wrapped_dek = b64decode(entry["wrapped_dek"])
#     old_key = derive_key(old_password, salt)
#     cipher = AES.new(old_key, AES.MODE_CBC, iv)
#     dek = unpad(cipher.decrypt(wrapped_dek), AES.block_size)
#     new_salt = get_random_bytes(SALT_LEN)
#     new_iv = get_random_bytes(IV_LEN)
#     new_key = derive_key(new_password, new_salt)
#     new_cipher = AES.new(new_key, AES.MODE_CBC, new_iv)
#     new_wrapped_dek = new_cipher.encrypt(pad(dek, AES.block_size))
#     blob["wrapped_keys"][user_name] = {
#         "salt": b64encode(new_salt).decode(),
#         "iv": b64encode(new_iv).decode(),
#         "wrapped_dek": b64encode(new_wrapped_dek).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# def add_user_to_secret(user_name: str, user_password: str, infile: str, authfile: str, existing_user: str, existing_user_pw: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     existing = blob["wrapped_keys"][existing_user]
#     salt = b64decode(existing["salt"])
#     wrapper_iv = b64decode(existing["iv"])
#     encrypted_dek = b64decode(existing["wrapped_dek"])
#     user_key = derive_key(existing_user_pw, salt)
#     wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
#     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
#     new_salt = get_random_bytes(SALT_LEN)
#     new_iv = get_random_bytes(IV_LEN)
#     new_key = derive_key(user_password, new_salt)
#     new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
#     new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
#     with open(authfile, "r") as f:
#         auth_db = json.load(f)
#     role = auth_db[user_name].get("role", "user")
#     blob["wrapped_keys"][user_name] = {
#         "salt": b64encode(new_salt).decode(),
#         "iv": b64encode(new_iv).decode(),
#         "wrapped_dek": b64encode(new_wrapped_dek).decode(),
#         "role": role
#     }
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# def remove_user_from_secret(user_name: str, infile: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     if user_name in blob["wrapped_keys"]:
#         del blob["wrapped_keys"][user_name]
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# def admin_reset_wrapped_password(target_user: str, new_password: str, infile: str, admin: str, admin_pw: str):
#     with open(infile, "r") as f:
#         blob = json.load(f)
#     if target_user not in blob["wrapped_keys"]:
#         raise ValueError(f"User '{target_user}' not found")
#     wrapped = blob["wrapped_keys"][admin]
#     salt = b64decode(wrapped["salt"])
#     wrapper_iv = b64decode(wrapped["iv"])
#     encrypted_dek = b64decode(wrapped["wrapped_dek"])
#     admin_key = derive_key(admin_pw, salt)
#     wrapper = AES.new(admin_key, AES.MODE_CBC, wrapper_iv)
#     dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
#     new_salt = get_random_bytes(SALT_LEN)
#     new_iv = get_random_bytes(IV_LEN)
#     new_key = derive_key(new_password, new_salt)
#     new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
#     new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
#     entry = blob["wrapped_keys"][target_user]
#     blob["wrapped_keys"][target_user] = {
#         "salt": b64encode(new_salt).decode(),
#         "iv": b64encode(new_iv).decode(),
#         "wrapped_dek": b64encode(new_wrapped_dek).decode(),
#         "role": entry.get("role", "user")
#     }
#     with open(infile, "w") as f:
#         json.dump(blob, f)

# # === CLI ===

# @click.group()
# def cli():
#     """Franklin Educator User & Secret Management CLI"""
#     pass

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("authfile")
# @click.option("--role", default="user", help="Role for the user (default: user)")
# def create_user_cmd(username, password, authfile, role):
#     """Create a user with a role."""
#     create_user(username, password, authfile, role)
#     click.echo(f"User '{username}' created with role '{role}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("authfile")
# def get_role(username, authfile):
#     """Get a user's role."""
#     role = get_user_role(username, authfile)
#     click.echo(f"User '{username}' has role '{role}'.")

# @cli.command()
# @click.argument("username")
# @click.argument("old_password")
# @click.argument("new_password")
# @click.argument("authfile")
# @click.argument("secret_files", nargs=-1)
# def change_password(username, old_password, new_password, authfile, secret_files):
#     """Change your password everywhere (auth and all secrets)."""
#     change_user_password_everywhere(username, old_password, new_password, authfile, list(secret_files))
#     click.echo(f"Password changed for '{username}' in auth and all secrets.")

# @cli.command()
# @click.argument("username")
# @click.argument("new_password")
# @click.argument("authfile")
# @click.argument("secret_files", nargs=-1)
# def admin_reset_password(username, new_password, authfile, secret_files):
#     """Admin: reset a user's password everywhere."""
#     admin_reset_user_password(username, new_password, authfile, list(secret_files))
#     click.echo(f"Password reset for '{username}' in auth and all secrets.")

# @cli.command()
# @click.argument("secret")
# @click.argument("usernames", nargs=-1)
# @click.argument("authfile")
# @click.argument("outfile")
# def encrypt_secret(secret, usernames, authfile, outfile):
#     """
#     Encrypt a secret for users.
#     USERNAMES: list of usernames (passwords will be prompted)
#     """
#     password_lookup = {}
#     for user in usernames:
#         pw = click.prompt(f"Password for {user}", hide_input=True)
#         password_lookup[user] = pw
#     encrypt_for_users(secret, list(usernames), authfile, outfile, password_lookup)
#     click.echo(f"Secret encrypted for users: {', '.join(usernames)}")

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("infile")
# def decrypt_secret(username, password, infile):
#     """Decrypt a secret as a user."""
#     secret = decrypt_with_user(username, password, infile)
#     click.echo(f"Decrypted secret: {secret}")

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("infile")
# @click.argument("authfile")
# @click.argument("existing_user")
# @click.argument("existing_user_pw")
# def add_user_secret(username, password, infile, authfile, existing_user, existing_user_pw):
#     """Add a user to a secret (requires existing user credentials)."""
#     add_user_to_secret(username, password, infile, authfile, existing_user, existing_user_pw)
#     click.echo(f"User '{username}' added to secret.")

# @cli.command()
# @click.argument("username")
# @click.argument("infile")
# def remove_user_secret(username, infile):
#     """Remove a user from a secret."""
#     remove_user_from_secret(username, infile)
#     click.echo(f"User '{username}' removed from secret.")

# @cli.command()
# @click.argument("target_user")
# @click.argument("new_password")
# @click.argument("infile")
# @click.argument("admin")
# @click.argument("admin_pw")
# def admin_reset_secret_password(target_user, new_password, infile, admin, admin_pw):
#     """Admin: reset a user's secret password."""
#     admin_reset_wrapped_password(target_user, new_password, infile, admin, admin_pw)
#     click.echo(f"Secret password reset for '{target_user}'.")

# if __name__ == "__main__":
#     cli()


##############################################################


import os
import json
from base64 import b64encode, b64decode
from typing import Dict, List
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import click

# Constants
KEY_LEN = 32
IV_LEN = 16
SALT_LEN = 16
PBKDF2_ITERATIONS = 100_000
HASH_ITERATIONS = 100_000

MASTER_ROLE = "master"
ADMIN_ROLE = "admin"
USER_ROLE = "user"

def derive_key(password: str, salt: bytes) -> bytes:
    return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=PBKDF2_ITERATIONS, hmac_hash_module=SHA256)

def hash_password(password: str, salt: bytes) -> bytes:
    return PBKDF2(password.encode(), salt, dkLen=KEY_LEN, count=HASH_ITERATIONS)

# def create_user(username: str, password: str, authfile: str, role: str = "user"):
#     salt = get_random_bytes(SALT_LEN)
#     pw_hash = hash_password(password, salt)
#     try:
#         with open(authfile, "r") as f:
#             db = json.load(f)
#     except FileNotFoundError:
#         db = {}
#     db[username] = {
#         "salt": b64encode(salt).decode(),
#         "password_hash": b64encode(pw_hash).decode(),
#         "role": role
#     }
#     with open(authfile, "w") as f:
#         json.dump(db, f)

# def get_user_role(username: str, authfile: str) -> str:
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         raise ValueError("User not found")
#     return db[username].get("role", "user")

# def verify_user_password(username: str, password: str, authfile: str) -> bool:
#     with open(authfile, "r") as f:
#         db = json.load(f)
#     if username not in db:
#         return False
#     entry = db[username]
#     salt = b64decode(entry["salt"])
#     stored_hash = b64decode(entry["password_hash"])
#     return hash_password(password, salt) == stored_hash

def create_user(username: str, password: str, authfile: str, role: str = USER_ROLE):
    salt = get_random_bytes(SALT_LEN)
    pw_hash = hash_password(password, salt)
    try:
        with open(authfile, "r") as f:
            db = json.load(f)
    except FileNotFoundError:
        db = {}
    db[username] = {
        "salt": b64encode(salt).decode(),
        "password_hash": b64encode(pw_hash).decode(),
        "role": role
    }
    with open(authfile, "w") as f:
        json.dump(db, f)

def get_user_role(username: str, authfile: str) -> str:
    with open(authfile, "r") as f:
        db = json.load(f)
    if username not in db:
        raise ValueError("User not found")
    return db[username].get("role", USER_ROLE)

def verify_user_password(username: str, password: str, authfile: str) -> bool:
    with open(authfile, "r") as f:
        db = json.load(f)
    if username not in db:
        return False
    entry = db[username]
    salt = b64decode(entry["salt"])
    stored_hash = b64decode(entry["password_hash"])
    return hash_password(password, salt) == stored_hash

def change_user_password_everywhere(username: str, old_password: str, new_password: str, authfile: str, secret_files: List[str]):
    change_user_auth_password(username, old_password, new_password, authfile)
    for secretfile in secret_files:
        try:
            change_user_secret_password(username, old_password, new_password, secretfile)
        except Exception as e:
            print(f"Warning: Could not update secret file {secretfile}: {e}")

def change_user_auth_password(username: str, old_password: str, new_password: str, authfile: str):
    with open(authfile, "r") as f:
        db = json.load(f)
    if username not in db:
        raise ValueError("User not found")
    entry = db[username]
    salt = b64decode(entry["salt"])
    stored_hash = b64decode(entry["password_hash"])
    if hash_password(old_password, salt) != stored_hash:
        raise ValueError("Incorrect old password")
    new_salt = get_random_bytes(SALT_LEN)
    new_hash = hash_password(new_password, new_salt)
    db[username] = {
        "salt": b64encode(new_salt).decode(),
        "password_hash": b64encode(new_hash).decode(),
        "role": entry.get("role", "user")
    }
    with open(authfile, "w") as f:
        json.dump(db, f)

def admin_reset_user_password(username: str, new_password: str, authfile: str, secret_files: List[str]):
    with open(authfile, "r") as f:
        db = json.load(f)
    if username not in db:
        raise ValueError("User not found")
    entry = db[username]
    new_salt = get_random_bytes(SALT_LEN)
    new_hash = hash_password(new_password, new_salt)
    db[username] = {
        "salt": b64encode(new_salt).decode(),
        "password_hash": b64encode(new_hash).decode(),
        "role": entry.get("role", "user")
    }
    with open(authfile, "w") as f:
        json.dump(db, f)
    for secretfile in secret_files:
        try:
            admin_reset_wrapped_password(username, new_password, secretfile, username, new_password)
        except Exception as e:
            print(f"Warning: Could not update secret file {secretfile}: {e}")

def encrypt_for_users(secret: str, usernames: List[str], authfile: str, outfile: str, password_lookup: Dict[str, str]):
    iv = get_random_bytes(IV_LEN)
    dek = get_random_bytes(KEY_LEN)
    cipher = AES.new(dek, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(secret.encode(), AES.block_size))
    wrapped_keys = {}
    with open(authfile, "r") as f:
        auth_db = json.load(f)
    for user in usernames:
        user_pw = password_lookup[user]
        salt = get_random_bytes(SALT_LEN)
        user_key = derive_key(user_pw, salt)
        wrapper_iv = get_random_bytes(IV_LEN)
        wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
        encrypted_dek = wrapper.encrypt(pad(dek, AES.block_size))
        role = auth_db[user].get("role", "user")
        wrapped_keys[user] = {
            "salt": b64encode(salt).decode(),
            "iv": b64encode(wrapper_iv).decode(),
            "wrapped_dek": b64encode(encrypted_dek).decode(),
            "role": role
        }
    output = {
        "ciphertext": b64encode(ciphertext).decode(),
        "iv": b64encode(iv).decode(),
        "wrapped_keys": wrapped_keys
    }
    with open(outfile, "w") as f:
        json.dump(output, f)

def decrypt_with_user(user: str, user_pw: str, infile: str) -> str:
    with open(infile, "r") as f:
        blob = json.load(f)
    ciphertext = b64decode(blob["ciphertext"])
    iv = b64decode(blob["iv"])
    wrapped = blob["wrapped_keys"][user]
    salt = b64decode(wrapped["salt"])
    wrapper_iv = b64decode(wrapped["iv"])
    encrypted_dek = b64decode(wrapped["wrapped_dek"])
    user_key = derive_key(user_pw, salt)
    wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
    dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
    cipher = AES.new(dek, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return plaintext.decode()

def change_user_secret_password(user_name: str, old_password: str, new_password: str, infile: str):
    with open(infile, "r") as f:
        blob = json.load(f)
    entry = blob["wrapped_keys"][user_name]
    salt = b64decode(entry["salt"])
    iv = b64decode(entry["iv"])
    wrapped_dek = b64decode(entry["wrapped_dek"])
    old_key = derive_key(old_password, salt)
    cipher = AES.new(old_key, AES.MODE_CBC, iv)
    dek = unpad(cipher.decrypt(wrapped_dek), AES.block_size)
    new_salt = get_random_bytes(SALT_LEN)
    new_iv = get_random_bytes(IV_LEN)
    new_key = derive_key(new_password, new_salt)
    new_cipher = AES.new(new_key, AES.MODE_CBC, new_iv)
    new_wrapped_dek = new_cipher.encrypt(pad(dek, AES.block_size))
    blob["wrapped_keys"][user_name] = {
        "salt": b64encode(new_salt).decode(),
        "iv": b64encode(new_iv).decode(),
        "wrapped_dek": b64encode(new_wrapped_dek).decode(),
        "role": entry.get("role", "user")
    }
    with open(infile, "w") as f:
        json.dump(blob, f)

def add_user_to_secret(user_name: str, user_password: str, infile: str, authfile: str, existing_user: str, existing_user_pw: str):
    with open(authfile, "r") as f:
        auth_db = json.load(f)
    if auth_db[existing_user].get("role") not in ["admin", "master"]:
        raise click.ClickException("Only admins or master can add users to secrets.")
    if not verify_user_password(existing_user, existing_user_pw, authfile):
        raise click.ClickException("Admin authentication failed.")
    with open(infile, "r") as f:
        blob = json.load(f)
    existing = blob["wrapped_keys"][existing_user]
    salt = b64decode(existing["salt"])
    wrapper_iv = b64decode(existing["iv"])
    encrypted_dek = b64decode(existing["wrapped_dek"])
    user_key = derive_key(existing_user_pw, salt)
    wrapper = AES.new(user_key, AES.MODE_CBC, wrapper_iv)
    dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
    new_salt = get_random_bytes(SALT_LEN)
    new_iv = get_random_bytes(IV_LEN)
    new_key = derive_key(user_password, new_salt)
    new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
    new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
    role = auth_db[user_name].get("role", "user")
    blob["wrapped_keys"][user_name] = {
        "salt": b64encode(new_salt).decode(),
        "iv": b64encode(new_iv).decode(),
        "wrapped_dek": b64encode(new_wrapped_dek).decode(),
        "role": role
    }
    with open(infile, "w") as f:
        json.dump(blob, f)

def remove_user_from_secret(user_name: str, infile: str):
    with open(infile, "r") as f:
        blob = json.load(f)
    if user_name in blob["wrapped_keys"]:
        del blob["wrapped_keys"][user_name]
    with open(infile, "w") as f:
        json.dump(blob, f)

def admin_reset_wrapped_password(target_user: str, new_password: str, infile: str, admin: str, admin_pw: str):
    # Only allow if admin is actually an admin and password is correct
    # (for legacy compatibility, allow self-reset)
    with open("auth_db.json", "r") as f:
        auth_db = json.load(f)
    if admin != target_user:
        if auth_db[admin].get("role") != "admin":
            raise click.ClickException("Only admins can reset other users' secret passwords.")
        if not verify_user_password(admin, admin_pw, "auth_db.json"):
            raise click.ClickException("Admin authentication failed.")
    with open(infile, "r") as f:
        blob = json.load(f)
    if target_user not in blob["wrapped_keys"]:
        raise ValueError(f"User '{target_user}' not found")
    wrapped = blob["wrapped_keys"][admin]
    salt = b64decode(wrapped["salt"])
    wrapper_iv = b64decode(wrapped["iv"])
    encrypted_dek = b64decode(wrapped["wrapped_dek"])
    admin_key = derive_key(admin_pw, salt)
    wrapper = AES.new(admin_key, AES.MODE_CBC, wrapper_iv)
    dek = unpad(wrapper.decrypt(encrypted_dek), AES.block_size)
    new_salt = get_random_bytes(SALT_LEN)
    new_iv = get_random_bytes(IV_LEN)
    new_key = derive_key(new_password, new_salt)
    new_wrapper = AES.new(new_key, AES.MODE_CBC, new_iv)
    new_wrapped_dek = new_wrapper.encrypt(pad(dek, AES.block_size))
    entry = blob["wrapped_keys"][target_user]
    blob["wrapped_keys"][target_user] = {
        "salt": b64encode(new_salt).decode(),
        "iv": b64encode(new_iv).decode(),
        "wrapped_dek": b64encode(new_wrapped_dek).decode(),
        "role": entry.get("role", "user")
    }
    with open(infile, "w") as f:
        json.dump(blob, f)

@click.group()
def cli():
    """Franklin Educator User & Secret Management CLI"""
    pass

@cli.command("franklin-admin-user-add")
@click.argument("username")
@click.argument("password")
@click.argument("authfile")
@click.option("--role", default=USER_ROLE, help="Role for the user (user/admin/master)")
@click.option("--inviter", default=None, help="Existing master username (required for admin/master role)")
def master_create_user(username, password, authfile, role, inviter):
    """Create a user. Only master can add admin/master users."""
    if role in [ADMIN_ROLE, MASTER_ROLE]:
        if inviter is None:
            # Allow first master only if no masters exist yet
            try:
                with open(authfile, "r") as f:
                    db = json.load(f)
                if any(u.get("role") == MASTER_ROLE for u in db.values()):
                    raise click.ClickException("Only master can add admin/master users. Use --inviter.")
            except FileNotFoundError:
                pass  # Allow first master
        else:
            inviter_pw = click.prompt(f"Password for master '{inviter}'", hide_input=True)
            if not verify_user_password(inviter, inviter_pw, authfile):
                raise click.ClickException("Authentication failed for inviter.")
            if get_user_role(inviter, authfile) != MASTER_ROLE:
                raise click.ClickException("Only master can add admin/master users.")
    create_user(username, password, authfile, role)
    click.echo(f"User '{username}' created with role '{role}'.")

@cli.command("franklin-user-get-role")
@click.argument("username")
@click.argument("authfile")
def get_role(username, authfile):
    """Get a user's role."""
    role = get_user_role(username, authfile)
    click.echo(f"User '{username}' has role '{role}'.")

@cli.command("franklin-user-set-pw")
@click.argument("username")
@click.argument("old_password")
@click.argument("new_password")
@click.argument("authfile")
@click.argument("secret_files", nargs=-1)
def change_password(username, old_password, new_password, authfile, secret_files):
    """Change your password everywhere (auth and all secrets)."""
    change_user_password_everywhere(username, old_password, new_password, authfile, list(secret_files))
    click.echo(f"Password changed for '{username}' in auth and all secrets.")

@cli.command("franklin-master-user-password")
@click.argument("username")
@click.argument("new_password")
@click.argument("authfile")
@click.argument("secret_files", nargs=-1)
@click.option("--inviter", required=True, help="Master username performing the reset")
def master_reset_password(username, new_password, authfile, secret_files, inviter):
    """Master: reset a user's password everywhere. Only master can reset admin passwords."""
    inviter_pw = click.prompt(f"Password for master '{inviter}'", hide_input=True)
    if not verify_user_password(inviter, inviter_pw, authfile):
        raise click.ClickException("Authentication failed for inviter.")
    if get_user_role(inviter, authfile) != MASTER_ROLE:
        raise click.ClickException("Only master can reset passwords.")
    # Only allow master to reset admin or master passwords
    target_role = get_user_role(username, authfile)
    if target_role not in [ADMIN_ROLE, MASTER_ROLE, USER_ROLE]:
        raise click.ClickException("Unknown target user role.")
    if target_role in [ADMIN_ROLE, MASTER_ROLE]:
        admin_reset_user_password(username, new_password, authfile, list(secret_files))
        click.echo(f"Password reset for '{username}' (role: {target_role}) in auth and all secrets.")
    else:
        # For normal users, allow master to reset as well
        admin_reset_user_password(username, new_password, authfile, list(secret_files))
        click.echo(f"Password reset for '{username}' (role: user) in auth and all secrets.")

@cli.command("franklin-admin-user-password")
@click.argument("username")
@click.argument("new_password")
@click.argument("authfile")
@click.argument("secret_files", nargs=-1)
@click.option("--inviter", required=True, help="Admin username performing the reset")
def admin_reset_password(username, new_password, authfile, secret_files, inviter):
    """Admin: reset a user's password everywhere. Cannot reset admin/master users."""
    inviter_pw = click.prompt(f"Password for admin '{inviter}'", hide_input=True)
    if not verify_user_password(inviter, inviter_pw, authfile):
        raise click.ClickException("Authentication failed for inviter.")
    if get_user_role(inviter, authfile) != ADMIN_ROLE:
        raise click.ClickException("Only admins can reset passwords.")
    target_role = get_user_role(username, authfile)
    if target_role in [ADMIN_ROLE, MASTER_ROLE]:
        raise click.ClickException("Admins cannot reset admin/master passwords. Only master can.")
    admin_reset_user_password(username, new_password, authfile, list(secret_files))
    click.echo(f"Password reset for '{username}' (role: user) in auth and all secrets.")

# @click.group()
# def cli():
#     """Franklin Educator User & Secret Management CLI"""
#     pass

# @cli.command()
# @click.argument("username")
# @click.argument("password")
# @click.argument("authfile")
# @click.option("--role", default="user", help="Role for the user (default: user)")
# @click.option("--inviter", default=None, help="Existing admin username (required for admin role)")
# def create_user_cmd(username, password, authfile, role, inviter):
#     """Create a user with a role. Only admins can add other admins."""
#     if role == "admin":
#         if inviter is None:
#             # Allow first admin only if no admins exist yet
#             try:
#                 with open(authfile, "r") as f:
#                     db = json.load(f)
#                 if any(u.get("role") == "admin" for u in db.values()):
#                     raise click.ClickException("Only admins can add other admins. Use --inviter.")
#             except FileNotFoundError:
#                 pass  # Allow first admin
#         else:
#             inviter_pw = click.prompt(f"Password for admin '{inviter}'", hide_input=True)
#             if not verify_user_password(inviter, inviter_pw, authfile):
#                 raise click.ClickException("Authentication failed for inviter.")
#             if get_user_role(inviter, authfile) != "admin":
#                 raise click.ClickException("Only admins can add other admins.")
#     create_user(username, password, authfile, role)
#     click.echo(f"User '{username}' created with role '{role}'.")

# @cli.command("franklin-users-get-role")
# @click.argument("username")
# @click.argument("authfile")
# def get_role(username, authfile):
#     """Get a user's role."""
#     role = get_user_role(username, authfile)
#     click.echo(f"User '{username}' has role '{role}'.")

# @cli.command("franklin-users-set-password")
# @click.argument("username")
# @click.argument("old_password")
# @click.argument("new_password")
# @click.argument("authfile")
# @click.argument("secret_files", nargs=-1)
# def change_password(username, old_password, new_password, authfile, secret_files):
#     """Change your password everywhere (auth and all secrets)."""
#     change_user_password_everywhere(username, old_password, new_password, authfile, list(secret_files))
#     click.echo(f"Password changed for '{username}' in auth and all secrets.")

# @cli.command("franklin-admin-users-password-reset")
# @click.argument("username")
# @click.argument("new_password")
# @click.argument("authfile")
# @click.argument("secret_files", nargs=-1)
# @click.option("--inviter", required=True, help="Admin username performing the reset")
# def admin_reset_password(username, new_password, authfile, secret_files, inviter):
#     """Admin: reset a user's password everywhere."""
#     inviter_pw = click.prompt(f"Password for admin '{inviter}'", hide_input=True)
#     if not verify_user_password(inviter, inviter_pw, authfile):
#         raise click.ClickException("Authentication failed for inviter.")
#     if get_user_role(inviter, authfile) != "admin":
#         raise click.ClickException("Only admins can reset passwords.")
#     admin_reset_user_password(username, new_password, authfile, list(secret_files))
#     click.echo(f"Password reset for '{username}' in auth and all secrets.")

@cli.command("franklin-admin-user-token-set")
@click.argument("secret")
@click.argument("usernames", nargs=-1)
@click.argument("authfile")
@click.argument("outfile")
def encrypt_secret(secret, usernames, authfile, outfile):
    """
    Encrypt a secret for users.
    USERNAMES: list of usernames (passwords will be prompted)
    """
    password_lookup = {}
    for user in usernames:
        pw = click.prompt(f"Password for {user}", hide_input=True)
        password_lookup[user] = pw
    encrypt_for_users(secret, list(usernames), authfile, outfile, password_lookup)
    click.echo(f"Secret encrypted for users: {', '.join(usernames)}")

@cli.command("franklin-admin-user-token-get")
@click.argument("username")
@click.argument("password")
@click.argument("infile")
def decrypt_secret(username, password, infile):
    """Decrypt a secret as a user."""
    secret = decrypt_with_user(username, password, infile)
    click.echo(f"Decrypted secret: {secret}")

@cli.command("franklin-admin-user-grant-role")
@click.argument("username")
@click.argument("password")
@click.argument("infile")
@click.argument("authfile")
@click.argument("existing_user")
@click.argument("existing_user_pw")
def add_user_secret(username, password, infile, authfile, existing_user, existing_user_pw):
    """Add a user to a secret (requires existing admin credentials)."""
    add_user_to_secret(username, password, infile, authfile, existing_user, existing_user_pw)
    click.echo(f"User '{username}' added to secret.")

# @cli.command("franklin-users-revoke-role")
# @click.argument("username")
# @click.argument("infile")
# def remove_user_secret(username, infile):
#     """Remove a user from a secret."""
#     remove_user_from_secret(username, infile)
#     click.echo(f"User '{username}' removed from secret.")

@cli.command("franklin-user-revoke-role")
@click.argument("username")
@click.argument("infile")
@click.option("--admin", required=True, help="Admin username performing the removal")
def remove_user_secret(username, infile, admin):
    """Remove a user from a secret (admin authentication required)."""
    admin_pw = click.prompt(f"Password for admin '{admin}'", hide_input=True)
    # Authenticate admin
    if not verify_user_password(admin, admin_pw, "auth_db.json"):
        raise click.ClickException("Authentication failed for admin.")
    if get_user_role(admin, "auth_db.json") != "admin":
        raise click.ClickException("Only admins can remove users from secrets.")
    remove_user_from_secret(username, infile)
    click.echo(f"User '{username}' removed from secret.")

@cli.command("franklin-admin-user-password")
@click.argument("target_user")
@click.argument("new_password")
@click.argument("infile")
@click.argument("admin")
@click.argument("admin_pw")
def admin_reset_secret_password(target_user, new_password, infile, admin, admin_pw):
    """Admin: reset a user's secret password."""
    admin_reset_wrapped_password(target_user, new_password, infile, admin, admin_pw)
    click.echo(f"Secret password reset for '{target_user}'.")



@cli.command("franklin-admin-user-add")
@click.argument("username")
@click.argument("password")
@click.argument("authfile")
@click.option("--role", default=USER_ROLE, help="Role for the user (user only, not admin/master)")
@click.option("--inviter", required=True, help="Admin username creating the user")
def admin_create_user(username, password, authfile, role, inviter):
    """Admin: create a user (user role only)."""
    if role != USER_ROLE:
        raise click.ClickException("Admins can only create users with role 'user'.")
    inviter_pw = click.prompt(f"Password for admin '{inviter}'", hide_input=True)
    if not verify_user_password(inviter, inviter_pw, authfile):
        raise click.ClickException("Authentication failed for inviter.")
    if get_user_role(inviter, authfile) != ADMIN_ROLE:
        raise click.ClickException("Only admins can create users.")
    create_user(username, password, authfile, role)
    click.echo(f"User '{username}' created with role '{role}' by admin '{inviter}'.")




if __name__ == "__main__":
    cli()