#!/bin/bash
sudo dnf update -y
sudo dnf group install "Development tools" -y
sudo dnf install git python3 python3-devel java-21-openjdk java-21-openjdk-devel libffi libffi-devel cargo -y
install_return=$?
if [[ "$install_return" != 0 ]];then
	exit $install_return
fi
sudo useradd crafty -s /bin/bash
exit 0
