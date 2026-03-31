#!/bin/bash
sudo dnf update -y
sudo dnf install git-core python3 java-17-openjdk-headless -y
install_return=$?
if [[ "$install_return" != 0 ]];then
	exit $install_return
fi
sudo useradd crafty -s /bin/bash
exit 0
