import typer
from rich.console import Console
from typing_extensions import Annotated
from pathlib import Path
from enum import Enum


from rich.table import Table
from cli_helpers import center_print, left_print, prompt_user

# Im sick of dealing with pythons pkg system, Im now 
# adding to path 
#import sys
#sys.path.append('cargo_picky/')



app = typer.Typer()
console = Console()

import cargo_picky.cli.cli as cargo_cli
#from cargo_picky.cli import cli
#import go_picky.cli as go_cli
import ripbin.cli as dumpty

app.add_typer(cargo_cli.app,name='cargo')
#app.add_typer(go_cli.app, name='go')
#app.add_typer(dumpty.app, name='dumpty')



if __name__ == "__main__":
    app()
