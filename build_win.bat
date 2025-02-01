@echo off
REM Create virtual environment if it doesn't exist
if not exist venv (
    py -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install requirements
python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
pip install pyinstaller

REM Create executable
pyinstaller --onefile ^
    --icon=assets/fire.ico ^
    --add-data "assets;assets" ^
    --hidden-import=engineio.async_drivers.threading ^
    --hidden-import=engineio.async_drivers ^
    --hidden-import=socketio ^
    --paths venv\Lib\site-packages ^
    source/flambe.py

REM Create distribution folder
if not exist dist\windows mkdir dist\windows
move /Y dist\flambe.exe dist\windows\
if not exist dist\windows\assets mkdir dist\windows\assets
copy /Y assets\*.* dist\windows\assets\

echo Build complete! Executable is in dist\windows\flambe.exe

pause 