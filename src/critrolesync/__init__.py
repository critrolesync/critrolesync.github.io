from pathlib import Path
import json

with Path(__file__).parent.joinpath('../../docs/data.json').open() as _fd:
    data = json.load(_fd)

from .download import *
from .jsonencoder import *
from .tools import *
