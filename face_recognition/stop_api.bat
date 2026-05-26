@echo off
echo Stopping processes on port 8000 and 8001...
for %%P in (8000 8001) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do (
        echo Killing PID %%a on port %%P
        taskkill /F /PID %%a >nul 2>&1
    )
)
echo Done.
pause
