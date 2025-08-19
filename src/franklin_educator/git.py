import time
import sys
import re
import tempfile
import click
import subprocess
from subprocess import DEVNULL, STDOUT, PIPE
import os
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Tuple, List, Dict, Callable, Any, Optional, Union
import webbrowser
import pyperclip
import platform
from contextlib import redirect_stderr, redirect_stdout
# import importlib_resources
from functools import wraps, partial

from franklin_cli import config as cfg
from franklin_cli import utils
from franklin_cli import terminal as term
from franklin_cli import gitlab
from franklin_cli import jupyter
from franklin_cli import docker
from franklin_cli import update
from franklin_cli import options
from franklin_cli.logger import logger, LoggerWriter
from franklin_cli import chrome
from franklin_cli import system
from franklin_cli import crash
#from . import encrypt

def check_ssh_set_up() -> bool:
    """Check if SSH connection to GitLab is properly configured.
    
    Returns
    -------
    bool
        True if SSH connection to GitLab is working, False otherwise.
    """
    cmd = f'ssh -T git@{cfg.gitlab_domain} <<<yes'
    logger.debug(cmd)
    logger.debug(f"Checking encrypted connection to GitLab")
    utils.run_cmd(cmd, check=False)
    cmd = f'ssh -T git@g{cfg.gitlab_domain}'
    logger.debug(cmd)
    cmd = f'ssh -T git@{cfg.gitlab_domain}'
    output = utils.run_cmd(cmd)
    if output.startswith('Welcome to GitLab'):
        return True
    return False


def ssh_keygen() -> None:
    """Generate an SSH key pair and guide user through adding it to GitLab.
    
    Creates an RSA SSH key pair if it doesn't exist, copies the public key
    to clipboard, displays instructions for adding it to GitLab, and opens
    the GitLab SSH keys page in a browser.
    
    Raises
    ------
    FileNotFoundError
        If SSH key generation fails or key files cannot be read.
    """
    path = Path.home() / '.ssh/id_rsa'
    if platform.system() == 'Windows':
        path = PureWindowsPath(path)
        
    if not path.exists():
        logger.debug(f"Generating ssh key pair at {path}")
        utils.run_cmd(f"ssh-keygen -q -t rsa -N '' -f {path} <<<y")

    with open(path.with_suffix('.pub')) as f:
        public_key = f.read()
    pyperclip.copy(public_key)

    term.boxed_text("Add ssh key to GitLab", lines = [
        "To allow authentication without password, you need to log into "
        "GitLab and add an ssh key to your account. When the GitLab website "
        "opens in your browser, complete the following steps:",
        '1. Sign into GitLab using the white "UNI-AD" button',
        '2. Click the "Add new key" button',
        '3. The ssh key is already copied to your clipboard. Paste it into the'
        '   "Key" text field',
        '4. In the "Expiration date" field, remove the date by clicking'
        ' the small'
        '   black circle with a white x in it.',
        '5. Click the blue "Add key" button',
    ], prompt = "Press Enter to open the GitLab website.", fg='green')

    webbrowser.open(f'https://{cfg.gitlab_domain}/-/user_settings/ssh_keys', new=1)

    click.pause("Press Enter when you have added the ssh key to GitLab.")


def gitlab_ssh_access(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for functions that require SSH access to GitLab.

    Parameters
    ----------
    func : Callable[..., Any]
        Function that requires SSH access to GitLab.

    Returns
    -------
    Callable[..., Any]
        Decorated function that ensures SSH access is configured.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not check_ssh_set_up():
            ssh_keygen()
        return func(*args, **kwargs)
    return wrapper


def _git_cmd(cmd: str, path: Optional[Union[str, Path]] = None, commands: bool = False) -> None:
    """Execute a git command with optional path and command display.
    
    Parameters
    ----------
    cmd : str
        Git command to execute.
    path : Optional[Union[str, Path]], optional
        Path to repository directory. If provided, command will be executed
        in this directory using git -C option.
    commands : bool, optional
        Whether to display the command being executed, by default False.
        
    Raises
    ------
    subprocess.CalledProcessError
        If git command fails.
    AssertionError
        If path is provided but cmd already contains -C option, or if
        cmd doesn't start with 'git '.
    """


   
    if path is not None:
        assert '-C' not in cmd 
        # if system.system() == 'Windows':
        #     path = PurePosixPath(path)
        # else:
        #     path = Path(path)
        path = Path(path)
        try:
            # make the path sorter for cosmetic reasons if possible
            path = path.relative_to(os.getcwd())
        except ValueError:
            # don't bother
            pass
        # cmd = cmd.replace('git', f'git -C {path}')
        assert cmd[:4] == 'git '
        cmd = f'git -C "{path}" ' + cmd[4:]
    if commands:
        term.secho(f"  {cmd}", fg='blue', nowrap=True)

    p = subprocess.run(utils.fmt_cmd(cmd), 
                    stdout=PIPE, stderr=STDOUT, check=True)

    if p.stdout:
        output = p.stdout.decode()
        if output:
            logger.debug(output)
#    subprocess.check_call(utils.fmt_cmd(cmd))


def config_local_repo(repo_local_path: str, commands: bool = False) -> None:
    """Configure local repository with VS Code as merge and diff tool.

    Parameters
    ----------
    repo_local_path : str
        Path to the local repository.
    commands : bool, optional
        Whether to display git commands being executed, by default False.
        
    Raises
    ------
    subprocess.CalledProcessError
        If git configuration commands fail.
    """
    git_cmd = partial(_git_cmd, commands=commands)

    output = utils.run_cmd(f'git -C "{repo_local_path}" config --local -l')
    local_git_config = {}
    for line in output.splitlines():
        key, val = line.split('=')
        local_git_config[key] = val

    config = (
        ('pull.rebase', 
            'false'),
        ('merge.tool', 
            'vscode'),
        ('mergetool.vscode.cmd', 
            "'code --wait --merge $REMOTE $LOCAL $BASE $MERGED'"),
        ('diff.tool', 
            'vscode'),
        ('difftool.vscode.cmd', 
            "'code --wait --diff $LOCAL $REMOTE'"),
    )
    for key, val in config:
        if key not in local_git_config or local_git_config[key] != val:
            git_cmd(f'git config --local {key} {val}', repo_local_path)


def git_safe_pull(repo_local_path: str) -> bool:
    """Pull changes from remote repository and check for merge conflicts.

    Parameters
    ----------
    repo_local_path : str
        Path to the local repository.

    Returns
    -------
    bool
        True if there is a merge conflict, False otherwise.
        
    Raises
    ------
    subprocess.CalledProcessError
        If git commands fail.
    """

    merge_conflict = False
    posix = PurePosixPath(repo_local_path)
    cmd = f'git -C "{posix}" diff --name-only --diff-filter=U --relative'
    try:
        subprocess.run(
            utils.fmt_cmd(
                cmd), stdout=DEVNULL, stderr=STDOUT, check=True)
    except subprocess.CalledProcessError as e:        
#        print(e.output.decode())

        # merge conflict
        output = subprocess.check_output(utils.fmt_cmd(cmd)).decode()

        term.echo('Changes to the following files conflict with changes to '
                  'the gitlab versions of the same files:')
        term.echo(output)
        term.echo("Please resolve any conflicts and then run the "
                  "command again.")
        term.echo("For more information on resolving conflicts, see:")
        term.echo("https://munch-group/franklin/git.html#resolving-conflicts", 
                  fg='blue')
        click.pause("Press Enter to launch vscode's mergetool")

        gitlab.launch_mergetool(repo_local_path)

        merge_conflict = True

    return merge_conflict


def merge_in_progress(repo_local_path: str) -> bool:
    """Check if a git merge is currently in progress.

    Parameters
    ----------
    repo_local_path : str
        Path to the local repository.

    Returns
    -------
    bool
        True if a merge is in progress, False otherwise.
    """
    return os.path.exists(os.path.join(repo_local_path, '.git/MERGE_HEAD'))


def config_gitui() -> None:
    """Copy gitui configuration files to user's config directory.
    
    Copies gitui configuration files from the franklin_admin package
    data directory to the user's home .gitui directory.
    
    Raises
    ------
    OSError
        If directory creation or file copying fails.
    """
    path = str(Path.home() / '.gitui')
    package_data_dir = os.path.dirname(
        sys.modules['franklin_admin'].__file__) + '/data/gitui'

    if not os.path.exists(path):
        os.makedirs(path)       
    for file in Path(package_data_dir).glob('*'):
        logger.debug(f'Copying {file} to {path}')
        shutil.copy(file, path)


@options.git_commands 
def launch_mergetool(repo_local_path: str, commands: bool = False) -> None:
    """Launch VS Code's merge tool for resolving conflicts.

    Parameters
    ----------
    repo_local_path : str
        Path to the local repository.
    commands : bool, optional
        Whether to display git commands being executed, by default False.
        
    Raises
    ------
    subprocess.CalledProcessError
        If git mergetool command fails.
    """
    git_cmd = partial(_git_cmd, commands=commands)
    try:
        git_cmd('git mergetool', repo_local_path)
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())   
   

@options.git_commands
def finish_any_merge_in_progress(repo_local_path: str, 
                                 commands: bool = False) -> None:
    """Complete any ongoing git merge process.
    
    Parameters
    ----------
    repo_local_path : str
        Path to the local repository.
    commands : bool, optional
        Whether to display git commands being executed, by default False.
        
    Raises
    ------
    subprocess.CalledProcessError
        If git merge continue command fails.
    """
    git_cmd = partial(_git_cmd, commands=commands)
    if merge_in_progress(repo_local_path):
        try:
            git_cmd('git merge --continue --no-edit', repo_local_path)
            term.secho("Merge continued.", fg='green')
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            term.secho("You have merge conflicts. Please resolve the "
                       "conflicts and then run the command again.", fg='red')
            click.pause("Press Enter to launch vscode's mergetool")
            gitlab.launch_mergetool(repo_local_path)
            return


@options.git_commands
@gitlab_ssh_access
def git_down(commands: bool = False, only_with_image: bool = False) -> Tuple[Optional[str], str]:
    """Download an exercise repository from GitLab.
    
    Parameters
    ----------
    commands : bool, optional
        Whether to display git commands being executed, by default False.
    only_with_image : bool, optional
        If True, only show exercises that have Docker images available,
        by default False.
        
    Returns
    -------
    Tuple[Optional[str], str]
        Tuple containing (image_url, repo_local_path). If only_with_image
        is False, image_url will be None.
        
    Raises
    ------
    subprocess.CalledProcessError
        If git clone or pull operations fail.
    click.Abort
        If user cancels operation or SSH key has expired.
    """

    git_cmd = partial(_git_cmd, commands=commands)

    if only_with_image:
        # get images for available exercises
        url = \
            f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}/registry/repositories'
        exercises_images = gitlab.get_registry_listing(url)

        # pick course and exercise
        (course, _), (exercise, _) = gitlab.select_exercise(exercises_images)
    else:
        # pick course and exercise
        (course, _), (exercise, _) = gitlab.select_exercise()
        
    # url for cloning the repository
    repo_name = exercise.split('/')[-1]
    clone_url = f'git@{cfg.gitlab_domain}:{cfg.gitlab_group}/{course}/{repo_name}.git'
    repo_local_path = os.path.join(os.getcwd(), repo_name)

    # check if we are in an already cloned repo
    os.path.dirname(os.path.realpath(__file__))
    if os.path.basename(os.getcwd()) == repo_name and os.path.exists('.git'):
        repo_local_path = os.path.join(os.getcwd())

    # Finish any umcompleted merge
    finish_any_merge_in_progress(repo_local_path)

    # update or clone the repository
    if os.path.exists(repo_local_path):
        term.secho(f"The repository '{os.path.abspath(repo_local_path)}' already exists "
                   f"at {repo_local_path}.")
        if click.confirm('\nDo you want to update the existing repository?', 
                         default=True):
            merge_conflict = git_safe_pull(repo_local_path)
            if merge_conflict:
                return
            else:
                term.echo()
                term.secho(f"Local repository updated.")
        else:
            raise click.Abort()
    else:
        try:
            git_cmd(f'git clone {clone_url}')
        except subprocess.CalledProcessError as e:
            output = e.output.decode()
            term.secho(f"Cloning of repository failed:\n{output}", 
                       fg='red')
            if 'Your SSH key has expired' in output:
                term.secho("The SSH key for your GitLab account has expired. "
                           "See the documentation for how to register your "
                           "SSH key again")
                term.secho(f'{cfg.documentation_url}/pages/about/ssh.html',
                            fg='blue')
            raise click.Abort()
        term.echo()        
        term.secho(f"Cloned repository to {repo_local_path}.")

    config_local_repo(repo_local_path)

    if only_with_image:
        image = exercises_images[(course, exercise)]
        return image, repo_local_path
    else:
        return None, repo_local_path
    

@click.command()
@click.option('--admin-password', prompt=True, hide_input=True,
              confirmation_prompt=False, help='Admin password')
def main(admin_password: str) -> None:
    """Main command for admin password verification.
    
    Parameters
    ----------
    admin_password : str
        Admin password to verify.
    """
    # Use the password in your logic
    if admin_password == "expected_password":
        click.echo("Access granted.")
    else:
        click.echo("Access denied.")


@gitlab_ssh_access
def git_up(repo_local_path: str, remove_tracked_files: bool) -> None:
    """Upload exercise changes to GitLab.

    Parameters
    ----------
    repo_local_path : str
        Path to the local repository.
    remove_tracked_files : bool
        Whether to remove tracked files after uploading.
        
    Raises
    ------
    subprocess.CalledProcessError
        If git operations (add, commit, push) fail.
    click.Abort
        If user cancels operation or if repository operations fail.
    PermissionError
        If local files cannot be removed when remove_tracked_files is True.
    """

    if not os.path.exists(repo_local_path):
        term.secho(f"{repo_local_path} does not exist", fg='red')
        return
    if not os.path.exists(os.path.join(repo_local_path, '.git')):
        term.secho(f"{repo_local_path} is not a git repository", fg='red')
        return

    config_local_repo(repo_local_path)

    # Fetch the latest changes from the remote repository
    output = subprocess.check_output(
        utils.fmt_cmd(f'git -C "{repo_local_path}" fetch')).decode()

    # Finish any umcompleted merge
    finish_any_merge_in_progress(repo_local_path)

#    term.secho("Inspecting file changes")

    # add
    try:
        output = subprocess.check_output(
            utils.fmt_cmd(f'git -C "{repo_local_path}" add -u')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())
        raise click.Abort()
    
    try:
        staged_changes = subprocess.check_output(
           utils.fmt_cmd(f'git -C "{repo_local_path}" diff --cached')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())
        raise click.Abort()
    
    if staged_changes:

        # commit
        term.echo("Your exercise files changed")
        term.echo("Enter *short* description of the nature of the '" \
        "'changes made:", fg='green')        
        msg = click.prompt("Description", default="Exercise update",
                           show_default=True)
        try:
            output = subprocess.check_output(
                utils.fmt_cmd(
                    f'git -C "{repo_local_path}" commit -m "{msg}"')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()
        
        # pull
        merge_conflict = git_safe_pull(repo_local_path)
        if merge_conflict:
            sys.exit(1)
        
        # push
        try:
            output = subprocess.check_output(
                utils.fmt_cmd(f'git -C "{repo_local_path}" push')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()

        term.secho(f"Changes uploaded to GitLab.")
    else:
        term.secho("No changes to your local files.")

    if remove_tracked_files:

        try:
            output = subprocess.check_output(
                utils.fmt_cmd(
                    f'git -C "{repo_local_path}" status')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()

        if 'nothing to commit, working tree clean' in output:
            try:
                utils.rmtree(repo_local_path)
                term.secho("Local files removed.")
            except PermissionError as e:
                term.secho("You can remove the lo   cal files.")

        elif 'nothing added to commit but untracked files present' in output:

            if merge_in_progress(repo_local_path):
                term.secho("A merge is in progress. Local repository will"
                           " not be removed.", fg='red')
                return

            # Instead of deleting the repository dir, we prune all tracked files and 
            # and resulting empty directories - in case there are 
            path = os.path.join(repo_local_path, 'franklin.log')
            if os.path.exists(path):
                os.remove(path)
            output = subprocess.check_output(
                utils.fmt_cmd(
                    f'git -C "{repo_local_path}" ls-files')).decode()
            tracked_dirs = set()
            for line in output.splitlines():
                path = os.path.join(repo_local_path, *(line.split('/')))
                tracked_dirs.add(os.path.dirname(path))
                os.remove(path)
            # traverse repo bottom up and remove empty directories
            subdirs = \
                [x[0] for x in os.walk(repo_local_path) if os.path.isdir(x[0])]
            for subdir in reversed(subdirs):
                if not os.listdir(subdir) and subdir in tracked_dirs:
                    os.rmdir(subdir)
            path = os.path.join(repo_local_path, '.git')
            if os.path.exists(path):
                utils.rmtree(path)
            if os.path.exists(repo_local_path) \
                and not os.listdir(repo_local_path):
                os.rmdir(repo_local_path)

            term.secho(f"Local files removed.")

        else:
            term.secho("There are local changes to repository files. Local "
                       "repository will not be removed.", fg='red')
            return
    

@gitlab_ssh_access
def git_status() -> None:
    """Display the status of the local repository.
    
    Currently a placeholder function that performs no operations.
    """
    pass


@click.group(cls=utils.AliasedGroup)
def exercise() -> None:
    """Commands for managing exercises.
    
    This group contains subcommands for creating, editing, cloning,
    and managing exercise repositories.
    """


# @exercise.command()
# @crash.crash_report
# def status():
#     """Sync status of retrieved exercise.
#     """
#     if not os.path.exists('.git'):
#         term.secho(f"To use this command, you must be in the folder "
#                    f"of a retrieve exercise.", fg='red')
#         click.Abort()
#     git_status()



@crash.crash_report
@options.git_commands
@exercise.command(hidden=True)
@gitlab_ssh_access
def clone(commands: bool = False) -> None:
    """Clone an exercise git repository to local machine.
    
    Parameters
    ----------
    commands : bool, optional
        Whether to display git commands being executed, by default False.
        
    Raises
    ------
    subprocess.CalledProcessError
        If git clone operation fails.
    click.Abort
        If repository already exists.
    """
    url = \
        f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}/registry/repositories'
    # exercises_images = gitlab.get_registry_listing(url)
    (course, _), (exercise, _) = gitlab.select_exercise()
    if os.path.exists(exercise):
        term.secho(f"The exercise repository '{exercise}' already exists "
                   f"at {os.path.abspath(exercise)}.", fg='red')
        raise click.Abort()

    clone_url = f'git@{cfg.gitlab_domain}:franklin/{course}/{exercise}.git'
    _git_cmd(f'git clone {clone_url}', commands=commands)
    term.echo()
    term.secho(f"Exercise repository cloned to folder: {os.path.abspath(exercise)}", fg='green')
    term.echo()


@crash.crash_report
@exercise.command(hidden=True)
@gitlab_ssh_access
def down() -> None:
    """Retrieve exercise from GitLab.
    
    Downloads an exercise repository from GitLab by calling git_down().
    """
    git_down()


@crash.crash_report
# @click.option('-d', '--directory', default=None)
@click.argument('directory', default=None, type=click.Path(exists=True))
@click.option('--remove/--no-remove', default=True, show_default=True)
@exercise.command(hidden=True)
@gitlab_ssh_access
def up(directory: Optional[str], remove: bool) -> None:
    """Upload retrieved exercise to GitLab.
    
    Parameters
    ----------
    directory : Optional[str]
        Directory containing the exercise repository. If None, uses current directory.
    remove : bool
        Whether to remove local files after upload.
        
    Raises
    ------
    click.Abort
        If not in a git repository directory.
    """
    if directory is None:
        directory = os.getcwd()
    if system.system() == 'Windows':
        directory = PureWindowsPath(directory)
    if not os.path.exists('.git'):
        term.secho(f"To use this command, you must be in the folder of a "
                   "retrieve exercise.", fg='red')
        click.Abort()
    git_up(directory, remove)


@exercise.command()
@crash.crash_report
@gitlab_ssh_access
def gitui() -> None:
    """Launch terminal git GUI (gitui).
    
    Configures gitui and launches it with SSH agent for GitLab access.
    """
    config_gitui()
    # config_file = Path.home() / '.gitui/theme.ron'
    rsa_file = Path.home() / '.ssh/id_rsa'
    # cmd = f"eval $(ssh-agent) && ssh-add {rsa_file} && gitui -t {config_file}"
    cmd = f"eval $(ssh-agent) && ssh-add {rsa_file} && gitui"
    logger.debug(f"Launching gitui with command: {cmd}")
    subprocess.run(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
    # subprocess.check_output(cmd, shell=True)

# $HOME/.config/gitui/key_bindings.ron (mac)
# $XDG_CONFIG_HOME/gitui/key_bindings.ron (linux using XDG)
# $HOME/.config/gitui/key_bindings.ron (linux)
# %APPDATA%/gitui/key_bindings.ron (Windows)


@options.git_commands
def create_repository_from_template(course: str, repo_name: str, api_token: str, commands: bool = False) -> None:
    """Create a new repository from the exercise template.
    
    Parameters
    ----------
    course : str
        Course name where the repository will be created.
    repo_name : str
        Name of the new repository.
    api_token : str
        GitLab API token for authentication.
    commands : bool, optional
        Whether to display git commands being executed, by default False.
        
    Raises
    ------
    subprocess.CalledProcessError
        If git operations fail.
    OSError
        If template directory copying fails.
    """

    git_cmd = partial(_git_cmd, commands=commands)

    repo_dir = os.path.join(tempfile.gettempdir(), repo_name)
    # if os.path.exists(repo_dir):
    #     shutil.rmtree(repo_dir)

    # repo_template_files = [
    #     p for p in (importlib_resources.files()
    #     .joinpath('data/repo_templates/exercise')
    #     .iterdir())
    #     ]

    # template files are stored in franklin because we need them there too
    template_dir = Path(os.path.dirname(sys.modules['franklin'].__file__)) / 'data' / 'templates' / 'exercise'
    shutil.copytree(template_dir, repo_dir, dirs_exist_ok=True)

    # os.makedirs(repo_dir, exist_ok=False)
    # for path in repo_template_files:
    #     path = Path(path)        
    #     if path.is_file():
    #         logger.debug(f"Copying {path} to {repo_dir}")
    #         shutil.copy(path, repo_dir)

    remote = \
        f'git@{cfg.gitlab_domain}:{cfg.gitlab_group}/{course}/{repo_name}.git'

    git_cmd(f'git init --initial-branch=main', repo_dir)
    git_cmd(f'git add .', repo_dir)
    git_cmd(f'git commit -m "Initial commit"', repo_dir)

#    gitlab.create_public_gitlab_project(repo_name, course, api_token)

    git_cmd(f'git remote add origin {remote}', repo_dir)
    git_cmd(f'git push -u origin main', repo_dir)

    #shutil.rmtree(repo_dir)


def repository_exists(course: str, repo_name: str) -> bool:
    """Check if a repository exists on GitLab.
    
    Parameters
    ----------
    course : str
        Course name containing the repository.
    repo_name : str
        Name of the repository to check.
        
    Returns
    -------
    bool
        True if repository exists, False otherwise.
        
    Raises
    ------
    subprocess.TimeoutExpired
        If git ls-remote command times out.
    """
    remote = \
        f'git@{cfg.gitlab_domain}:{cfg.gitlab_group}/{course}/{repo_name}.git'
    try:        
        cmd = f'git ls-remote --exit-code {remote}'
        logger.debug(f"Checking if repository {remote} exists")
        logger.debug(cmd)
        # Use subprocess.run to check if the repository exists
        p = subprocess.run(utils.fmt_cmd(cmd), check=False, 
                           capture_output=True, timeout=3)
        return p.returncode == 0
    except subprocess.TimeoutExpired as e:
        return False


# @click.option('--user', default=None, required=False, prompt=True,)
# @click.option('--password', default=None, required=False, prompt=True, hidden=True)
@click.option('--course', default=None)
@click.option('--new-repo-name', default=None)
@exercise.command('new')
@crash.crash_report
@gitlab_ssh_access
def create_exercise(course: Optional[str] = None, 
                    # user: str = None, password: str = None,
                     new_repo_name: Optional[str] = None) -> None:
    """Create a new exercise repository for a course.

    Parameters
    ----------
    course : Optional[str], optional
        Course name. If None, user will be prompted to select from available courses.
    new_repo_name : Optional[str], optional
        Name of the new repository. If None, user will be prompted to enter one.
        
    Raises
    ------
    click.Abort
        If user cancels operation, repository name is invalid, or repository
        already exists.
    """

    # api_token = encrypt.get_api_token(user, password)
    api_token = cfg.gitlab_token

    if course is None:
        course, danish_course_name = gitlab.pick_course()

    term.echo()
    term.secho(f"You will creating a new exercise for:", fg='green', nl=False)
    term.secho(f" {danish_course_name}", bold=True)
    click.confirm(f"Do you want to continue?", default=True)

    def validate_repo_name(name):
        return name and name[0].isalpha() \
            and re.match(r'^[\w-]+$', name) is not None

    term.echo()
    term.echo("Enter a short descriptive label for the new exercise "
                "repository.", fg='green')
    term.echo()
    term.echo(" - It must begin with a letter.")
    term.echo(" - Only use lowercase letters, numbers, underscores, "
              "and dashes.")
    term.echo("")

    for _ in range(10):
        name_valid, name_avail = False, False
        new_repo_name = click.prompt("Repository name")
        if validate_repo_name(new_repo_name):
            name_valid = True
        else:
            term.secho("Invalid name. Read restrictions above and try again.", 
                       fg='red')
            continue
        if repository_exists(course, new_repo_name):
            term.echo()
            term.secho("An exercise with that name already exists. "
                       "Please try another name.")
            term.echo()
            continue
        else:
            name_avail = True
        if name_valid and name_avail:
            break
    else:
        click.Abort()

    create_repository_from_template(course, new_repo_name, api_token)

    term.echo('')
    term.secho(f'The exercise is being created and will be available through'
               'Franklin in about 10 minutes.')

    term.echo('')
    # term.boxed_text("The Last step is to add the Danish name of the exercise"
    #                 " name shown in franklin's' menu", 
    #                 lines=[
    #                     'On the GitLab settings page for the exercise, '
    #                     'add the (brief) Danish title of the exercise in the '
    #                     '"Project description" text box.',
    #                     '',
    #                     'If you want to hide the exercise from students, '
    #                     'just add the word HIDDEN',
    #                     ''
    #                     'Remember to to click "Save changes"!'
    #                 ], fg='green')
    term.boxed_text("The final steps", 
                    lines=[
                        'The last steps take need to be cond in the '
                        'GitLab Uer Interface. If you are prompted for login, '
                        'just click teh UNI-AD button. You need to:',  
                        '',
                        '1. Add the (brief) Danish title of the exercise. You fill '
                        'that into the "Project description" text box. '
                        'If you want to hide the exercise from students, '
                        'just add the word HIDDEN to the name',
                        '',
                        '2. Click "Save changes".',                        
                        '',
                        '3. Make the repository public. To do that, you '
                        'click where it says "Visibility, project features, '
                        'permissions" and change Project visibility from '
                        '"Private" to "Public."',
                        '',
                        '4. Click "Save changes".',
                        '',
                        '5. Close the browser window.',
                    ], fg='green', subsequent_indent='   ')
    

    # term.secho(f"Last step is to add the exercise name visible to students:", 
    #            fg='green')
    # term.echo('')
    # term.echo(f'On the GitLab settings page for the exercise, '
    #           'add the (brief) Danish title of the exercise in the '
    #           '"Project description" field.\n\nIf you want to hide the exercise '
    #           'from students, just add the word HIDDEN')
    # term.echo('Remember to to click "Save changes"!')
    term.echo('')
    click.pause(f"Press enter to open the exercise settings page")

    repo_settings_gitlab_url = \
    f'https://{cfg.gitlab_domain}/{cfg.gitlab_group}/{course}/{new_repo_name}/edit'

    repo_pipelines_gitlab_url = \
    f'https://{cfg.gitlab_domain}/{cfg.gitlab_group}/{course}/{new_repo_name}/edit'

    term.echo()
    term.echo('Settings page: ', nl=False)
    term.secho(repo_settings_gitlab_url, nowrap=True, fg='blue')

    # webbrowser.open(repo_settings_gitlab_url, new=1)
    with redirect_stdout(LoggerWriter(logger.debug)):
        with redirect_stderr(LoggerWriter(logger.debug)):
            chrome.chrome_open_and_wait(repo_settings_gitlab_url)

    visibility = gitlab.get_project_visibility(
        course, new_repo_name, api_token)
    if visibility != 'public':
        term.secho("The exercise was not made public. You need to make it public "
                   "to be able to use it with Franklin. Please follow the instructions above", fg='red')
        term.echo()
        click.pause(f"Press enter to open the exercise settings page")
        webbrowser.open(repo_settings_gitlab_url, new=1)
        return
    
    term.echo()
    term.secho("Exercise created successfully", fg='green')

    term.echo()
    term.echo('Next steps:', bold=True)
    term.echo()
    term.echo(' - The Docker image is being built. '
              'You can monitor the process from this page:', 
              subsequent_indent='   ')
    term.secho(repo_settings_gitlab_url, nowrap=True, fg='blue', 
               initial_indent='   ')
    term.echo()
    term.secho(' - Once it is ready, you can use the "franklin exercise edit" '
               'command to develop the exercise.', 
               subsequent_indent='   ')
    term.echo()
    term.secho(' - If you know your way around git and vscode, you can '
               'clone it right away using "franklin exercise clone"', 
               subsequent_indent='   ')
    term.echo()


# ssh git@gitlab.au.dk personal_access_token GITLAB-API-TMP api,write_repository 1

    # s = requests.Session()
    # s.headers.update({'PRIVATE-TOKEN': '<token>'})
    # url = f'{GITLAB_API_URL}/projects?name={new_repo_name}'
    # f'&namespace_id={GITLAB_GROUP}%2F{course_name}'
    # r  = s.post(url, headers={ "Content-Type" : "application/json"})
    # if not r.ok:
    #     r.raise_for_status()
    # term.secho(f"New repository '{new_repo_name}' created for"
    #            " '{course_name}'.", fg='green')


@exercise.command("settings")
@click.option('--course', default=None)
@click.option('--exercise', default=None)
@crash.crash_report
@gitlab_ssh_access
def open_gitlab_repo_settings(course: Optional[str] = None, exercise: Optional[str] = None) -> None:
    """Open GitLab settings page for an exercise repository.

    Parameters
    ----------
    course : Optional[str], optional
        Course name. If None, user will be prompted to select from available courses.
    exercise : Optional[str], optional
        Exercise name. If None, user will be prompted to select from available exercises.
        
    Raises
    ------
    click.Abort
        If user cancels operation or if exercise is specified without course.
    """

    if course is None and exercise is not None:
        term.secho(f"If you specify exercise you also need to specify course")
        click.Abort()

    danish_course_name = None 
    if course is None:
        course, danish_course_name = gitlab.pick_course()
    if exercise is None:
        exercise, listed_exercise_name = gitlab.pick_exercise(course, danish_course_name)

    term.boxed_text("Exercise settings",
                    lines=[
                        'The GitLab settings page will open in Chrome.',
                        '',
                        '- To change the exercise title listed by franklin, '
                        'you change the text in the "Project description" '
                        'box. You can hide the exercise from students by '
                        'adding the word HIDDEN to the title in '
                        '"Project description" box. Remember to to click '
                        '"Save changes".',
                        '',
                        '- To add another educator to the course, choose '
                        'Manage > Members in the sidebar. On the '
                        '"Project members" pate, you click the blue '
                        '"Invite members" button. In the '
                        '"Select maximum role" dropdown, choose "Owner" '
                        'for other professors and "Maintainer" for TAs',
                        '',                        
                        'Remember to to click "Save changes"!'
                    ], fg='green', subsequent_indent='   ')
    term.echo('')
    click.pause(f"Press enter to open GitLab page.")

    repo_settings_gitlab_url = \
    f'https://{cfg.gitlab_domain}/{cfg.gitlab_group}/{course}/{exercise}/edit'

    term.secho(repo_settings_gitlab_url, nowrap=True, fg='blue')
    webbrowser.open(repo_settings_gitlab_url, new=1)

import signal

class EditCycleKeyboardInterrupt:
    """Context manager to handle KeyboardInterrupt during edit cycle.
    
    Suppresses KeyboardInterrupt signals and displays a warning message
    to prevent users from interrupting the edit workflow which could
    result in data loss.
    
    Attributes
    ----------
    signal_received : Union[bool, Tuple[int, Any]]
        Flag indicating if SIGINT was received. False by default,
        or tuple of (signal, frame) if signal was caught.
    old_handler : Callable
        Original signal handler to restore on exit.
    """
    def __enter__(self) -> 'EditCycleKeyboardInterrupt':
        """Enter the context manager and set up signal handling.
        
        Returns
        -------
        EditCycleKeyboardInterrupt
            Self instance.
        """
        self.signal_received = False
        self.old_handler = signal.signal(signal.SIGINT, self.handler)
        return self
                
    def handler(self, sig: int, frame: Any) -> None:
        """Handle SIGINT signal during edit cycle.
        
        Parameters
        ----------
        sig : int
            Signal number.
        frame : Any
            Current stack frame.
        """
        self.signal_received = (sig, frame)
        # logging.debug('SIGINT received. Delaying KeyboardInterrupt.')
        term.boxed_text("Do not interrupt this workflow",
                        ['Your changes are only saved when the workflow is '''
                        ' completed'], fg='red'
                        )

    def __exit__(self, exc_type: Optional[type], exc_value: Optional[Exception], traceback: Optional[Any]) -> None:
        """Exit the context manager and restore original signal handler.
        
        Parameters
        ----------
        exc_type : Optional[type]
            Exception type if an exception was raised.
        exc_value : Optional[Exception]
            Exception value if an exception was raised.
        traceback : Optional[Any]
            Traceback if an exception was raised.
        """
        signal.signal(signal.SIGINT, self.old_handler)



@options.git_commands
@exercise.command('edit')
@crash.crash_report
@gitlab_ssh_access
def edit_cycle(commands: bool = False) -> None:
    """Edit exercise in jupyter

    The command runs a full cycle of downloading the exercise from GitLab,
    launching JupyterLab, and uploading changes back to GitLab. To avoid
    merge conflicts, and loss of work, the cycle must be completed once stated.

    The workflow goes through the following steps:

    \b
    1. Clone the exercise from GitLab.
    2. Download the exercise docker image.
    3. Start the docker container.
    4. Launch Jupyter in the local repository folder.
    5. [The user can now edit the exercise in JupyterLab]
    6. When Jupyter is shut down (by pressing Q), modified files 
       will be added to git.
    7. The user is prompted for a commit message to label the set of 
       changes made.
    8. Changes are committed and pushed to GiLab, where a new version
       of the exercise docker image is generated.
    9. The local repository is removed to avoid future merge conflicts.

    NB: Problems may arise if an exercise has more than one ongoing/incomplete 
    edit-cycle at the same time. The best way to avoid this is to complete
    each edit-cycle in one sitting.
    """

    git_cmd = partial(_git_cmd, commands=commands)

    system.check_internet_connection()

    update.update_packages()

    system.check_free_disk_space()

    docker.failsafe_start_desktop()
    time.sleep(2)

    with EditCycleKeyboardInterrupt():

        image_url, repo_local_path = git_down(only_with_image=True)

        jupyter.launch_jupyter(image_url, 
                               cwd=os.path.basename(repo_local_path))

        git_up(repo_local_path, remove_tracked_files=True)

        term.secho("Any changes have been saved to GitLab and will be "
                   "available in a few minutes")

        sys.exit(0)
        
