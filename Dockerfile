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

RUN pip install \
    https://github.com/critrolesync/dejavu/zipball/master \
    docker \
    ffmpeg-python \
    librosa \
    matplotlib \
    numpy \
    psycopg2 \
    pyaudio \
    pydub \
    requests \
    scipy \
    tqdm \
    youtube_dl

# although dejavu pins pydub to version 0.23.1, a longstanding bug was fixed in
# version 0.24.0 that caused bad match results
RUN pip install pydub==0.25.1

WORKDIR /code/src

CMD python playground2.py
