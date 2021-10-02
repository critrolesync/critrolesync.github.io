#!/usr/bin/env bash

apt-get update

apt-get install -y python3.7 python3-pip ffmpeg libasound-dev portaudio19-dev libportaudio2 libportaudiocpp0 python3-psycopg2

python3 -m pip install -r /vagrant/environment/python/requirements.txt
patch /usr/local/lib/python3.8/dist-packages/dejavu/__init__.py /vagrant/environment/python/dejavu-logging.patch

curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

if [ -e "/vagrant/Vagrantfile"]; then
    sudo usermod -aG docker vagrant
else
    sudo usermod -aG docker $USER
fi

systemctl enable docker
systemctl start docker
