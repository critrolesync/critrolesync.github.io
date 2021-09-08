#!/usr/bin/env bash

apt-get update

apt-get install -y python3.7 python3-pip ffmpeg

python3 -m pip install -r /vagrant/src/requirements.txt

curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

if [ -e "/vagrant/Vagrantfile"]; then
    sudo usermod -aG docker vagrant
else
    sudo usermod -aG docker $USER
fi

systemctl enable docker
systemctl start docker
