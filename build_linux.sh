#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
python3 -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
pip install pyinstaller

# Create executable
pyinstaller --onefile \
    --add-data "assets:assets" \
    --icon=assets/fire.png \
    --hidden-import=engineio.async_drivers.threading \
    --hidden-import=engineio.async_drivers \
    --hidden-import=socketio \
    source/flambe.py

# Create distribution folder
mkdir -p dist/linux
mv dist/flambe dist/linux/
mkdir -p dist/linux/assets
cp -r assets/* dist/linux/assets/

# Make executable
chmod +x dist/linux/flambe

echo "Build complete! Executable is in dist/linux/flambe" 