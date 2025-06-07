import click
import subprocess
import sys
import os
from subprocess import DEVNULL, STDOUT, PIPE
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Tuple, List, Dict, Callable, Any

from franklin import config as cfg
from franklin import utils
from franklin import terminal as term
from franklin import gitlab
from franklin.logger import logger
from . import encrypt
from . import git


import requests

token_path_templ = os.path.dirname(sys.modules['franklin_educator'].__file__) + '/data/admin/{}_token.enc'

def update_project_permissions(user_id: int, project_id: int, access_level: int, api_token: str):
    # API endpoint to update existing member
    url = f"{cfg.gitlab_domain}/api/v4/projects/{project_id}/members/{user_id}"

    headers = {
        "PRIVATE-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    payload = {
        "access_level": access_level
    }

    # Execute request
    response = requests.put(url, headers=headers, json=payload)

    # Output response
    if response.status_code == 200:
        print("Access level updated successfully.")
    elif response.status_code == 404:
        print("User is not a member of the project.")
    else:
        print(f"Error {response.status_code}: {response.json()}")


def update_group_permissions(user_id: int, group_id: int, access_level: int, api_token: str):
    # API endpoint to update existing member
    url = f"{cfg.gitlab_domain}/api/v4/groups/{group_id}/members/{user_id}"

    headers = {
        "PRIVATE-TOKEN": api_token,
        "Content-Type": "application/json"
    }

    payload = {
        "access_level": access_level
    }

    # Execute request
    response = requests.put(url, headers=headers, json=payload)

    # Output response
    if response.status_code == 200:
        print("Access level updated successfully.")
    elif response.status_code == 404:
        print("User is not a member of the project.")
    else:
        print(f"Error {response.status_code}: {response.json()}")


def get_group_id(group_name, api_token):
    url = f"{cfg.gitlab_domain}/api/v4/groups"
    headers = {"PRIVATE-TOKEN": api_token}
    response = requests.get(url, headers=headers, params={"search": group_name})
    for group in response.json():
        if group["path"] == group_name or group["full_path"] == group_name:
            return group['id']


def get_project_id(project_name, group_id, api_token):
    url = f"{cfg.gitlab_domain}/api/v4/groups/{group_id}/projects"
    headers = {"PRIVATE-TOKEN": api_token}
    response = requests.get(url, headers=headers)
    for project in response.json():
        if project["path"] == project_name or project["name"] == project_name:
            return project['id']


def get_user_id(user_name, api_token):
    url = f"{cfg.gitlab_domain}/api/v4/users?username={user_name}"
    headers = {"PRIVATE-TOKEN": api_token}
    response = requests.get(url, headers=headers)
    user = response.json()[0]
    return user['id']


def update_permissions(user_name, role, course, user, password, project=None):

    with open(token_path_templ.format(user), "rb") as f:
        encrypted = f.read()
    api_token = encrypt.decrypt_token(encrypted, password)


    user_id = get_user_id(user_name)
    group_id = get_group_id(cfg.gitlab_group)
    subgroup_id = get_group_id(course)

    group_perm, subgroup_perm, project_perm = cfg.permissions[role]

    update_group_permissions(user_id, group_id, group_perm, api_token)
    update_group_permissions(user_id, subgroup_id, subgroup_perm, api_token)

    # if project_id is not None:
    #     project_id = get_project_id(project, group_id)
    #     update_group_permissions(user_id, project_id, project_perm)

    # # If you receive a 404 error, the user is not yet a member of the project. In that case, use:
    # # POST /projects/:id/members to add a new user
    # url = f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/members"
    # response = requests.post(url, headers=headers, json={
    #     "user_id": USER_ID,
    #     "access_level": ACCESS_LEVEL
    # })


@click.group(cls=utils.AliasedGroup)
def admin():
    """Admin commands for access control.
    """

@admin.group(cls=utils.AliasedGroup)
def token():
    """Admin commands for admin tokens.
    """


@token.command('set')
@click.option('--user', prompt=True,
              confirmation_prompt=False, help='User name')
@click.option('--password', prompt=True, hide_input=True,
              confirmation_prompt=False, help='Password')
@click.option('--api-token', prompt=True, hide_input=True,
              confirmation_prompt=False, help='Admin personal API token')
def set_admin_token(user, password, api_token, ):
    """Stores an encrypted token for the admin user.
    """
    encrypt.store_encrypted_token(token_path_templ.format(user), api_token, password)


@token.command('get')
@click.option('--user', prompt=True,
              confirmation_prompt=False, help='User name')
@click.option('--password', prompt=True, hide_input=True,
              confirmation_prompt=False, help='Password')
def get_admin_token(user, password):
    """Stores an encrypted token for the admin user.
    """
    with open(token_path_templ.format(user), "rb") as f:
        encrypted = f.read()
    decrypted_token = encrypt.decrypt_token(encrypted, password)
    term.echo(f'Stored personal access token: {decrypted_token}')



@admin.group(cls=utils.AliasedGroup)
def grant():
    """Commands for granting/revoking user permissions.
    """

@grant.command('ta')
@click.argument('user_name')
@click.option('--user', prompt=True,
              confirmation_prompt=False, help='Admin user')
@click.option('--password', prompt=True, hide_input=True,
              confirmation_prompt=False, help='Admin password')
@click.option('course', '--course', '-c', required=False, help='Course name')
@utils.crash_report
@git.gitlab_ssh_access
def grant_ta_role(user_name, user, password, course=None):
    """Grant TA permissions to a user.
    """
    update_permissions(user_name, 'ta', course, user, password)


@grant.command('prof')
@click.argument('user_name')
@click.option('--user', prompt=True,
              confirmation_prompt=False, help='Admin user')
@click.option('--password', prompt=True, hide_input=True,
              confirmation_prompt=False, help='Admin password')
@click.option('course', '--course', '-c', required=False, help='Course name')
@utils.crash_report
@git.gitlab_ssh_access
def grant_prof_role(user_name, user, password, course=None):
    """Grant course responsible permissions to a user.
    """
    update_permissions(user_name, 'prof', course, user, password)


# @grant.command('admin')
# @click.argument('user')
# @click.option('--password', prompt=True, hide_input=True,
#               confirmation_prompt=False, help='Admin password')
# @click.option('course', '--course', '-c', required=False, help='Course name')
# @utils.crash_report
# @git.gitlab_ssh_access
# def grant_admin_role(user, password, course=None):
#     """Grant admin permissions to a user.
#     """
#     update_permissions(user, 'prof', course, password)




# # Example usage:
# if __name__ == "__main__":
#     path = "admin_token.enc"
#     # First time: store_encrypted_token(path)
#     # Later use:
#     decrypted_token = load_and_decrypt_token(path)
#     print(f"Decrypted API token: {decrypted_token}")



# @click.option('--admin-password', required=False, prompt=True, hide_input=True)

# if admin_password == "expected_password":

    



# headers = {
#     "Private-Token": ADMIN_TOKEN,
#     "Content-Type": "application/json"
# }

# def add_user_to_group(group_id, user_id, access_level):
#     url = f"{GITLAB_URL}/api/v4/groups/{group_id}/members"
#     data = {
#         "user_id": user_id,
#         "access_level": access_level
#     }
#     response = requests.post(url, headers=headers, json=data)
#     return response.json()

# def add_user_to_subgroup(subgroup_id, user_id, access_level):
#     url = f"{GITLAB_URL}/api/v4/groups/{subgroup_id}/members"
#     data = {
#         "user_id": user_id,
#         "access_level": access_level
#     }
#     response = requests.post(url, headers=headers, json=data)
#     return response.json()

# def add_user_to_project(project_id, user_id, access_level):
#     url = f"{GITLAB_URL}/api/v4/projects/{project_id}/members"
#     data = {
#         "user_id": user_id,
#         "access_level": access_level
#     }
#     response = requests.post(url, headers=headers, json=data)
#     return response.json()


# perm = {
#     'No access': 0,
#     'Reporter': 20,
#     'Maintainer': 40,
#     'Owner': 50,
#     'Admin': 60
# }

# permission_levels = {
#     'ta': (perm['Reporter'], perm['Maintainer']),
#     'prof': (perm['Reporter'], perm['Owner']),
#     'admin': (perm['Admin'], perm['Admin']),
# }

# def give_permissions(group_id, subgroup_id, user_id, role):
#     """
#     Assigns TA permissions to a user in a group.
#     """
#     group_access, subgroup_access = permission_levels[role]
#     group_response = add_user_to_group(group_id, user_id, group_access)
#     print("Group response:", group_response)
#     subgroup_response = add_user_to_subgroup(subgroup_id, user_id, subgroup_access)
#     print("Subgroup response:", subgroup_response)

# # Replace these variables with your actual values
# GITLAB_URL = "https://gitlab.au.dk"
# PRIVATE_TOKEN = "your_personal_access_token"
# GROUP_ID = "your_group_id"
# SUBGROUP_ID = "your_subgroup_id"
# PROJECT_ID = "your_project_id"
# USER_ID = "user_id_to_add"
# ACCESS_LEVEL = 30  # Developer access level; see GitLab documentation for other levels


# # group_response = add_user_to_group(GROUP_ID, USER_ID, ACCESS_LEVEL)
# # print("Group response:", group_response)

# # subgroup_response = add_user_to_subgroup(SUBGROUP_ID, USER_ID, ACCESS_LEVEL)
# # print("Subgroup response:", subgroup_response)

# # project_response = add_user_to_project(PROJECT_ID, USER_ID, ACCESS_LEVEL)
# # print("Project response:", project_response)

# project_response = add_user_to_project('franklin', 'genomic-thinking', perm['Admin'])
# print("Project response:", project_response)

# ##########


# import requests

# # GitLab instance and authentication
# GITLAB_URL = "https://gitlab.example.com"
# API_TOKEN = "your_private_token"
# PROJECT_ID = 12345
# USER_ID = 67890

# # New access level
# ACCESS_LEVEL = 40  # Maintainer

# # API endpoint to update existing member
# url = f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/members/{USER_ID}"

# headers = {
#     "PRIVATE-TOKEN": API_TOKEN,
#     "Content-Type": "application/json"
# }

# payload = {
#     "access_level": ACCESS_LEVEL
# }

# # Execute request
# response = requests.put(url, headers=headers, json=payload)

# # Output response
# if response.status_code == 200:
#     print("Access level updated successfully.")
# elif response.status_code == 404:
#     print("User is not a member of the project.")
# else:
#     print(f"Error {response.status_code}: {response.json()}")


# # If you receive a 404 error, the user is not yet a member of the project. In that case, use:

# # POST /projects/:id/members to add a new user
# url = f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/members"
# response = requests.post(url, headers=headers, json={
#     "user_id": USER_ID,
#     "access_level": ACCESS_LEVEL
# })



# # https://docs.gitlab.com/ee/api/members.html#edit-a-project-member
# # https://docs.gitlab.com/ee/api/members.html#add-a-member-to-a-project-or-group



