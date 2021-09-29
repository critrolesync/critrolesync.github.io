import docker, logging, io, shutil
from pathlib import Path
from typing import Any
from time import sleep

logger = logging.getLogger(__name__)

class Database:
    _container: Any
    _db_name: str

    def __init__(
        self,
        database_name: str,
        password='password',
        root='root',
        address='127.0.0.1',
        port=5432,
        container_name=None,
    ):
        self._db_name = database_name
        self._db_pass = password
        self._db_root = root
        self._db_address = address
        self._db_port = port

        """Sets up the database."""
        logger.info('setting up database')

        logger.debug('connecting to docker host')
        client = docker.from_env()

        logger.debug('pulling postgres image (if necessary)')
        client.images.pull('postgres:10.7-alpine')

        logger.debug('starting database container')
        self._container = client.containers.run(
            name=container_name,
            image='postgres:10.7-alpine',
            auto_remove=True,
            environment={
                'POSTGRES_USER': root,
                'POSTGRES_PASSWORD': password,
                'POSTGRES_DB': database_name
            },
            ports={
                '5432': (address, port),
            },
            detach=True,
        )

        logger.debug('ensuring database is ready')
        while True:
            if self._container.exec_run("pg_isready -d {}".format(database_name)).exit_code == 0:
                break
            else:
                sleep(3)

        logger.info('database setup completed')

    def close(self):
        logger.info('stopping database container')
        self._container.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _run(self, cmd: str) -> str:
        result = self._container.exec_run('sh -c "{}"'.format(cmd))
        if result.exit_code != 0:
            raise Exception(result.output)

        return str(result.output)

    def dump(self, file: str):
        """Dumps the database content as 'tar' to the given file."""
        logger.info('dumping database to {}'.format(file))

        logger.debug('dumping inside the container')
        self._run("pg_dump {} > /root/tmp.sql".format(self._db_name))

        logger.debug('extracting dump from container')
        tar_raw, _ = self._container.get_archive('/root/tmp.sql')

        temp_file = str(file) + '.temp'

        logger.debug('writing to tar file {}'.format(file))
        try:
            with open(temp_file, 'wb') as f:
                for chunk in tar_raw:
                    f.write(chunk)
        except:
            # the dump is likely incomplete, so delete the temporary file
            Path(temp_file).unlink(missing_ok=True)

            # raise the exception so that it can be handled elsewhere
            raise
        else:
            # dump completed, so move the temp file to the final location
            shutil.move(temp_file, file)

        logger.debug('deleting dump inside the container')
        self._run("rm /root/tmp.sql")

        logger.info('dump completed')

    def load(self, file: str):
        """Loads the database content as 'tar' from the given file."""
        logger.info('loading database from {}'.format(file))

        tarstream = io.BytesIO()
        logger.debug('opening tar file {}'.format(file))
        with open(file, 'rb') as f:
            tarstream.write(f.read())
        tarstream.seek(0)

        logger.debug('inserting load to container')
        self._container.put_archive('/root/', tarstream)

        logger.debug('recreating existing database')
        self._run('dropdb --if-exists {}'.format(self._db_name))
        self._run('createdb {}'.format(self._db_name))

        logger.debug('loading dump into database')
        self._run('psql {} < /root/tmp.sql'.format(self._db_name))

        logger.debug('deleting dump inside the container')
        self._run("rm /root/tmp.sql")

        logger.info('load completed')
