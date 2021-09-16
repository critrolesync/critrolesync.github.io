import logging, os, collections
from dejavu import Dejavu
from dejavu.logic.recognizer.file_recognizer import FileRecognizer
from .database import Database

logger = logging.getLogger(__name__)

CPU_COUNT = len(os.sched_getaffinity(0))
FORMATS = ['.mp3', '.m4a']

class Matcher:
    _db: Database
    _dejavu: Dejavu

    def __init__(self):
        db_name = 'dejavu_db'
        db_host = '127.0.0.1'
        db_user = 'root'
        db_pass = 'password'
        db_config = {
            'database': {
            'host': db_host,
            'user': db_user,
            'password': db_pass,
            'database': db_name,
            },
            'database_type' : 'postgres',
        }
        self._db = Database(
            database_name=db_name,
            address=db_host,
            root=db_user,
            password=db_pass,
        )
        self._dejavu = Dejavu(db_config)

    def close(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def generate_fingerprints(self, directory: str):
        logger.info('fingerprinting {0} with {1} thread(s)'.format(directory, CPU_COUNT))
        self._dejavu.fingerprint_directory(directory, FORMATS, CPU_COUNT)

    def load_fingerprints(self, file:str):
        self._db.load(file)
        self._dejavu._Dejavu__load_fingerprinted_audio_hashes()

    def store_fingerprints(self, file:str):
        self._db.dump(file)

    def match(self, file:str):
        Result = collections.namedtuple('Result', ['name', 'offset', 'confidence'])
        matches = []

        logger.info('matching {0}'.format(file))
        result = self._dejavu.recognize(FileRecognizer, file)

        logger.info('collecting results')
        for m in result['results']:
            matches.append(Result(
                name=m['song_name'].decode('utf8'),
                offset=m['offset_seconds'],
                confidence=m['input_confidence'],
            ))

        return matches
