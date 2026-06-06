@echo off
title Aegis Crypto Builder
color 0A

:: This forces the script to run in the exact folder where the .bat file is located!
cd /d "%~dp0"

echo ===================================================
echo     Aegis Crypto - Standalone Executable Builder
echo ===================================================
echo.

:: Check if main.py actually exists in this folder
if not exist "main.py" (
    color 0C
    echo ERROR: Could not find main.py! 
    echo Please make sure this build.bat file is inside the same folder as main.py.
    echo.
    pause
    exit /b
)

echo [1/3] Cleaning up old build files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"
del /f /q *.spec 2>nul
del /f /q xref-*.html 2>nul
del /f /q warn-*.txt 2>nul

echo.
echo [2/3] Installing/Verifying required dependencies...
python -m pip install pyinstaller customtkinter cryptography argon2-cffi pycryptodome

echo.
echo [3/3] Compiling Aegis_Crypto.exe...
:: Added error checking to stop the script if PyInstaller fails!
python -m PyInstaller --noconfirm --onedir --windowed --clean --icon=icon.ico --name "Aegis_Crypto" main.py

if %errorlevel% neq 0 (
    echo.
    color 0C
    echo ===================================================
    echo   CRITICAL ERROR! 
    echo   PyInstaller failed to build the application.
    echo   Please scroll up to read the red error message from Python!
    echo ===================================================
    pause
    exit /b
)

echo.
echo ===================================================
echo   SUCCESS! 
echo   Your compiled app is ready inside the "dist" folder!
echo ===================================================
pause