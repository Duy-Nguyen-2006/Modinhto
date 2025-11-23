# Hướng Dẫn Sửa Lỗi và Triển Khai Docker trên Windows

Tài liệu này cung cấp chi tiết về các lỗi đã được sửa, cách chạy ứng dụng trên localhost, và hướng dẫn triển khai bằng Docker trên Windows.

## Phần 1: Phân tích và sửa lỗi

Tôi đã phân tích mã nguồn và thực hiện các thay đổi sau để đảm bảo ứng dụng hoạt động ổn định và lắng nghe trên cổng 8080.

### 1. `main.py`
- **Vấn đề:**
    - Ứng dụng không tự động chạy trên cổng 8080 khi khởi chạy trực tiếp bằng Python.
    - Đường dẫn cơ sở dữ liệu (`./data/data.db`) có thể gây lỗi nếu thư mục `data` chưa tồn tại.
- **Sửa chữa:**
    - Thêm khối `if __name__ == "__main__":` để chạy server với `uvicorn` trên host `0.0.0.0` và port `8080`.
    - Thêm logic để tự động tạo thư mục `data` nếu chưa tồn tại.

```python
# Đoạn mã đã thêm vào main.py
import os
from pathlib import Path

# ... (code khác)

# Đảm bảo thư mục data tồn tại
data_dir = Path("./data")
data_dir.mkdir(parents=True, exist_ok=True)

DB_PATH = f"sqlite:///{data_dir}/data.db"

# ... (code khác)

if __name__ == "__main__":
    import uvicorn
    # Chạy trên port 8080 như yêu cầu
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### 2. `Dockerfile`
- **Vấn đề:**
    - Cấu hình mặc định lắng nghe trên cổng 8000.
    - Thiếu cài đặt `beautifulsoup4` (cần thiết cho module `bs4`).
- **Sửa chữa:**
    - Đổi `EXPOSE` và lệnh `CMD` sang cổng 8080.
    - Đảm bảo đầy đủ các thư viện được cài đặt.

```dockerfile
# Dockerfile đã sửa
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY *.py readme.md index.html /app/

RUN mkdir -p /app/data

RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlmodel sqlalchemy crawl4ai bs4

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 3. `docker-compose.yml`
- **Vấn đề:**
    - Mapping port cũ là `8080:8000`. Dù hoạt động, nhưng để nhất quán với cấu hình container mới, cần map `8080:8080`.
- **Sửa chữa:**
    - Cập nhật ports thành `8080:8080`.

```yaml
version: "3.9"
services:
  backend:
    build: .
    container_name: video-crawler-backend
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### 4. `requirements.txt`
- **Vấn đề:** File này bị thiếu, gây khó khăn cho việc cài đặt môi trường local.
- **Sửa chữa:** Đã tạo file `requirements.txt` với đầy đủ dependencies.

### 5. Cải thiện logic Crawl (`main.py`)
- **Vấn đề:** Khi tìm kiếm, nếu kết nối timeout hoặc lần trước lỗi (lưu 0 kết quả), hệ thống vẫn trả về cache rỗng.
- **Sửa chữa:**
  - Tăng thời gian chờ (timeout) lên 120 giây để đảm bảo crawl đủ dữ liệu.
  - Thêm cơ chế tự động crawl lại nếu trong cache không có video nào (0 video).

---

## Phần 2: Cấu hình cho localhost:8080

Để chạy ứng dụng trực tiếp trên Windows (không dùng Docker), làm theo các bước sau:

1.  **Cài đặt Python:** Đảm bảo bạn đã cài Python 3.8+ (tải từ [python.org](https://www.python.org/)).
2.  **Mở CMD hoặc PowerShell** tại thư mục dự án.
3.  **Cài đặt dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Cài đặt trình duyệt cho Playwright:**
    ```bash
    playwright install chromium
    ```
5.  **Chạy ứng dụng:**
    ```bash
    python main.py
    ```
    *Thông báo sẽ hiện ra: `Uvicorn running on http://0.0.0.0:8080`*

6.  **Kiểm tra:** Mở trình duyệt và truy cập `http://localhost:8080`.

---

## Phần 3: Hướng dẫn Docker (Windows)

Dưới đây là hướng dẫn từng bước để triển khai dự án bằng Docker trên Windows.

### 1. Yêu cầu hệ thống
- **Docker Desktop:** Đã cài đặt và đang chạy (tải tại [docker.com](https://www.docker.com/products/docker-desktop/)).
- Đảm bảo WSL 2 (Windows Subsystem for Linux) đã được bật (Docker Desktop thường sẽ nhắc bạn cài đặt).

### 2. Các bước triển khai

**Bước 1: Mở Terminal**
- Mở PowerShell hoặc Command Prompt và di chuyển đến thư mục chứa code dự án.

**Bước 2: Build Docker Image**
Chạy lệnh sau để tạo image (tên là `video-crawler`):
```bash
docker build -t video-crawler .
```
*Lưu ý: Quá trình này có thể mất vài phút để tải base image và cài đặt thư viện.*

**Bước 3: Chạy Container**
Sau khi build xong, chạy container và map port 8080:
```bash
docker run -d -p 8080:8080 --name crawler-container -v "%cd%/data:/app/data" video-crawler
```
*Giải thích lệnh:*
- `-d`: Chạy ngầm (detached mode).
- `-p 8080:8080`: Chuyển port 8080 của máy Windows vào port 8080 của container.
- `-v "%cd%/data:/app/data"`: Mount thư mục `data` hiện tại vào container để dữ liệu không bị mất khi tắt container. (Nếu dùng PowerShell, thay `%cd%` bằng `${PWD}`).

**Lựa chọn thay thế: Sử dụng Docker Compose (Khuyên dùng)**
Nếu bạn muốn đơn giản hơn, chỉ cần chạy lệnh duy nhất:
```bash
docker-compose up -d --build
```

### 3. Kiểm tra và Debug

- **Kiểm tra container đang chạy:**
  ```bash
  docker ps
  ```
  Bạn sẽ thấy `crawler-container` (hoặc tên trong compose) với trạng thái `Up` và port `0.0.0.0:8080->8080/tcp`.

- **Xem log (nếu có lỗi):**
  ```bash
  docker logs -f crawler-container
  ```

- **Kiểm tra hoạt động:**
  Mở trình duyệt và vào: `http://localhost:8080`.
  Hoặc dùng lệnh curl trong PowerShell:
  ```powershell
  curl http://localhost:8080/api/home
  ```

### 4. Xử lý lỗi phổ biến

- **Lỗi "Port already in use":**
  Có ứng dụng khác đang dùng port 8080.
  - Tìm process: `netstat -ano | findstr :8080`
  - Tắt container cũ: `docker rm -f crawler-container`

- **Lỗi không kết nối được Database:**
  Đảm bảo bạn đã cấp quyền chia sẻ ổ đĩa cho Docker (trong Docker Desktop Settings > Resources > File Sharing) nếu file DB không được tạo. Tuy nhiên, Docker Desktop trên WSL 2 thường tự xử lý việc này.

---
**Kết quả mong đợi:**
Khi truy cập `http://localhost:8080`, bạn sẽ thấy giao diện chính (file `index.html`) hoặc JSON API trả về dữ liệu.
