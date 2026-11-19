@echo off
cd /d "%~dp0"
title Afk token
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set "REQ=r162"
set "PY="

py -3.13 -c "import sys" >nul 2>nul && set "PY=py -3.13" && goto found
py -3.12 -c "import sys" >nul 2>nul && set "PY=py -3.12" && goto found
py -3.11 -c "import sys" >nul 2>nul && set "PY=py -3.11" && goto found
py -3.14 -c "import sys" >nul 2>nul && set "PY=py -3.14" && goto found
py -3.10 -c "import sys" >nul 2>nul && set "PY=py -3.10" && goto found
python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,14) else 1)" >nul 2>nul && set "PY=python" && goto found

echo.
echo [ERROR] Need Python 3.13 64-bit. Python 3.15 and newer are NOT supported yet.
echo Download: https://www.python.org/downloads/windows/
echo Find Python 3.13.x - Windows installer 64-bit - check "Add python.exe to PATH"
echo Read INSTRUKCIYA / the instruction file in this folder, step 1.
echo.
pause
exit /b

:found
echo Using Python:
%PY% --version

set "INST="
if exist ".installed" set /p INST=<.installed
if "%INST%"=="%PY% %REQ%" goto run

echo.
echo Installing libraries. First time takes 5-10 minutes, do not close this window...
echo.
%PY% -m pip install --upgrade pip
%PY% -m pip install --prefer-binary -r requirements.txt
if errorlevel 1 goto fail
>.installed echo %PY% %REQ%

:run
echo.
echo Starting Afk token... do not close this window while the bot works
%PY% afk_token.py %*
if errorlevel 1 pause
exit /b

:fail
echo.
echo [ERROR] Install failed. Check the internet and run start.bat again.
echo If it fails again, send a screenshot of this window to @kk4ose
pause
exit /b
