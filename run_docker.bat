@echo off
echo ========================================================
echo Hướng dẫn: Đang build Docker Image...
echo ========================================================
docker build -t video-crawler .

echo.
echo ========================================================
echo Hướng dẫn: Đang chạy Docker Container...
echo ========================================================
REM Xóa container cũ nếu tồn tại
docker rm -f crawler-container 2>nul

REM Chạy container mới
docker run -d -p 8080:8080 --name crawler-container -v "%cd%/data:/app/data" video-crawler

echo.
echo ========================================================
echo Container đã chạy!
echo Hãy truy cập: http://localhost:8080
echo Để xem log, chạy lệnh: docker logs -f crawler-container
echo ========================================================
pause
