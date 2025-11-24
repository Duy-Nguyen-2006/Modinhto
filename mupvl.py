#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để crawl video theo diễn viên từ website mupvl.info
Sử dụng Crawl4AI và BeautifulSoup để phân tích HTML
Hỗ trợ phân trang và chuẩn hóa tên diễn viên qua DuckDuckGo
"""

import re
import unicodedata
import asyncio
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
import json

# Cấu hình
BASE_URL = "https://mupvl.info"
MAX_PAGES = 10  # Giới hạn số trang crawl cho mỗi diễn viên


def normalize_name(name: str) -> str:
    """
    Chuẩn hóa tên diễn viên thành slug
    Loại bỏ dấu, chuyển thành chữ thường và thay thế khoảng trắng bằng dấu gạch ngang
    
    Args:
        name: Tên diễn viên gốc (vd: "Eimi Fukada" hoặc "eimu fuk")
    
    Returns:
        Slug chuẩn hóa (vd: "eimi-fukada")
    """
    # Loại bỏ dấu tiếng Việt và các ký tự đặc biệt
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('utf-8')
    
    # Chuyển thành chữ thường và loại bỏ ký tự đặc biệt
    name = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
    
    # Thay thế nhiều khoảng trắng liên tiếp bằng 1 khoảng trắng
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Thay thế khoảng trắng bằng dấu gạch ngang
    slug = name.replace(' ', '-')
    
    return slug


async def search_actress_on_duckduckgo(query: str) -> Optional[str]:
    """
    Tìm kiếm tên diễn viên chuẩn trên DuckDuckGo
    
    Args:
        query: Tên diễn viên (có thể sai chính tả)
    
    Returns:
        Tên/slug diễn viên chuẩn, hoặc None nếu không tìm thấy
    """
    print(f"🔍 Đang tìm kiếm '{query}' trên DuckDuckGo...")
    
    # Tạo query tìm kiếm với từ khóa actress/JAV
    search_query = f"{query} actress JAV"
    search_url = f"https://duckduckgo.com/html/?q={search_query}"
    
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=search_url)
            
            if not result.success:
                print(f"⚠️  Không thể truy cập DuckDuckGo")
                return None
            
            soup = BeautifulSoup(result.html, 'html.parser')
            
            # Tìm suggestion "Including results for" nếu có
            did_you_mean = soup.find('div', id='did_you_mean')
            if did_you_mean:
                suggested_link = did_you_mean.find('a')
                if suggested_link:
                    suggested_text = suggested_link.get_text().strip().lower()
                    # Loại bỏ "actress jav" khỏi suggested text
                    suggested_text = re.sub(r'\s*(actress|jav)\s*', ' ', suggested_text, flags=re.IGNORECASE).strip()
                    if suggested_text:
                        print(f"✓ Gợi ý từ DuckDuckGo: {suggested_text}")
                        return suggested_text
            
            # Tìm các kết quả tìm kiếm
            results = soup.find_all('a', class_='result__a')
            
            for link in results[:10]:  # Kiểm tra 10 kết quả đầu tiên
                text = link.get_text().strip()
                
                # Extract tên diễn viên từ title
                # Pattern: Tìm tên người (các từ viết hoa liên tiếp)
                # VD: "Melody Hiina Marks JAV Actress" -> "Melody Hiina Marks"
                
                # Cách 1: Tìm pattern "Name JAV" hoặc "Name Actress"
                match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:JAV|Actress|Porn|AV)', text)
                if match:
                    actress_name = match.group(1).lower()
                    print(f"✓ Tìm thấy: {actress_name}")
                    return actress_name
                
                # Cách 2: Lấy các từ viết hoa ở đầu title (trước các từ khóa)
                words = text.split()
                name_parts = []
                for word in words:
                    # Dừng khi gặp từ khóa không phải tên
                    if word.lower() in ['jav', 'actress', 'porn', 'av', 'movies', 'videos', 'star', 'idol', 'model', '-', '|']:
                        break
                    # Lấy các từ viết hoa (có thể là tên)
                    if word[0].isupper() and len(word) > 1:
                        name_parts.append(word)
                
                if len(name_parts) >= 2:
                    actress_name = ' '.join(name_parts).lower()
                    print(f"✓ Tìm thấy: {actress_name}")
                    return actress_name
            
            # Nếu không tìm thấy kết quả phù hợp, thử chuẩn hóa query gốc
            print(f"⚠️  Không tìm thấy kết quả phù hợp, sử dụng tên gốc")
            return query.lower().strip()
            
    except Exception as e:
        print(f"⚠️  Lỗi khi tìm kiếm: {e}")
        return query.lower().strip()


def create_actress_url(actress_name: str, page: int = 1) -> List[str]:
    """
    Tạo các URL có thể có cho trang diễn viên
    Thử nhiều pattern khác nhau để tìm URL đúng
    
    Args:
        actress_name: Tên diễn viên đã chuẩn hóa
        page: Số trang (mặc định là 1)
    
    Returns:
        Danh sách các URL có thể có (sắp xếp theo độ ưu tiên)
    """
    slug = normalize_name(actress_name)
    parts = slug.split('-')
    
    urls = []
    page_suffix = f"?page={page}" if page > 1 else ""
    
    # Pattern 1: Tên đầy đủ (vd: melody-hiina-marks)
    urls.append(f"{BASE_URL}/actresses/{slug}{page_suffix}")
    
    # Pattern 2: Nếu có 3 phần (First Middle Last), thử bỏ middle name
    if len(parts) == 3:
        # First-Last (vd: melody-marks)
        first_last = f"{parts[0]}-{parts[2]}"
        urls.append(f"{BASE_URL}/actresses/{first_last}{page_suffix}")
        
        # Last-First (vd: marks-melody)
        last_first = f"{parts[2]}-{parts[0]}"
        urls.append(f"{BASE_URL}/actresses/{last_first}{page_suffix}")
        
        # First-Middle (vd: melody-hiina) - ít phổ biến nhưng vẫn thử
        first_middle = f"{parts[0]}-{parts[1]}"
        urls.append(f"{BASE_URL}/actresses/{first_middle}{page_suffix}")
    
    # Pattern 3: Nếu có 2 phần (First Last), thử đảo ngược
    elif len(parts) == 2:
        # Last-First (vd: fukada-eimi)
        reversed_slug = f"{parts[1]}-{parts[0]}"
        urls.append(f"{BASE_URL}/actresses/{reversed_slug}{page_suffix}")
    
    # Pattern 4: Nếu có 4+ phần, thử các tổ hợp
    elif len(parts) >= 4:
        # First-Last
        first_last = f"{parts[0]}-{parts[-1]}"
        urls.append(f"{BASE_URL}/actresses/{first_last}{page_suffix}")
        
        # Last-First
        last_first = f"{parts[-1]}-{parts[0]}"
        urls.append(f"{BASE_URL}/actresses/{last_first}{page_suffix}")
    
    return urls


async def check_url_validity(url: str, crawler) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra xem URL có hợp lệ không (HTTP 200 và có video)
    
    Args:
        url: URL cần kiểm tra
        crawler: AsyncWebCrawler instance
    
    Returns:
        (valid, html) - True nếu hợp lệ, kèm theo HTML content
    """
    try:
        result = await crawler.arun(url=url)
        
        if not result.success:
            return False, None
        
        soup = BeautifulSoup(result.html, 'html.parser')
        video_items = soup.find_all('div', class_='video-item')
        
        # Nếu có ít nhất 1 video item thì URL hợp lệ
        if len(video_items) > 0:
            return True, result.html
        
        return False, None
        
    except Exception as e:
        return False, None


def extract_videos_from_html(html: str) -> List[Dict[str, str]]:
    """
    Trích xuất thông tin video từ HTML
    
    Args:
        html: Nội dung HTML của trang
    
    Returns:
        Danh sách các video với title và link
    """
    soup = BeautifulSoup(html, 'html.parser')
    videos = []
    
    # Tìm tất cả các video items
    video_items = soup.find_all('div', class_='video-item')
    
    for item in video_items:
        # Tìm thẻ a đầu tiên (chứa link video)
        link_tag = item.find('a', class_='video-item__thumb')
        
        if link_tag:
            video_url = link_tag.get('href', '')
            video_title = link_tag.get('title', '')
            
            # Nếu URL không đầy đủ, thêm base URL
            if video_url and not video_url.startswith('http'):
                video_url = urljoin(BASE_URL, video_url)
            
            # Nếu không có title từ thumb, thử lấy từ title div
            if not video_title:
                title_div = item.find('div', class_='video-item__title')
                if title_div:
                    title_link = title_div.find('a')
                    if title_link:
                        video_title = title_link.get('title', '') or title_link.get_text(strip=True)
            
            if video_url and video_title:
                videos.append({
                    'title': video_title.strip(),
                    'link': video_url.strip()
                })
    
    return videos


def has_pagination(html: str) -> bool:
    """
    Kiểm tra xem trang có phân trang không
    
    Args:
        html: Nội dung HTML của trang
    
    Returns:
        True nếu có phân trang
    """
    soup = BeautifulSoup(html, 'html.parser')
    pagenavi = soup.find('div', class_='pagenavi')
    
    if pagenavi and pagenavi.find_all('a'):
        return True
    
    return False


async def search_videos_by_actress(actress_name: str) -> List[Dict[str, str]]:
    """
    Tìm kiếm và crawl tất cả video của một diễn viên
    Hỗ trợ phân trang tự động
    
    Args:
        actress_name: Tên diễn viên đã chuẩn hóa
    
    Returns:
        Danh sách tất cả video từ tất cả các trang
    """
    all_videos = []
    seen_links = set()  # Để loại bỏ trùng lặp
    
    print(f"\n🎬 Bắt đầu crawl video của {actress_name}...")
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        # Bước 1: Tìm URL hợp lệ
        print("📍 Đang tìm URL hợp lệ...")
        possible_urls = create_actress_url(actress_name, page=1)
        
        valid_url = None
        base_html = None
        
        for url in possible_urls:
            print(f"   Thử: {url}")
            is_valid, html = await check_url_validity(url, crawler)
            
            if is_valid:
                valid_url = url
                base_html = html
                print(f"   ✓ URL hợp lệ!")
                break
        
        if not valid_url:
            print("❌ Không tìm thấy trang diễn viên hợp lệ")
            return []
        
        # Bước 2: Crawl trang đầu tiên
        print(f"\n📄 Crawl trang 1...")
        videos = extract_videos_from_html(base_html)
        
        for video in videos:
            if video['link'] not in seen_links:
                all_videos.append(video)
                seen_links.add(video['link'])
        
        print(f"   ✓ Tìm thấy {len(videos)} video")
        
        # Bước 3: Kiểm tra và crawl các trang tiếp theo
        # Lấy base URL (không có query params)
        base_actress_url = valid_url.split('?')[0]
        
        for page_num in range(2, MAX_PAGES + 1):
            page_url = f"{base_actress_url}?page={page_num}"
            
            print(f"\n📄 Crawl trang {page_num}...")
            print(f"   URL: {page_url}")
            
            try:
                result = await crawler.arun(url=page_url)
                
                if not result.success:
                    print(f"   ⚠️  Không thể truy cập trang {page_num}")
                    break
                
                videos = extract_videos_from_html(result.html)
                
                # Nếu không còn video, dừng lại
                if len(videos) == 0:
                    print(f"   ℹ️  Không còn video, dừng crawl")
                    break
                
                # Thêm video mới vào danh sách
                new_videos_count = 0
                for video in videos:
                    if video['link'] not in seen_links:
                        all_videos.append(video)
                        seen_links.add(video['link'])
                        new_videos_count += 1
                
                print(f"   ✓ Tìm thấy {len(videos)} video ({new_videos_count} video mới)")
                
                # Nếu không có video mới, có thể đã hết
                if new_videos_count == 0:
                    print(f"   ℹ️  Không có video mới, dừng crawl")
                    break
                
                # Delay nhỏ giữa các request
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"   ⚠️  Lỗi khi crawl trang {page_num}: {e}")
                break
    
    return all_videos


def display_results(videos: List[Dict[str, str]], actress_name: str):
    """
    Hiển thị kết quả tìm kiếm một cách đẹp mắt
    
    Args:
        videos: Danh sách video
        actress_name: Tên diễn viên
    """
    print("\n" + "="*80)
    print(f"🎯 KẾT QUẢ TÌM KIẾM CHO: {actress_name.upper()}")
    print("="*80)
    
    if not videos:
        print("\n❌ Không tìm thấy video nào!")
        return
    
    print(f"\n✓ Tìm thấy tổng cộng {len(videos)} video\n")
    
    for idx, video in enumerate(videos, 1):
        print(f"{idx}. {video['title']}")
        print(f"   🔗 {video['link']}")
        print()
    
    print("="*80)


async def main():
    """
    Hàm chính - chạy chương trình
    """
    print("="*80)
    print("🎬 CÔNG CỤ TÌM KIẾM VIDEO THEO DIỄN VIÊN - MUPVL.INFO")
    print("="*80)
    
    # Nhận input từ người dùng
    actress_input = input("\n👤 Nhập tên diễn viên (VD: eimi fukada, eimu fuk): ").strip()
    
    if not actress_input:
        print("❌ Vui lòng nhập tên diễn viên!")
        return
    
    print(f"\n📝 Bạn đã nhập: {actress_input}")
    
    # Bước 1: Chuẩn hóa tên qua DuckDuckGo
    normalized_name = await search_actress_on_duckduckgo(actress_input)
    
    if not normalized_name:
        print("❌ Không thể chuẩn hóa tên diễn viên. Vui lòng thử lại!")
        return
    
    print(f"✓ Tên chuẩn: {normalized_name}")
    
    # Bước 2: Tìm kiếm video
    videos = await search_videos_by_actress(normalized_name)
    
    # Bước 3: Hiển thị kết quả
    display_results(videos, normalized_name)


if __name__ == "__main__":
    # Chạy chương trình
    asyncio.run(main())
