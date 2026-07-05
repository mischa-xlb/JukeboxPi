#!/bin/bash
cd /home/pi/git/JukeboxPi

if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
venv/bin/pip install -q -r requirements.txt

exec venv/bin/python3 -u JukeBoxSonosProd.py
