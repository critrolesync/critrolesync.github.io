from pathlib import Path
import logging
from critrolesync.autosync import Matcher

logging.basicConfig(level=logging.INFO)

with Matcher() as m:
    m.generate_fingerprints(Path(__file__).parent.joinpath('testdata/fingerprint'))
    m.store_fingerprints(Path(__file__).parent.joinpath('prints.tar'))

with Matcher() as m:
    m.load_fingerprints(Path(__file__).parent.joinpath('prints.tar'))
    print(m.match(Path(__file__).parent.joinpath('testdata/sample20_.mp3')))
