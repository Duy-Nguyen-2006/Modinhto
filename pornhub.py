#!/usr/bin/env python3
"""
Pornhub Video Crawler - Educational purposes only
Tìm kiếm video theo tên diễn viên với 3 lớp lọc
"""

import asyncio
import re
import unicodedata
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler


def normalize_name(name: str) -> str:
    """
    Chuẩn hóa tên diễn viên:
    - Loại bỏ dấu (accents)
    - Chuyển thành lowercase
    - Thay space bằng +
    """
    # Loại bỏ dấu tiếng Việt và các dấu khác
    nfd = unicodedata.normalize('NFD', name)
    name_no_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    # Lowercase và thay space bằng +
    normalized = name_no_accents.lower().strip()
    normalized = re.sub(r'\s+', '+', normalized)
    
    return normalized


def create_search_url(actress_name: str, page: int = 1) -> str:
    """
    Tạo URL search từ tên diễn viên đã normalize
    """
    base_url = "https://www.pornhub.com/video/search"
    normalized_name = normalize_name(actress_name)
    
    if page == 1:
        return f"{base_url}?search={normalized_name}"
    else:
        return f"{base_url}?search={normalized_name}&page={page}"


def extract_video_info(video_item, base_url: str = "https://www.pornhub.com") -> dict:
    """
    Trích xuất thông tin video từ HTML element
    Trả về dict với keys: title, link
    """
    try:
        # Tìm thẻ <a> có attribute title (chứa tiêu đề video)
        title_link = video_item.find('a', attrs={'title': True})
        
        if not title_link:
            return None
        
        title = title_link.get('title', '').strip()
        href = title_link.get('href', '').strip()
        
        # LỚP 2: Loại bỏ link giả/không hợp lệ
        if not href or href == '#' or 'javascript:' in href.lower():
            return None
        
        # Xử lý URL (relative hoặc absolute)
        if href.startswith('/'):
            video_url = urljoin(base_url, href)
        elif href.startswith('http'):
            # Kiểm tra không phải link ads đến domain khác
            parsed = urlparse(href)
            if 'pornhub.com' not in parsed.netloc:
                return None
            video_url = href
        else:
            video_url = base_url + '/' + href
        
        return {
            'title': title,
            'link': video_url
        }
    
    except Exception as e:
        # Bỏ qua video lỗi, tiếp tục
        return None


def filter_by_actress_name(videos: list, actress_name: str) -> list:
    """
    LỚP 3: Lọc video theo tên diễn viên
    CHỈ GIỮ video có ít nhất 1 keyword của tên diễn viên trong tiêu đề
    """
    # Split tên diễn viên thành keywords
    actress_keywords = actress_name.lower().split()
    
    filtered_videos = []
    
    for video in videos:
        title_lower = video['title'].lower()
        
        # Kiểm tra xem có ít nhất 1 keyword trong tiêu đề không
        has_actress_name = any(keyword in title_lower for keyword in actress_keywords)
        
        if has_actress_name:
            filtered_videos.append(video)
    
    return filtered_videos


async def search_videos_by_actor(actress_name: str, max_pages: int = 10) -> list:
    """
    Crawl và tìm kiếm video theo tên diễn viên
    
    Args:
        actress_name: Tên diễn viên cần tìm
        max_pages: Số trang tối đa cần crawl (mặc định 10)
    
    Returns:
        List các video dict với keys: title, link
    """
    all_videos = []
    seen_titles = set()  # Deduplication
    base_url = "https://www.pornhub.com"
    
    print(f"\n🔍 Đang tìm kiếm video của: {actress_name}")
    print(f"📄 Sẽ crawl tối đa {max_pages} trang kết quả...\n")
    
    async with AsyncWebCrawler(verbose=False, headless=True) as crawler:
        current_page = 1
        
        while current_page <= max_pages:
            search_url = create_search_url(actress_name, current_page)
            
            print(f"📥 Đang crawl trang {current_page}: {search_url}")
            
            try:
                # Crawl trang
                result = await crawler.arun(
                    url=search_url,
                    bypass_cache=True,
                    delay_before_return_html=3.0,
                    wait_for="css:li.videoBox"
                )
                
                if not result.success:
                    print(f"❌ Lỗi khi crawl trang {current_page}: {result.error_message}")
                    break
                
                # Parse HTML
                soup = BeautifulSoup(result.html, 'lxml')
                
                # Tìm tất cả video items
                video_boxes = soup.find_all('li', class_='videoBox')
                
                if not video_boxes:
                    print(f"⚠️  Không tìm thấy video nào ở trang {current_page}")
                    break
                
                print(f"   Tìm thấy {len(video_boxes)} video items")
                
                page_videos = []
                
                for video_box in video_boxes:
                    # LỚP 1: Loại bỏ Premium Videos & Ads
                    # Kiểm tra class có premium, sponsored, ads không
                    classes = video_box.get('class', [])
                    class_str = ' '.join(classes).lower()
                    
                    if any(marker in class_str for marker in ['premium', 'sponsor', 'ad-']):
                        continue
                    
                    # Kiểm tra style="display: block" (thường là ads)
                    style = video_box.get('style', '')
                    if 'display' in style and 'block' in style:
                        # Note: Có thể là video hợp lệ, cần kiểm tra thêm
                        pass
                    
                    # Trích xuất thông tin video
                    video_info = extract_video_info(video_box, base_url)
                    
                    if video_info:
                        # Deduplication
                        if video_info['title'] not in seen_titles:
                            seen_titles.add(video_info['title'])
                            page_videos.append(video_info)
                
                print(f"   Sau khi lọc lớp 1 & 2: {len(page_videos)} video")
                
                # Thêm vào kết quả tổng
                all_videos.extend(page_videos)
                
                # Kiểm tra xem có trang tiếp theo không
                pagination = soup.find('div', class_='pagination3')
                if pagination:
                    next_page_link = pagination.find('li', class_='page_next')
                    if not next_page_link or next_page_link.find('a', href=True) is None:
                        print(f"✓ Đã đến trang cuối cùng")
                        break
                else:
                    # Không có pagination, chỉ có 1 trang
                    print(f"✓ Chỉ có 1 trang kết quả")
                    break
                
                current_page += 1
                
                # Delay giữa các request để tránh bị block
                await asyncio.sleep(2)
            
            except Exception as e:
                print(f"❌ Lỗi khi xử lý trang {current_page}: {str(e)}")
                break
    
    print(f"\n📊 Tổng số video crawl được (trước lọc tên): {len(all_videos)}")
    
    # LỚP 3: Filter theo tên diễn viên (QUAN TRỌNG NHẤT)
    filtered_videos = filter_by_actress_name(all_videos, actress_name)
    
    print(f"📊 Sau khi lọc theo tên diễn viên: {len(filtered_videos)} video\n")
    
    return filtered_videos


def display_results(videos: list, actress_name: str) -> None:
    """
    Hiển thị kết quả tìm kiếm đẹp mắt
    """
    print("=" * 80)
    print(f"📹 KẾT QUẢ TÌM KIẾM: {actress_name.upper()}")
    print("=" * 80)
    
    if not videos:
        print("\n❌ Không tìm thấy video nào phù hợp!")
        print("💡 Gợi ý:")
        print("   - Kiểm tra lại chính tả tên diễn viên")
        print("   - Thử với tên khác (tên thật, stage name...)")
        print("   - Trang web có thể đang chặn crawler\n")
        return
    
    print(f"\n✅ Tìm thấy {len(videos)} video:\n")
    
    for i, video in enumerate(videos, 1):
        print(f"{i}. 📺 {video['title']}")
        print(f"   🔗 {video['link']}\n")
    
    print("=" * 80)


async def main():
    """
    Chương trình chính
    """
    print("\n" + "=" * 80)
    print("🎬 PORNHUB VIDEO CRAWLER - BY ACTRESS NAME")
    print("=" * 80)
    print("⚠️  Educational purposes only - Use responsibly")
    print("=" * 80 + "\n")
    
    # Nhập tên diễn viên
    actress_name = input("👤 Nhập tên diễn viên (ví dụ: melody marks): ").strip()
    
    if not actress_name:
        print("❌ Vui lòng nhập tên diễn viên!")
        return
    
    # Mặc định crawl 10 trang
    max_pages = 10
    
    # Crawl và lọc video
    videos = await search_videos_by_actor(actress_name, max_pages)
    
    # Hiển thị kết quả
    display_results(videos, actress_name)


if __name__ == "__main__":
    asyncio.run(main())
