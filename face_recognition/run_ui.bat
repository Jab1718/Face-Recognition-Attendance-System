@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Streamlit UI - API expected at http://127.0.0.1:8001
streamlit run ui/app.py
