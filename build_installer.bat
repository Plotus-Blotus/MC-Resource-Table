@echo off
setlocal
cd /d "%~dp0"
echo === MC Resource Table 13.2 Studio Installer Builder ===
where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python launcher not found. Install Python from python.org and enable the launcher.
  pause
  exit /b 1
)
py -m pip install -r requirements.txt
if errorlevel 1 goto :fail
py -m PyInstaller --noconfirm --clean --onedir --windowed --icon mc_resource_table.ico --add-data "mc_resource_table.png;." --name MCResourceTable app.py
if errorlevel 1 goto :fail
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo ERROR: Inno Setup 6 was not found. Install it from jrsoftware.org.
  pause
  exit /b 1
)
"%ISCC%" installer.iss
if errorlevel 1 goto :fail
echo.
echo SUCCESS! Find MC_Resource_Table_Setup.exe inside the output folder.
pause
exit /b 0
:fail
echo ERROR: Build failed. Check the error messages above.
pause
exit /b 1
