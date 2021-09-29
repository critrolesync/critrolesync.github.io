import logging, os, collections
from time import sleep
import psycopg2
from dejavu import Dejavu
import dejavu.logic.decoder as decoder
from dejavu.logic.recognizer.file_recognizer import FileRecognizer
from .database import Database

logger = logging.getLogger(__name__)

CPU_COUNT = len(os.sched_getaffinity(0))
FORMATS = ['.mp3', '.m4a', '.opus']

class Matcher:
    _db: Database
    _dejavu: Dejavu

    def __init__(self, db=None):

        if db is None:
            db_name = 'dejavu_db'
            db_host = '127.0.0.1'
            db_user = 'root'
            db_pass = 'password'
            container_name = None
            self._db = Database(
                database_name=db_name,
                address=db_host,
                root=db_user,
                password=db_pass,
                container_name=container_name,
            )
            self._db_private = True

        else:
            self._db = db
            db_name = db._db_name
            db_host = db._db_address
            db_user = db._db_root
            db_pass = db._db_pass
            self._db_private = False

        db_config = {
            'database': {
            'host': db_host,
            'user': db_user,
            'password': db_pass,
            'database': db_name,
            },
            'database_type' : 'postgres',
        }

        while True:
            try:
                self._dejavu = Dejavu(db_config)
                break
            except psycopg2.OperationalError:
                logger.info('waiting for database to connect to the network')
                sleep(1)

    def close(self):
        if self._db_private:
            self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def fingerprint_directory(self, directory: str):
        logger.info('fingerprinting {0} with {1} thread(s)'.format(directory, CPU_COUNT))
        self._dejavu.fingerprint_directory(directory, FORMATS, CPU_COUNT)

    def fingerprint_file(self, file_path: str):
        logger.info('fingerprinting {0}'.format(file_path))

        # self._dejavu.fingerprint_file(file)

        # the version of fingerprint_file contained in dejavu is bugged, so
        # it is reimplemented here

        song_name = decoder.get_audio_name_from_path(file_path)
        song_hash = decoder.unique_hash(file_path)
        # don't refingerprint already fingerprinted files
        if song_hash in self._dejavu.songhashes_set:
            logger.info(f"{song_name} already fingerprinted, skipping")
        else:
            song_name, hashes, file_hash = Dejavu._fingerprint_worker((file_path, self._dejavu.limit))
            sid = self._dejavu.db.insert_song(song_name, file_hash, len(hashes))

            self._dejavu.db.insert_hashes(sid, hashes)
            self._dejavu.db.set_song_fingerprinted(sid)
            self._dejavu._Dejavu__load_fingerprinted_audio_hashes()

    def empty_fingerprints(self):
        self._dejavu.db.empty()
        self._dejavu._Dejavu__load_fingerprinted_audio_hashes()

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
