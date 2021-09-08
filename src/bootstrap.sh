#!/usr/bin/env bash

apt-get update

apt-get install -y python3.7 python3-pip ffmpeg

python3 -m pip install -r /vagrant/src/requirements.txt
