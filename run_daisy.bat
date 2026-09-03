@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m daisy_pet
    exit /b 0
)

where pythonw.exe >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw.exe -m daisy_pet
    exit /b 0
)

python -m daisy_pet
