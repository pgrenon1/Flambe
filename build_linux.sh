#!/bin/bash

echo "[INFO] Starting Linux build process..."

echo "[INFO] Setting up virtual environment..."
if [ ! -d "venv" ]; then
    echo "[INFO] Creating new virtual environment..."
    python3 -m venv venv
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

echo "[INFO] Installing/Upgrading pip tools..."
python3 -m pip install --upgrade pip wheel setuptools

echo "[INFO] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    libpython3-dev \
    python3-venv \
    python3-pip \
    libatlas-base-dev \
    libjasper-dev \
    libqt4-test \
    libhdf5-dev \
    libhdf5-serial-dev

echo "[INFO] Installing requirements..."
pip install -r requirements.txt
pip install pyinstaller

echo "[INFO] Creating executable with PyInstaller..."
pyinstaller --onefile \
    --add-data "assets:assets" \
    --icon=assets/fire.png \
    --hidden-import=engineio.async_drivers.threading \
    --hidden-import=engineio.async_drivers \
    --hidden-import=socketio \
    --runtime-tmpdir /tmp \
    --add-binary '/usr/lib/python3.11/lib-dynload/*:lib-dynload' \
    source/flambe.py

echo "[INFO] Setting up distribution folder..."
mkdir -p dist/linux
mv dist/flambe dist/linux/
mkdir -p dist/linux/assets
cp -r assets/* dist/linux/assets/

echo "[INFO] Making executable..."
chmod +x dist/linux/flambe

echo "[INFO] Setting up systemd service..."
# Create service file
sudo tee /etc/systemd/system/flambe.service > /dev/null << EOL
[Unit]
Description=Flambe Application
After=graphical.target

[Service]
Type=simple
User=$USER
Environment=DISPLAY=:0
ExecStart=$(pwd)/dist/linux/flambe
Restart=on-failure
WorkingDirectory=$(pwd)/dist/linux

[Install]
WantedBy=graphical.target
EOL

if [ "$1" = "--no-service" ]; then
    echo "[INFO] Disabling flambe service..."
    sudo systemctl stop flambe.service
    sudo systemctl disable flambe.service
    sudo systemctl daemon-reload
    echo "[INFO] Service disabled and removed"
else
    echo "[INFO] Enabling and starting service..."
    sudo systemctl daemon-reload
    sudo systemctl enable flambe.service
    sudo systemctl start flambe.service
    echo "[INFO] Service status:"
    systemctl status flambe.service
fi

echo "[INFO] Build complete! Executable is in dist/linux/flambe" 