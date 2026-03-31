#!/bin/bash
sudo pacman -Syu
sudo pacman -S --noconfirm git python python-pip jdk-openjdk rust
install_return=$?
if [[ "$install_return" != 0 ]];then
	exit $install_return
fi
sudo useradd crafty -s /bin/bash
exit 0
