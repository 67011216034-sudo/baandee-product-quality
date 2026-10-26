@echo off
rem Legacy HTML/API app. For the Streamlit UI use start_streamlit.bat.
if "%~1"=="--check" (
  call "%~dp0start_streamlit.bat" --check --legacy
  exit /b
)
call "%~dp0start_streamlit.bat" --legacy %*
exit /b %errorlevel%
