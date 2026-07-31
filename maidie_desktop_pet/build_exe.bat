@echo off
setlocal
cd /d "%~dp0"

echo [INFO] build_exe.bat is a compatibility entry. Using scripts\build.py beta.
python scripts\build.py beta
exit /b %ERRORLEVEL%
