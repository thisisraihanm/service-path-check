@echo off
cd /d "%~dp0"
py -3 -c "import sys, tkinter; assert sys.version_info >= (3,11)" >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3 "%~dp0desktop.py"
    exit /b
)
python -c "import sys, tkinter; assert sys.version_info >= (3,11)" >nul 2>nul
if not errorlevel 1 (
    start "" pythonw "%~dp0desktop.py"
    exit /b
)
echo This source copy needs Python 3.11 or newer with Tcl/Tk.
echo The Windows app download runs without installing Python.
echo Open the download page below and get the Windows ZIP under Assets.
start "" "https://github.com/thisisraihanm/service-path-check/releases/latest"
pause
