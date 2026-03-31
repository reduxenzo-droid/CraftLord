#!/bin/bash
sudo apt update -y
sudo apt install git python3 python3-dev python3-pip python3-venv libcurl4 software-properties-common -y
install_return=$?
if [[ "$install_return" != 0 ]];then
	exit $install_return
fi
sudo useradd crafty -s /bin/bash
exit 0
