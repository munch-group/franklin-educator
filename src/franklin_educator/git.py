"""
Core components for `PrintItStyle`
"""


import click

######################################
# new "franklin jupyter banana" command

@click.command("banana")
def _banana():

    print('hello world')


######################################
# new "franklin annanas" group

@click.group()
def annanas():

    pass

@annanas.command('xxxxxxxx')
def something():

    print('something else')

