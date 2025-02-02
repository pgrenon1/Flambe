@echo off
echo [INFO] Starting Windows build process...

echo [INFO] Setting up virtual environment...
if not exist venv (
    echo [INFO] Creating new virtual environment...
    py -m venv venv
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Installing/Upgrading pip tools...
python -m pip install --upgrade pip wheel setuptools

echo [INFO] Installing requirements...
pip install -r requirements.txt
pip install pyinstaller

echo [INFO] Creating executable with PyInstaller...
pyinstaller --onefile ^
    --icon=assets/fire.ico ^
    --add-data "assets;assets" ^
    --hidden-import=engineio.async_drivers.threading ^
    --hidden-import=engineio.async_drivers ^
    --hidden-import=socketio ^
    --paths venv\Lib\site-packages ^
    source/flambe.py

echo [INFO] Setting up distribution folder...
if not exist dist\windows mkdir dist\windows
move /Y dist\flambe.exe dist\windows\
if not exist dist\windows\assets mkdir dist\windows\assets
copy /Y assets\*.* dist\windows\assets\

echo [INFO] Build complete! Executable is in dist\windows\flambe.exe
echo [INFO] Press any key to exit...
pause 