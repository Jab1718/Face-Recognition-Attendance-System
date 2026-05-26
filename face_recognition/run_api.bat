@echo off
title Face Recognition API Server
echo ========================================================
echo DANG KHOI DONG BACKEND API (PORT 8001)...
echo ========================================================

:: Kích hoạt môi trường ảo (dựa theo ảnh cây thư mục của bạn có folder .venv)
call .venv\Scripts\activate

:: Chạy server với chế độ in chi tiết lỗi (debug)
uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload

:: Giữ cửa sổ CMD không bị tắt nếu server bị sập
echo.
echo [!] TIEP TRINH API DA BI DUNG HOAC GAP LOI.
pause