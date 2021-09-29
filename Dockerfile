# Usage: (docker-compose recommended instead for simplicity)
#   docker build -t critrolesync_autosync .
#   docker run -it -v "$(pwd)":/code -v //var/run/docker.sock:/var/run/docker.sock --network host critrolesync_autosync

FROM python:3.7

RUN apt-get update -y && apt-get upgrade -y && apt-get install -y \
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
# - although dejavu pins pydub to version 0.23.1, a longstanding bug was fixed
#   in version 0.24.0 that caused bad match results
RUN pip install \
    docker \
    ffmpeg-python \
    librosa \
    matplotlib \
    numpy \
    psycopg2 \
    pyaudio \
    "pydub>=0.24" \
    requests \
    scipy \
    tqdm \
    youtube_dl

# install dejavu
# - use --no-deps to avoid using dejavu's pinned versions
RUN pip install --no-deps https://github.com/critrolesync/dejavu/zipball/master

WORKDIR /code/src

CMD python playground2.py
