# Usage: (docker-compose recommended instead for simplicity)
#   docker build -t critrolesync_autosync .
#   docker run -it -v //var/run/docker.sock:/var/run/docker.sock -v "$(pwd)":/code -v ~/critrolesync-data:/data --network host critrolesync_autosync episode_ids
# where episode_ids takes a form like C1E1 or C2E1-141

FROM python:3.9

RUN apt-get update -y && apt-get install -y \
    ffmpeg \
    gcc \
    libasound-dev \
    libportaudio2 \
    libportaudiocpp0 \
    nano \
    portaudio19-dev \
    postgresql \
    postgresql-contrib \
&& rm -rf /var/lib/apt/lists/*

# install python packages
# - packages that may affect dejavu fingerprint hashes are pinned to the latest
#   known working versions
# - in particular, pydub>=0.24 is needed to avoid a fingerprint matching bug
RUN pip install \
    docker \
    ffmpeg-python==0.2.0 \
    librosa==0.8.1 \
    matplotlib==3.4.3 \
    numpy==1.20.3 \
    psycopg2==2.9.1 \
    pyaudio==0.2.11 \
    pydub==0.25.1 \
    requests \
    scipy==1.7.1 \
    tqdm \
    yt_dlp==2021.10.22

# install dejavu
# - use --no-deps to avoid using dejavu's pinned versions
RUN pip install --no-deps https://github.com/critrolesync/dejavu/zipball/master

# copy this project's source code to the image
# - this allows the image to be shared and deployed in isolation with a static
#   version of the source code included
# - however, for a development environment, it is convenient to run editable
#   source on the host machine; this is accomplished by mounting a host
#   directory at /code, which will supersede this copy, using either the -v
#   flag or docker-compose
COPY . /code

WORKDIR /code/src

ENTRYPOINT ["python", "-m", "critrolesync.autosync"]
