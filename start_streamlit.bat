@echo off
setlocal
cd /d "%~dp0"
set "TASK_PYTHON="
if defined BAANDEE_PYTHON call :candidate "%BAANDEE_PYTHON%"
call :candidate "%~dp0.venv\Scripts\python.exe"
where py.exe >nul 2>nul
if not errorlevel 1 for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do call :candidate "%%P"
call :candidate "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :candidate "%%~fD\python.exe"
for /d %%D in ("%ProgramFiles%\Python3*") do call :candidate "%%~fD\python.exe"
for /f "delims=" %%P in ('where python.exe 2^>nul') do call :candidate "%%P"
if not defined TASK_PYTHON goto missing_python
"%TASK_PYTHON%" "%~dp0launch.py" %*
set "TASK_EXIT=%errorlevel%"
goto finish

:candidate
if defined TASK_PYTHON exit /b 0
if not exist "%~1" exit /b 0
"%~1" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if not errorlevel 1 set "TASK_PYTHON=%~1"
exit /b 0

:missing_python
echo.
echo No working Python 3.10+ was found. Python 3.12 is recommended.
echo Install Python from https://www.python.org/downloads/windows/
echo Select Add python.exe to PATH, then run this file again.
echo No need to change Windows security settings or execution aliases.
echo.
echo To use the online demo without Python, double-click open_online.url
echo https://baandee-quality-studio.streamlit.app/
set "TASK_EXIT=9009"

:finish
if "%~1"=="--check" exit /b %TASK_EXIT%
if not "%TASK_EXIT%"=="0" echo Startup failed. See the message above and GETTING_STARTED.md
pause
exit /b %TASK_EXIT%
