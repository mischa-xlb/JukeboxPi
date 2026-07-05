#!/bin/bash
cd /home/pi/git/JukeboxPi

if [ ! -x venv/bin/pip ]; then
    echo "(Re)creating virtual environment..."
    rm -rf venv
    python3 -m venv venv
fi
venv/bin/pip install -q -r requirements.txt

exec venv/bin/python3 -u web_manager.py
