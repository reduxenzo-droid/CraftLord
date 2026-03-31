#!/bin/bash
cd $1/crafty-4
git checkout $2

source ../.venv/bin/activate

pip3 install wheel
pip3 install setuptools
pip3 install setuptools-rust
pip3 install --no-cache-dir -r requirements.txt
deactivate
