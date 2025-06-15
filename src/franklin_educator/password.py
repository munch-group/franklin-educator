

import random

def generate_password(password):
    """
    Users are issued the first of the 100 passwords and can then generate 
    new passwords from their current password.
    """
    random.seed(f'{password} - franklin rules!', version=2)
    return ''.join([chr(random.randint(35, 90)) for _ in range(8)])

# def generate_passwords(user_name):
#     """
#     Generate 100 passwords for a user, starting with a new password based 
#     on the user's name.
#     """

#     passwords = []
#     random.seed(f'{user_name} - franklin rules!', version=2)
#     passwords = [new_password(user_name)]
#     for i in range(99):
#         passwords.append(new_password(passwords[-1]))
#     return passwords

# # I should store the current password for each user


# # a user can unlock the password generation module