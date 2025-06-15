
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

@cli.group()
def master_group():
    """User admin for master admins
    """
    pass

@cli.group()
def admin_group():
    """User admin for professors
    """
    pass

@cli.group()
def user_group():
    """User admin for TAs
    """
    pass

@admin_group.command("franklin-admin-user-add")
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

@user_group.command("franklin-user-get-role")
@click.argument("username")
@click.argument("authfile")
def get_role(username, authfile):
    """Get a user's role."""
    role = get_user_role(username, authfile)
    click.echo(f"User '{username}' has role '{role}'.")

@user_group.command("franklin-user-set-pw")
@click.argument("username")
@click.argument("old_password")
@click.argument("new_password")
@click.argument("authfile")
@click.argument("secret_files", nargs=-1)
def change_password(username, old_password, new_password, authfile, secret_files):
    """Change your password everywhere (auth and all secrets)."""
    change_user_password_everywhere(username, old_password, new_password, authfile, list(secret_files))
    click.echo(f"Password changed for '{username}' in auth and all secrets.")

@master_group.command("franklin-master-user-password")
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

@admin_group.command("franklin-admin-user-password")
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

@admin_group.command("franklin-admin-user-token-set")
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

@admin_group.command("franklin-admin-user-token-get")
@click.argument("username")
@click.argument("password")
@click.argument("infile")
def decrypt_secret(username, password, infile):
    """Decrypt a secret as a user."""
    secret = decrypt_with_user(username, password, infile)
    click.echo(f"Decrypted secret: {secret}")

@admin_group.command("franklin-admin-user-grant-role")
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

@user_group.command("franklin-user-revoke-role")
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

@admin_group.command("franklin-admin-user-password")
@click.argument("target_user")
@click.argument("new_password")
@click.argument("infile")
@click.argument("admin")
@click.argument("admin_pw")
def admin_reset_secret_password(target_user, new_password, infile, admin, admin_pw):
    """Admin: reset a user's secret password."""
    admin_reset_wrapped_password(target_user, new_password, infile, admin, admin_pw)
    click.echo(f"Secret password reset for '{target_user}'.")

@admin_group.command("franklin-admin-user-add")
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