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
from typing import Tuple, List, Dict, Callable, Any
import webbrowser
import pyperclip
import platform
from pkg_resources import iter_entry_points
from click_plugins import with_plugins
import importlib_resources

from franklin import config as cfg
from franklin import utils
from franklin import terminal as term
from franklin import logger
from franklin import gitlab
from franklin import jupyter
from franklin import docker
from franklin import update
from franklin import options
from franklin.logger import logger

def check_ssh_set_up():
    cmd = f'ssh -T git@{cfg.gitlab_domain} <<<yes'
    logger.debug(cmd)
    term.echo(f"Checking encrypted connection to GitLab")
    utils.run_cmd(cmd, check=False)
    cmd = f'ssh -T git@g{cfg.gitlab_domain}'
    logger.debug(cmd)
    cmd = f'ssh -T git@{cfg.gitlab_domain}'
    output = utils.run_cmd(cmd)
    if output.startswith('Welcome to GitLab'):
        return True
    return False


def ssh_keygen():
    """
    Generate an ssh key pair.
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
        "To allow authentication without password, you need to log into GitLab and add an ssh key to your account. When the GitLab website opens in your browser, complete the following steps:",
        '1. Sign into GitLab using the white "UNI-AD" button',
        '2. Click the "Add new key" button',
        '3. The ssh key is already copied to your clipboard. Paste it into the'
        '   "Key" text field',
        '4. In the "Expiration date" field, remove the date by clicking the small'
        '   black circle with a white x in it.',
        '5. Click the blue "Add key" button',
    ], prompt = "Press Enter to open the GitLab website.", fg='green')

    webbrowser.open('https://gitlab.au.dk/-/user_settings/ssh_keys', new=1)

    click.pause("Press Enter when you have added the ssh key to GitLab.")


def config_local_repo(repo_local_path: str) -> None:
    """
    Configures the local repository with the necessary settings for using vscode as the merge and diff tool.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository.
    """

    if utils.system() == 'Windows':
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config pull.rebase false'))
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config merge.tool vscode'))
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config mergetool.vscode.cmd "code --wait --merge $REMOTE $LOCAL $BASE $MERGED"'))
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config diff.tool vscode'))
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config difftool.vscode.cmd "code --wait --diff $LOCAL $REMOTE"'))
    else:
        subprocess.check_call(utils.fmt_cmd(f'git -C {repo_local_path} config pull.rebase false'))
        subprocess.check_call(utils.fmt_cmd(f"git -C {repo_local_path} config merge.tool vscode"))
        subprocess.check_call(utils.fmt_cmd(f"git -C {repo_local_path} config mergetool.vscode.cmd 'code --wait --merge $REMOTE $LOCAL $BASE $MERGED'"))
        subprocess.check_call(utils.fmt_cmd(f"git -C {repo_local_path} config diff.tool vscode"))
        subprocess.check_call(utils.fmt_cmd(f"git -C {repo_local_path} config difftool.vscode.cmd 'code --wait --diff $LOCAL $REMOTE'"))


def git_safe_pull(repo_local_path: str) -> bool:
    """
    Pulls changes from the remote repository and checks for merge conflicts.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository.

    Returns
    -------
    :
        True if there is a merge conflict, False otherwise.
    """

    merge_conflict = False
    try:
        # output = subprocess.check_output(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} pull')).decode()
        subprocess.run(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} diff --name-only --diff-filter=U --relative'), stdout=DEVNULL, stderr=STDOUT, check=True)
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())

        # merge conflict
        output = subprocess.check_output(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} diff --name-only --diff-filter=U --relative')).decode()

        term.echo('Changes to the following files conflict with changes to the gitlab versions of the same files:')
        term.echo(output)
        term.echo("Please resolve any conflicts and then run the command again.")
        term.echo("For more information on resolving conflicts, see:")
        term.echo("https://munch-group/franklin/git.html#resolving-conflicts", fg='blue')
        click.pause("Press Enter to launch vscode's mergetool")

        gitlab.launch_mergetool(repo_local_path)

        merge_conflict = True

    return merge_conflict


def merge_in_progress(repo_local_path: str) -> bool:
    """
    Checks if a merge is in progress.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository.

    Returns
    -------
    :
        True if a merge is in progress, False otherwise.
    """
    return os.path.exists(os.path.join(repo_local_path, '.git/MERGE_HEAD'))
    # git merge HEAD


def launch_mergetool(repo_local_path: str) -> None:
    """
    Launches vscode's mergetool.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository
    """
    try:
        output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} mergetool')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())   


def finish_any_merge_in_progress(repo_local_path):
    if merge_in_progress(repo_local_path):
        try:
            output = subprocess.check_output(utils.fmt_cmd(f'git -C repo_local_path merge --continue --no-edit')).decode()
            term.secho("Merge continued.", fg='green')
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            term.secho("You have merge conflicts. Please resolve the conflicts and then run the command again.", fg='red')
            click.pause("Press Enter to launch vscode's mergetool")
            gitlab.launch_mergetool(repo_local_path)
            return


def git_down() -> None:
    """
    "Downloads" an exercise from GitLab.
    """

    # get images for available exercises
    registry = f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}/registry/repositories'
    exercises_images = gitlab.get_registry_listing(registry)

    # pick course and exercise
    (course, _), (exercise, _) = gitlab.select_exercise(exercises_images)

    # url for cloning the repository
    repo_name = exercise.split('/')[-1]
    clone_url = f'git@gitlab.au.dk:{cfg.gitlab_group}/{course}/{repo_name}.git'
    repo_local_path = os.path.join(os.getcwd(), repo_name)
    if utils.system() == 'Windows':
        repo_local_path = PureWindowsPath(repo_local_path)

    # check if we are in an already cloned repo
    os.path.dirname(os.path.realpath(__file__))
    if os.path.basename(os.getcwd()) == repo_name and os.path.exists('.git'):
        repo_local_path = os.path.join(os.getcwd())

    # Finish any umcompleted merge
    finish_any_merge_in_progress(repo_local_path)

    # update or clone the repository
    if os.path.exists(repo_local_path):
        term.secho(f"The repository '{repo_name}' already exists at {repo_local_path}.")
        if click.confirm('\nDo you want to update the existing repository?', default=True):
            merge_conflict = git_safe_pull(repo_local_path)
            if merge_conflict:
                return
            else:
                term.secho(f"Local repository updated.", fg='green')
        else:
            raise click.Abort()
    else:
        try:
            output = subprocess.check_output(utils.fmt_cmd(f'git clone {clone_url}')).decode()
        except subprocess.CalledProcessError as e:
            term.secho(f"Failed to clone repository: {e.output.decode()}", fg='red')
            raise click.Abort()
        term.secho(f"Local repository updated.", fg='green')

    config_local_repo(repo_local_path)

    image = exercises_images[(course, exercise)]
    return image, repo_local_path



def git_up(repo_local_path: str, remove_tracked_files: bool) -> None:
    """
    "Uploads" an exercise to GitLab.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository.
    remove_tracked_files : 
        Whether to remove the tracked files after uploading
    """

    if not os.path.exists(repo_local_path):
        term.secho(f"{repo_local_path} does not exist", fg='red')
        return
    if not os.path.exists(os.path.join(repo_local_path, '.git')):
        term.secho(f"{repo_local_path} is not a git repository", fg='red')
        return

    config_local_repo(repo_local_path)

    # Fetch the latest changes from the remote repository
    output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} fetch')).decode()

    # Finish any umcompleted merge
    finish_any_merge_in_progress(repo_local_path)

    term.secho("\nChecking for changes to local files.", fg='red')

    # add
    try:
        output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} add -u')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())
        raise click.Abort()
    
    try:
        staged_changes = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} diff --cached')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())
        raise click.Abort()
    
    if staged_changes:

        # commit
        msg = click.prompt("Files changed. Enter short description of the nature of the changes made", default="an update", show_default=True)
        try:
            output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} commit -m "{msg}"')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()
        
        # pull
        # term.secho("Pulling changes from the remote repository.", fg='yellow')
        merge_conflict = git_safe_pull(repo_local_path)
        if merge_conflict:
            sys.exit(1)
        
        # push
        try:
            output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} push')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()

        term.secho(f"Changes uploaded to GitLab.", fg='yellow')
    else:
        term.secho("No changes to your local files.", fg='yellow')

    # # Check the status to see if there are any upstream changes
    # status_output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} status')).decode()
    # if "Your branch is up to date" in status_output:
    #     term.secho("No changes to upload.", fg='green')
    #     return
    # else:


    if remove_tracked_files:

        try:
            # output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} diff-index --quiet HEAD')).decode()
            output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} status')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()

        if 'nothing to commit, working tree clean' in output:
            shutil.rmtree(repo_local_path)
            term.secho("Local files removed.", fg='green')

        elif 'nothing added to commit but untracked files present' in output:

            if merge_in_progress(repo_local_path):
                term.secho("A merge is in progress. Local repository will not be removed.", fg='red')
                return

            # Instead of deleting the repository dir, we prune all tracked files and 
            # and resulting empty directories - in case there are 
            path = os.path.join(repo_local_path, 'franklin.log')
            if os.path.exists(path):
                os.remove(path)
            output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} ls-files')).decode()
            tracked_dirs = set()
            for line in output.splitlines():
                path = os.path.join(repo_local_path, *(line.split('/')))
                tracked_dirs.add(os.path.dirname(path))
                os.remove(path)
            # traverse repo bottom up and remove empty directories
            subdirs = reversed([x[0] for x in os.walk(repo_local_path) if os.path.isdir(x[0])])
            for subdir in subdirs:
                if not os.listdir(subdir) and subdir in tracked_dirs:
                    os.rmdir(subdir)
            path = os.path.join(repo_local_path, '.git')
            if os.path.exists(path):
                shutil.rmtree(path)
            if os.path.exists(repo_local_path) and not os.listdir(repo_local_path):
                os.rmdir(repo_local_path)

            term.secho(f"Local files removed.", fg='green')

        else:
            # term.secho("There are uncommitted changes. Please commit or stash them before removing local files.", fg='red')
            term.secho("There are local changes to repository files. Local repository will not be removed.", fg='red')
            return
    

def git_status() -> None:
    """Displays the status of the local repository.
    """
    pass

@with_plugins(iter_entry_points('franklin.git.plugins'))
@click.group(cls=utils.AliasedGroup)
def git():
    """GitLab commands.
    """
    pass

@git.command()
@utils.crash_report
def status():
    """Status of local repository.
    """
    git_status()

@git.command()
@utils.crash_report
def down():
    """Safely git clone or pull from the remote repository.
    
    Convenience function for adding, committing, and pushing changes to the remote repository.    
    """
    git_down()


@git.command()
@click.option('-d', '--directory', default=None)
@click.option('--remove/--no-remove', default=True, show_default=True)
@utils.crash_report
def up(directory, remove):
    """Safely add, commit, push and remove if possible.
    """
    if not check_ssh_set_up():
        ssh_keygen()
    if directory is None:
        directory = os.getcwd()
    if utils.system() == 'Windows':
        directory = PureWindowsPath(directory)
    git_up(directory, remove)

@git.command()
@utils.crash_report
def ui():
    """GitUI for interactive git
    
    Git UI for interactive staging, committing and pushing changes to the remote repository.
    """
    utils.config_gitui()

    if not check_ssh_set_up():
        ssh_keygen()

    subprocess.run(utils.fmt_cmd(f'gitui'), check=False)


@click.group(cls=utils.AliasedGroup)
def exercise():
    """Convenience command for full edit workflow.
    """


def create_repository_from_template(course, repo_name):

    repo_dir = os.path.join(tempfile.gettempdir(), repo_name)
    repo_template_files = [p.name for p in importlib_resources.files().joinpath('data/repo_templates/exercise').iterdir()]

    os.makedirs(repo_dir, exist_ok=False)
    for path in repo_template_files:
        if path.is_file():
            shutil.copy(path, os.path.join(repo_dir, path.name))
        # else:
        #     shutil.copytree(path, os.path.join(repo_dir, path.name))

    utils.run_cmd('git -C repo init --initial-branch=main')
    utils.run_cmd(f'git -C repo remote add origin git@{cfg.gitlab_domain}:{cfg.gitlab_group}/{course}/{repo_name}.git')
    utils.run_cmd('git -C repo add .')
    utils.run_cmd('git -C repo commit -m "Initial commit"')
    utils.run_cmd('git -C repo push -u origin main')

    shutil.rmtree(repo_dir)


@exercise.command('create')
@utils.crash_report
def create_exercise():
    """
    Create a new exercise repository for a course.

    Parameters
    ----------
    course : 
        Course name.
    new_repo_name : 
        Name of the new repository.
    """

    course, danish_course_name = gitlab.pick_course()

    term.echo(f"You will creating a new exercise for course:\n'{danish_course_name}'")
    click.confirm(f"Do you want to continue?", default=True)

    def validate_repo_name(name):
        return name and name[0].isalpha() and re.match(r'^[\w-]+$', str) is not None

    repo_name = None
    while not validate_repo_name(repo_name):
        repo_name = click.prompt("Enter the name of the new exercise repository. The name must start with a letter and can only contain letters, numbers, underscores and dashes:")
        if not validate_repo_name(repo_name):
            term.secho("Invalid repository name. Please try again.", fg='red')

    create_repository_from_template(course, repo_name)

    term.secho(f"Created new repository", fg='green')

    term.echo(f"The GitLab settings page will open in your browser.")
    term.echo(f'You only need to add the (brief) title of the exercise in the "Project description" field and click "save"')
    term.echo(f'(If you want to hide the exercise from students, you add "HIDDEN" to the title.)')
    term.echo('')
    term.echo('You can now use the "franklin exercise edit" command to edit the exercise.')
    time.sleep(2)

    repo_settings_gitlab_url = f'https://git@{cfg.gitlab_domain}:{cfg.gitlab_group}/{course}/{repo_name}/edit'

    webbrowser.open(repo_settings_gitlab_url, new=1)


    # ssh git@gitlab.au.dk personal_access_token GITLAB-API-TMP api,write_repository 1

    # s = requests.Session()
    # s.headers.update({'PRIVATE-TOKEN': '<token>'})
    # url = f'{GITLAB_API_URL}/projects?name={new_repo_name}&namespace_id={GITLAB_GROUP}%2F{course_name}'
    # r  = s.post(url, headers={ "Content-Type" : "application/json"})
    # if not r.ok:
    #     r.raise_for_status()
    # term.secho(f"New repository '{new_repo_name}' created for '{course_name}'.", fg='green')


@exercise.command('edit')
@utils.crash_report
def edit_cycle():
    """Edit exercise in JupyterLab

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
    utils.check_internet_connection()

    if not os.environ.get('DEVEL', None):
        update.update_client()

    utils.check_free_disk_space()

    logger.debug('Starting Docker Desktop')
    docker.failsafe_start_docker_desktop()
    time.sleep(2)

    with utils.DelayedKeyboardInterrupt():
        image_url, repo_local_path = git_down()
        jupyter.launch_jupyter(image_url, cwd=os.path.basename(repo_local_path))
        git_up(repo_local_path, remove_tracked_files=True)

        # term.secho("There was a merge conflict. Please resolve it and run 'franklin git up.", fg='red')
        

# ###########################################################
# # Group alias "exercise" the status, down and up  commands 
# # So users can do franklin exercise down / up / status
# ###########################################################

# @with_plugins(iter_entry_points('franklin.plugins'))
# @click.group(cls=utils.AliasedGroup)
# def exercise():
#     """GitLab commands.
#     """
#     pass

# @exercise.command('status')
# @utils.crash_report
# def _status():
#     """Status of local repository.
#     """
#     git_status()

# @exercise.command('down')
# @utils.crash_report
# def _down():
#     """Get local copy of exercise from GitLab
#     """
#     git_down()


# @exercise.command('up')
# @click.option('-d', '--directory', default=None)
# @click.option('--remove/--no-remove', default=True, show_default=True)
# @utils.crash_report
# def _up(directory, remove):
#     """Sync local copy or exercise to GitLab
#     """
#     if directory is None:
#         directory = os.getcwd()
#     if utils.system() == 'Windows':
#         directory = PureWindowsPath(directory)
#     git_up(directory, remove)

