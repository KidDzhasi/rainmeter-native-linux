@echo off
REM ============================================================================
REM Trad Desktop for Windows — Standalone .exe & Skin Package Builder
REM Builds:
REM   1. dist\TradDesktop-Windows-x64.exe (Standalone Engine + Control Center)
REM   2. dist\TradDesktop_1.2.0.rmskin    (Desktop Skin Package)
REM   3. dist\TradDesktop-Windows-Portable-x64.zip
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo ================================================================
echo   Building Trad Desktop for Windows (Standalone .exe + Package)
echo ================================================================

echo [1/4] Installing Python build dependencies (pyinstaller, psutil)...
python -m pip install --upgrade pip pyinstaller psutil

echo [2/4] Building TradDesktop_1.2.0.rmskin package...
python windows\build_rmskin.py 1.2.0 dist\TradDesktop_1.2.0.rmskin

echo [3/4] Compiling Standalone TradDesktop-Windows-x64.exe with PyInstaller...
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name "TradDesktop-Windows-x64" ^
  --icon "assets\trad-engine.ico" ^
  --add-data "assets;assets" ^
  --add-data "suites;suites" ^
  --add-data "widgets;widgets" ^
  --add-data "windows\build_rmskin.py;windows" ^
  windows\trad_desktop_win.py

echo [4/4] Packaging TradDesktop-Windows-Portable-x64.zip...
if exist "dist\TradDesktop-Windows" rmdir /s /q "dist\TradDesktop-Windows"
mkdir "dist\TradDesktop-Windows"
copy /y "dist\TradDesktop-Windows-x64.exe" "dist\TradDesktop-Windows\TradDesktop.exe"
copy /y "dist\TradDesktop_1.2.0.rmskin" "dist\TradDesktop-Windows\TradDesktop_1.2.0.rmskin"
copy /y "windows\README-WINDOWS.md" "dist\TradDesktop-Windows\README-WINDOWS.md"
xcopy /e /i /y "assets" "dist\TradDesktop-Windows\assets"
xcopy /e /i /y "suites" "dist\TradDesktop-Windows\suites"
xcopy /e /i /y "widgets" "dist\TradDesktop-Windows\widgets"

powershell -Command "Compress-Archive -Force -Path 'dist\TradDesktop-Windows\*' -DestinationPath 'dist\TradDesktop-Windows-Portable-x64.zip'"

echo ================================================================
echo Build Complete! Output files in dist\:
echo   * dist\TradDesktop-Windows-x64.exe
echo   * dist\TradDesktop_1.2.0.rmskin
echo   * dist\TradDesktop-Windows-Portable-x64.zip
echo ================================================================
