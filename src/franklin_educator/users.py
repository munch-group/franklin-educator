import click
import subprocess
import sys
import os
from subprocess import DEVNULL, STDOUT, PIPE
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Tuple, List, Dict, Callable, Any
import requests

from franklin import config as cfg
from franklin import utils
from franklin import terminal as term
from franklin import gitlab
from franklin.logger import logger
from . import encrypt
from . import git

from rapidfuzz import process, fuzz
import unicodedata
import re



perm = {
    'No access': 0,
    'Reporter': 20,
    'Maintainer': 40,
    'Owner': 50,
    'Admin': 60
}

permission_levels = {
    'guest': (perm['Reporter'], perm['Reporter'], perm['Reporter']),
    'ta': (perm['Reporter'], perm['Maintainer'], perm['Maintainer']),
    'prof': (perm['Reporter'], perm['Owner'], perm['Owner']),
    'admin': (perm['Admin'], perm['Admin'],  perm['Admin']),
}
# mbg aliases
permission_levels['vip'] = permission_levels['prof']
permission_levels['inst'] = permission_levels['ta']



def update_group_permissions(user_id: int, group_id: int, access_level: int, api_token: str):

    members = gitlab.get_group_members(group_id, api_token)
    logger.debug('existing members', members)

    headers = {"PRIVATE-TOKEN": api_token, "Content-Type": "application/json"}
    if user_id not in members:
        logger.debug('Adding usr to group', user_id, group_id, access_level)

        url = f"https://{cfg.gitlab_domain}/api/v4/groups/{group_id}/members"
        response = requests.post(url, headers=headers, json={
            "user_id": user_id,
            "access_level": access_level
        })
        if response.status_code == 200:
            print("Member added and permissions set successfully.")
        else:
            print(f"Error {response.status_code}: {response.json()}")
    else:
        logger.debug('Updating access to group', user_id, group_id, access_level)
        
        url = f"https://{cfg.gitlab_domain}/api/v4/groups/{group_id}/members/{user_id}"
        response = requests.put(
            url, 
            headers=headers, 
            json={"access_level": access_level}
            )
        if response.status_code == 200:
            print("Access level updated successfully.")
        # elif response.status_code == 404:
        #     print("User is not a member of the project.")
        else:
            print(f"Error {response.status_code}: {response.json()}")


def update_permissions(user_name, role, course, listed_course_name, user, password, project=None):

    api_token = encrypt.get_api_token(user, password)

    user_id = gitlab.get_user_id(user_name, api_token)
    group_id = gitlab.get_group_id(cfg.gitlab_group, api_token)
    subgroup_id = gitlab.get_group_id(course, api_token)

    # term.echo(f"Updating permissions for user '{user_name}' "
    #           f"({get_user_info(user_id, api_token)['name']}) "
    #           f"with role '{role}' in course '{listed_course_name}' "
    #           f"(repo: {course}).")
    term.secho()
    term.secho(f"Granting access to")
    term.secho(f'To user:')
    term.secho(f"  {user_name} ({gitlab.get_user_info(user_id, api_token)['name']})", fg='green')
    term.secho(f'as:')
    term.secho(f"  {role}", fg='green')
    term.secho(f'for course:')
    name = f', ({listed_course_name})' if listed_course_name else ''
    term.secho(f'  {course}' + name, fg='green')
    term.secho()
    click.confirm("Do you want to continue?", abort=True, default=True)

    group_perm, subgroup_perm, project_perm = permission_levels[role]

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


# clone password repo into franklin-educator/data/passwords dir and sync that way
# call th password  repo _passwords and skip all 

# add three levels of access: admin, vip, ta


def create_impersonation_token(user_id: int, token_name: str, admin_api_token: str):

    response = requests.post(
        f"https://{cfg.gitlab_domain}/api/v4/users/{user_id}/impersonation_tokens",
        headers={
            "PRIVATE-TOKEN": admin_api_token
            },
        json= {
            "name": 'api_access_token',
            "scopes": ["api", "read_repository", "write_repository"], 
            "expires_at": "2025-12-31"  # optional
            }
    )

    if response.status_code == 201:
        token_info = response.json()
        print("Token created:")
        print(f"Token: {token_info['token']}")
        print(f"Scopes: {token_info['scopes']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


@click.group(cls=utils.AliasedGroup)
def admin():
    """Admin commands for access control.
    """


@admin.group(cls=utils.AliasedGroup)
def password():
    """Admin commands for admin tokens.
    """

# add_admin(user, password, api_token, admin, admin_password)

# set_password(user, password, admin, admin_password)

# set_token(user, password)


@password.command('set')
@click.option('--admin', prompt=True, help='User name')
@click.option('--password', prompt=True, hide_input=True, help='Password')
@click.argument("user")
def set_password(admin, admin_password, user):



    encrypt.encrypt(user, user_password, 
                    admin_passwords={
                        admin: admin_password
                        }
                    )


# @password.command('get')
# @click.option('--admin', prompt=True, help='User name')
# @click.option('--password', prompt=True, hide_input=True, help='Password')
# @click.argument("user")
# def get_password(admin, password, user):
#     """Stores an encrypted token for the user.
#     """
#     api_token = encrypt.decrypt(admin, password)
#     term.echo(f'Stored personal access token: {api_token}')



@admin.group(cls=utils.AliasedGroup)
def token():
    """Admin commands for admin tokens.
    """


@token.command('set')
@click.option('--user', prompt=True, help='User name')
@click.option('--password', prompt=True, hide_input=True, help='Password')
@click.option('--api-token', prompt=True, hide_input=True, help='User API token')
def set_token(user, password, api_token):
    """Stores an encrypted token for the user.
    """
    encrypt.encrypt(user, password, api_token, "token.json")


@token.command('get')
@click.option('--user', prompt=True, help='User name')
@click.option('--password', prompt=True, hide_input=True, help='Password')
def get_token(user, password):
    """Stores an encrypted token for the user.
    """
    api_token = encrypt.decrypt(user, password, "token.json")
    term.echo(f'Stored personal access token: {api_token}')



# password set
# password get
# password change







@admin.command('find')
@click.option('--user', prompt=True, help='User name')
@click.option('--password', prompt=True, hide_input=True, help='Password')
@click.argument("query", nargs=-1)
def find_users(query, user, password):
    """Find users in GitLab by name.
    """
    api_token = encrypt.get_api_token(user, password)
    
    users = []
    page = 1
    while True:
        response = requests.get(
            f"http://{cfg.gitlab_domain}/api/v4/users",
            headers = {"PRIVATE-TOKEN": api_token},
            params={"per_page": 100, "page": page}
        )
        data = response.json()
        if not data:
            break
        users.extend(data)
        page += 1

    # Output user info
    user_names = []
    names = []
    for user in users:
        user_names.append(user['username'])
        names.append(user['name'])

    def normalize(name):
        name = name.lower()
        name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
        name = re.sub(r"[^\w\s]", "", name)
        return name.strip()

    normalized_names = [normalize(n) for n in names]

    for q in query:
        term.echo()
        query_normalized = normalize(q)
        # match = process.extractOne(query_normalized, normalized_names, scorer=fuzz.WRatio)
#        match = process.extractOne(query_normalized, normalized_names, scorer=fuzz.WRatio, score_cutoff=90.0)
        matches = process.extract(query_normalized, normalized_names, scorer=fuzz.WRatio, score_cutoff=80.0, limit=5)
        prev = 0
        if matches:
            for match in matches:
                name, score, index = match
                # term.secho(str(round(score, 1)).ljust(4), nl=False)
                term.secho(user_names[index].ljust(9), fg='green', nl=False)
                term.secho(names[index])
                if score - prev > 1:
                    break
                prev = score
        else:
            print(f"No users found matching '{q}'")
    term.echo()


@admin.group(cls=utils.AliasedGroup)
def grant():
    """Commands for granting/revoking user permissions.
    """


@grant.command('guest')
@click.argument('user_name')
@click.option('--user', prompt=True, help='Admin user')
@click.option('--password', prompt=True, hide_input=True, help='Admin password')
@click.option('--course', '-c', required=False, help='Course name')
@crash_report
@git.gitlab_ssh_access
def grant_ta_role(user_name, user, password, course=None):
    """Grant guest permissions to a user (read only).
    """
    listed_course_name = None
    if course is None:
        course, listed_course_name = gitlab.pick_course()
    update_permissions(user_name, 'guest', course, listed_course_name, user, password)


@grant.command('ta')
@click.argument('user_name')
@click.option('--user', prompt=True, help='Admin user')
@click.option('--password', prompt=True, hide_input=True, help='Admin password')
@click.option('--course', '-c', required=False, help='Course name')
@crash_report
@git.gitlab_ssh_access
def grant_ta_role(user_name, user, password, course=None):
    """Grant TA permissions to a user.
    """
    listed_course_name = None
    if course is None:
        course, listed_course_name = gitlab.pick_course()
    update_permissions(user_name, 'ta', course, listed_course_name, user, password)


@grant.command('prof')
@click.argument('user_name')
@click.option('--user', prompt=True, help='Admin user')
@click.option('--password', prompt=True, hide_input=True, help='Admin password')
@click.option('--course', '-c', required=False, help='Course name')
@crash_report
@git.gitlab_ssh_access
def grant_prof_role(user_name, user, password, course=None):
    """Grant course responsible permissions to a user.
    """
    listed_course_name = None
    if course is None:
        course, listed_course_name = gitlab.pick_course()
    
    update_permissions(user_name, 'prof', course, listed_course_name, user, password)

# @grant.command('admin')
# @click.argument('user')
# @click.option('--password', prompt=True, hide_input=True,
#               confirmation_prompt=False, help='Admin password')
# @click.option('course', '--course', '-c', required=False, help='Course name')
# @crash_report
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



