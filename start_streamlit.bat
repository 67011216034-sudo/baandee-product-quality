@echo off
setlocal
cd /d "%~dp0"
set "TASK_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "TASK_RUNTIME=%~dp0..\..\work\streamlit-runtime"
if exist "%TASK_PYTHON%" if exist "%TASK_RUNTIME%\streamlit" (
  set "PYTHONPATH=%TASK_RUNTIME%"
  "%TASK_PYTHON%" -m streamlit run streamlit_app.py --server.headless true
  goto done
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m streamlit run streamlit_app.py --server.headless true
) else (
  python -m streamlit run streamlit_app.py --server.headless true
)
:done
pause
