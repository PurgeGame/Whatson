#!/bin/bash

# Path to your virtual environment
VENV_PATH="/opt/scripts/Whatson/.venv"

# Activate the virtual environment
source "$VENV_PATH/bin/activate"

# Run the Python script
python /opt/scripts/Whatson/Whatson.py

# Deactivate the virtual environment (optional, since the script will exit)
deactivate