#!/bin/bash
sudo apt update -y
sudo apt install git python3 python3-dev libffi-dev python3-pip python3-venv libcurl4 software-properties-common openjdk-8-jdk-headless openjdk-8-jre-headless openjdk-11-jdk-headless openjdk-11-jre-headless openjdk-17-jdk-headless openjdk-17-jre-headless openjdk-21-jdk-headless openjdk-21-jre-headless -y
install_return=$?
if [[ "$install_return" != 0 ]];then
	exit $install_return
fi
if [[ "$(uname -m)" == "aarch64" ]];then
	sudo apt install build-essential libssl-dev libffi-dev -y
	install_return=$?
	if [[ "$install_return" != 0 ]];then
		exit $install_return
	fi
fi
sudo useradd crafty -s /bin/bash
exit 0
