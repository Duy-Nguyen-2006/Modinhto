# Unified Video Search API

API tổng hợp tìm kiếm video từ TẤT CẢ các nguồn trong một lần gọi duy nhất.

## Tính năng

- ✅ Tìm kiếm trên **11 nguồn** đồng thời:
  - VLXX
  - Thumbzilla
  - HeoVL
  - Javtiful
  - JavX
  - MupVL
  - Pornhub
  - SexTop1
  - VailonXX
  - XHamster
  - XVideo

- ✅ Kết quả tổng hợp từ tất cả nguồn
- ✅ Hỗ trợ CORS (có thể gọi từ mọi nguồn)
- ✅ Response JSON đầy đủ với metadata
- ✅ Xử lý lỗi tự động (nếu một nguồn lỗi, các nguồn khác vẫn hoạt động)

## Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements-unified-api.txt
```

### 2. Chạy API

```bash
python unified-api.py
```

API sẽ chạy tại: `http://localhost:8000`

## Sử dụng

### Endpoint: `/search`

**Method:** GET

**Parameters:**
- `q` (required): Tên diễn viên cần tìm kiếm

**Ví dụ:**

```bash
# Tìm kiếm "eimi fukada"
curl "http://localhost:8000/search?q=eimi+fukada"

# Hoặc dùng browser
http://localhost:8000/search?q=eimi%20fukada
```

### Response Format

```json
{
  "query": "eimi fukada",
  "total": 150,
  "sources_found": 8,
  "total_sources": 11,
  "results": [
    {
      "source": "VLXX",
      "title": "Video title here",
      "link": "https://..."
    },
    ...
  ],
  "by_source": {
    "VLXX": {
      "count": 25,
      "videos": [...]
    },
    "Thumbzilla": {
      "count": 30,
      "videos": [...]
    },
    ...
  }
}
```

### Các endpoint khác

- `GET /` - Thông tin API
- `GET /docs` - Swagger UI documentation
- `GET /health` - Health check

## Ví dụ sử dụng trong code

### Python

```python
import requests

response = requests.get("http://localhost:8000/search", params={"q": "eimi fukada"})
data = response.json()

print(f"Tìm thấy {data['total']} video từ {data['sources_found']} nguồn")

for video in data['results']:
    print(f"[{video['source']}] {video['title']}")
    print(f"  Link: {video['link']}")
```

### JavaScript/Fetch

```javascript
fetch('http://localhost:8000/search?q=eimi+fukada')
  .then(response => response.json())
  .then(data => {
    console.log(`Tìm thấy ${data.total} video từ ${data.sources_found} nguồn`);

    data.results.forEach(video => {
      console.log(`[${video.source}] ${video.title}`);
      console.log(`  Link: ${video.link}`);
    });
  });
```

### cURL

```bash
curl -X GET "http://localhost:8000/search?q=eimi%20fukada" -H "accept: application/json"
```

## Chạy trong production

### Với Uvicorn

```bash
# Chạy với nhiều workers
uvicorn unified-api:app --host 0.0.0.0 --port 8000 --workers 4

# Chạy với reload (development)
uvicorn unified-api:app --host 0.0.0.0 --port 8000 --reload
```

### Với Docker (tùy chọn)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements-unified-api.txt .
RUN pip install -r requirements-unified-api.txt

COPY *.py .

CMD ["uvicorn", "unified-api:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t unified-api .
docker run -p 8000:8000 unified-api
```

## Lưu ý

1. **Performance**: API gọi 11 nguồn đồng thời (concurrent), nhưng thời gian phản hồi phụ thuộc vào nguồn chậm nhất.

2. **Rate Limiting**: Một số nguồn có thể có rate limiting. Nếu gọi quá nhiều request, có thể bị block tạm thời.

3. **Error Handling**: Nếu một nguồn lỗi, các nguồn khác vẫn hoạt động bình thường. Kết quả sẽ được trả về từ những nguồn thành công.

4. **Timeout**: Mỗi nguồn có timeout riêng (thường 30-90 giây). Nếu timeout, nguồn đó sẽ bị bỏ qua.

## Troubleshooting

### API không chạy được

```bash
# Kiểm tra port đã được sử dụng chưa
lsof -i :8000

# Thay đổi port
uvicorn unified-api:app --host 0.0.0.0 --port 8080
```

### Lỗi import module

```bash
# Đảm bảo tất cả file scraper nằm cùng thư mục với unified-api.py
ls *.py

# Cài lại dependencies
pip install -r requirements-unified-api.txt --force-reinstall
```

### Kết quả trả về rỗng

- Kiểm tra tên diễn viên có đúng không
- Thử với tên khác (ví dụ: "yua mikami", "julia jav", ...)
- Kiểm tra log để xem nguồn nào bị lỗi

## Tích hợp với frontend

API này có CORS được bật, nên bạn có thể gọi trực tiếp từ browser/frontend:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Video Search</title>
</head>
<body>
    <input type="text" id="search" placeholder="Nhập tên diễn viên">
    <button onclick="search()">Tìm kiếm</button>
    <div id="results"></div>

    <script>
        async function search() {
            const query = document.getElementById('search').value;
            const response = await fetch(`http://localhost:8000/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            document.getElementById('results').innerHTML =
                `<h2>Tìm thấy ${data.total} video từ ${data.sources_found} nguồn</h2>` +
                data.results.map(v =>
                    `<div>[${v.source}] <a href="${v.link}">${v.title}</a></div>`
                ).join('');
        }
    </script>
</body>
</html>
```

## License

Chỉ sử dụng cho mục đích học tập và nghiên cứu.
