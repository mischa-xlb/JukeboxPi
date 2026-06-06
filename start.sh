#!/bin/bash
cd /home/pi/Documents/JukeboxPi

if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
fi


exec venv/bin/python3 -u JukeBoxSonosProd.py
