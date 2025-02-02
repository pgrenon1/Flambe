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

echo "[INFO] Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable flambe.service
sudo systemctl start flambe.service

echo "[INFO] Build complete! Executable is in dist/linux/flambe"
echo "[INFO] Service status:"
systemctl status flambe.service 