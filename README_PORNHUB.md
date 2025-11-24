# Pornhub Video Scraper

Module Python để tìm kiếm và lấy thông tin video theo tên diễn viên từ Pornhub.

## Tính năng

- ✅ Tìm kiếm video theo tên diễn viên
- ✅ Trả về tiêu đề và link video
- ✅ Hỗ trợ normalize tên (bỏ dấu) để tìm kiếm chính xác hơn
- ✅ Retry logic và error handling
- ✅ Debug mode để troubleshoot
- ✅ Hỗ trợ cloudscraper để bypass Cloudflare

## Cài đặt

```bash
# Dependencies cơ bản
pip install beautifulsoup4 lxml requests

# Để bypass Cloudflare (khuyến nghị)
pip install cloudscraper

# Hoặc sử dụng Selenium (tốt nhất cho bypass bot detection)
pip install selenium undetected-chromedriver
```

## Sử dụng

### Cách 1: Sử dụng requests + cloudscraper (porn_hub.py)

```python
from porn_hub import search_videos_by_actor

# Tìm kiếm video
actor_name = "melody mark"
results = search_videos_by_actor(actor_name)

# Hiển thị kết quả
for video in results:
    print(f"Title: {video['title']}")
    print(f"Link: {video['link']}")
    print(f"Source: {video['source']}")
    print()
```

### Cách 2: Sử dụng Selenium (porn_hub_selenium.py)

```python
from porn_hub_selenium import search_videos_by_actor

# Selenium tốt hơn cho việc bypass bot detection
results = search_videos_by_actor("eva elfie")
```

### Sử dụng debug mode

```python
# Bật debug để xem chi tiết quá trình crawl
results = search_videos_by_actor("eimi fukada", debug=True)
```

### Chạy từ command line

```bash
# Chạy trực tiếp file
python3 porn_hub.py

# Hoặc với selenium
python3 porn_hub_selenium.py

# Chạy demo với dữ liệu mẫu
python3 porn_hub_demo.py
```

## Output Format

Mỗi kết quả trả về là một dictionary với format:

```python
{
    'source': 'Pornhub',
    'title': 'Tên video',
    'link': 'https://www.pornhub.com/view_video.php?viewkey=...'
}
```

## Files

- `porn_hub.py` - Module chính sử dụng requests + cloudscraper
- `porn_hub_selenium.py` - Phiên bản sử dụng Selenium (tốt hơn cho bypass bot)
- `porn_hub_demo.py` - Demo với dữ liệu mẫu
- `test_pornhub.py` - Script test tự động với 3 tên diễn viên mẫu
- `README_PORNHUB.md` - Hướng dẫn này

## Các vấn đề thường gặp và giải pháp

### 1. Lỗi 403 Forbidden

**Nguyên nhân:** Website có bot detection mạnh, chặn requests

**Giải pháp:**
- Sử dụng VPN hoặc proxy
- Sử dụng phiên bản Selenium (`porn_hub_selenium.py`)
- Thêm delay giữa các requests
- Sử dụng undetected-chromedriver

```python
# Với VPN/Proxy
import cloudscraper

scraper = cloudscraper.create_scraper()
scraper.proxies = {
    'http': 'http://your-proxy:port',
    'https': 'https://your-proxy:port'
}
```

### 2. Không tìm thấy video

**Nguyên nhân:**
- Tên diễn viên không chính xác
- Website thay đổi HTML structure
- Diễn viên không có video hoặc bị remove

**Giải pháp:**
- Thử với tên khác (stage name, real name)
- Bật debug mode để xem chi tiết: `debug=True`
- Kiểm tra và cập nhật selector trong code

### 3. Dữ liệu bị thiếu hoặc không đầy đủ

**Nguyên nhân:** Website thay đổi cấu trúc HTML

**Giải pháp:**
- Cập nhật selectors trong hàm `crawl_videos()`
- Thêm selectors mới nếu cần
- Xem page source để tìm selectors đúng

### 4. Module chạy chậm

**Nguyên nhân:**
- Retry logic khi bị 403
- Website load chậm
- Nhiều requests liên tiếp

**Giải pháp:**
- Giảm retry attempts
- Tăng timeout
- Sử dụng async (cần refactor code)

## Test

Chạy test với 3 tên diễn viên mẫu:

```bash
python3 test_pornhub.py
```

Chạy demo với dữ liệu mẫu:

```bash
python3 porn_hub_demo.py
```

## Lưu ý

⚠️ **Quan trọng:**
- Module này chỉ dùng cho mục đích giáo dục và nghiên cứu
- Tuân thủ Terms of Service của website
- Không spam requests quá nhiều
- Sử dụng delay giữa các requests
- Có thể bị chặn nếu crawl quá nhiều

## Ví dụ nâng cao

### Tìm kiếm nhiều diễn viên

```python
from porn_hub import search_videos_by_actor

actors = ["melody mark", "eva elfie", "eimi fukada"]
all_results = {}

for actor in actors:
    print(f"Searching for: {actor}")
    results = search_videos_by_actor(actor)
    all_results[actor] = results
    print(f"Found {len(results)} videos\n")
```

### Lưu kết quả vào file JSON

```python
import json
from porn_hub import search_videos_by_actor

actor = "melody mark"
results = search_videos_by_actor(actor)

with open(f"{actor}_videos.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
```

### Lọc kết quả theo từ khóa

```python
from porn_hub import search_videos_by_actor

actor = "melody mark"
keyword = "POV"

results = search_videos_by_actor(actor)
filtered = [v for v in results if keyword.lower() in v['title'].lower()]

print(f"Found {len(filtered)} videos with keyword '{keyword}'")
```

## License

MIT License - Sử dụng tự do nhưng chịu trách nhiệm về hành vi của bản thân.

## Disclaimer

Công cụ này được tạo ra chỉ cho mục đích giáo dục. Người dùng chịu trách nhiệm về việc sử dụng công cụ này. Tác giả không chịu trách nhiệm về bất kỳ hành vi lạm dụng nào.
