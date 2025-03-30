
from typing import Tuple, List, Dict, Callable, Any

from franklin.howto import howto
from franklin import terminal as term
from franklin import utils


@howto.command("use-git")
@utils.crash_report
def _use_git():
    """
    How to use Git with Franklin.
    """

    term.echo()
    term.secho('Using Git', fg='green', center=True, width=70)

    term.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)




