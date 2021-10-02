from pathlib import Path
import json

with Path(__file__).parent.joinpath('../../docs/data.json').open() as _fd:
    data = json.load(_fd)

from .download import *
from .jsonencoder import *
from .time import *
from .tools import *

# Do not import autosync here, as this will make critrolesync unimportable
# outside the Docker container or Vagrant VM, where dejavu may not be
# installed. Instead, import critrolesync.autosync as a subpackage when needed.
