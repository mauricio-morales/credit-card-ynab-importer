#!/bin/bash
cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
    echo "Python 3 not found. Please install Python 3.9 or newer from https://python.org"
    echo "Press any key to exit."
    read -n 1
    exit 1
fi

echo "Installing/updating dependencies..."
pip3 install -r requirements.txt --quiet
echo "Starting the application..."
python3 run.py
echo "Press any key to exit."
read -n 1
