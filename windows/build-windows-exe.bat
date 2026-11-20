@echo off
REM ============================================================================
REM Trad Rainmeter for Windows — Standalone .exe & .rmskin Builder
REM Builds:
REM   1. dist\TradRainmeter-Windows-x64.exe (Standalone Engine + Control Center)
REM   2. dist\TradRainmeter_1.1.0.rmskin    (Windows Rainmeter Skin Package)
REM   3. dist\TradRainmeter-Windows-Portable-x64.zip
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo ================================================================
echo   Building Trad Rainmeter for Windows (Standalone .exe + .rmskin)
echo ================================================================

echo [1/4] Installing Python build dependencies (pyinstaller, psutil)...
python -m pip install --upgrade pip pyinstaller psutil

echo [2/4] Building TradRainmeter_1.1.0.rmskin package...
python windows\build_rmskin.py 1.1.0 dist\TradRainmeter_1.1.0.rmskin

echo [3/4] Compiling Standalone TradRainmeter-Windows-x64.exe with PyInstaller...
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name "TradRainmeter-Windows-x64" ^
  --icon "assets\trad-engine.ico" ^
  --add-data "assets;assets" ^
  --add-data "suites;suites" ^
  --add-data "widgets;widgets" ^
  --add-data "windows\build_rmskin.py;windows" ^
  windows\trad_rainmeter_win.py

echo [4/4] Packaging TradRainmeter-Windows-Portable-x64.zip...
if exist "dist\TradRainmeter-Windows" rmdir /s /q "dist\TradRainmeter-Windows"
mkdir "dist\TradRainmeter-Windows"
copy /y "dist\TradRainmeter-Windows-x64.exe" "dist\TradRainmeter-Windows\TradRainmeter.exe"
copy /y "dist\TradRainmeter_1.1.0.rmskin" "dist\TradRainmeter-Windows\TradRainmeter_1.1.0.rmskin"
copy /y "windows\README-WINDOWS.md" "dist\TradRainmeter-Windows\README-WINDOWS.md"
xcopy /e /i /y "assets" "dist\TradRainmeter-Windows\assets"
xcopy /e /i /y "suites" "dist\TradRainmeter-Windows\suites"
xcopy /e /i /y "widgets" "dist\TradRainmeter-Windows\widgets"

powershell -Command "Compress-Archive -Force -Path 'dist\TradRainmeter-Windows\*' -DestinationPath 'dist\TradRainmeter-Windows-Portable-x64.zip'"

echo ================================================================
echo Build Complete! Output files in dist\:
echo   * dist\TradRainmeter-Windows-x64.exe
echo   * dist\TradRainmeter_1.1.0.rmskin
echo   * dist\TradRainmeter-Windows-Portable-x64.zip
echo ================================================================
