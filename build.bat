@echo off
setlocal

cd /d "%~dp0"

echo Installing build dependencies...
py -3.14 -m pip install -r requirements.txt pyinstaller -q

echo Building Pixelizer.exe...
py -3.14 -m PyInstaller --noconfirm pixelizer.spec

if %ERRORLEVEL% NEQ 0 (
    echo Build failed.
    exit /b 1
)

echo.
echo Done: dist\Pixelizer.exe
endlocal
