@echo off
echo ========================================================
echo Hướng dẫn: Đang cài đặt thư viện cần thiết...
echo ========================================================
pip install -r requirements.txt

echo.
echo ========================================================
echo Hướng dẫn: Đang cài đặt trình duyệt Chromium...
echo ========================================================
playwright install chromium

echo.
echo ========================================================
echo Hướng dẫn: Đang khởi động Server tại http://localhost:8080
echo ========================================================
python main.py

pause
