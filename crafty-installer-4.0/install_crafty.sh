#!/bin/bash
sudo -v
sudo_test="$?"
if [ "${sudo_test}" -eq 127 ];then
    echo "ERROR: sudo is required for installation."
    fail=1
elif [ "${sudo_test}" -eq 1 ];then
    echo "Apologies - your system seems to have restricted sudo commands from your user"
    fail=1
elif [ "${sudo_test}" -eq 0 ];then
    fail=0
else
    echo "Something really bad broke. (sudo_test is ${sudo_test}). Please report this error to the developer"
fi

if [ "${fail}" -eq 1 ];then
    echo "Please see the documentation for details:"
    echo "    https://wiki.craftycontrol.com/"
elif [ "${fail}" -eq 0 ];then
    if [[ $EUID -ne 0 ]]; then
        echo "Note: You are not root. Re-executing this script as root using sudo"
        sudo "$0"
    else
        echo "Installing Crafty..."
        # Check to see what package manager to use.
        if [ -d "/etc/apt" ]; then
            sudo apt install python3-pip python3-distro -y
        elif [ -d "/etc/pacman.d" ]; then
            sudo pacman -S python-pip python-distro --noconfirm
        else
            sudo dnf install python3-pip python3-distro -y
        fi
        python3 install_crafty.py
    fi
else
    echo "Something really bad broke. (fail value is ${fail}). Please report this error to the developer"
fi
