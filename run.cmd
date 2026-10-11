@echo off
cd /d "%~dp0"
set "PKB_PYTHON=D:\venvs\pkb\Scripts\python.exe"
if not exist "%PKB_PYTHON%" (
    echo Python environment not found at D:\venvs\pkb.
    exit /b 1
)
"%PKB_PYTHON%" -m streamlit run frontend/app.py %*
