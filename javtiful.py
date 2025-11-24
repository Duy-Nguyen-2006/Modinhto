#!/usr/bin/env python3
"""
Javtiful Video Crawler v3.1
Tìm kiếm video theo tên diễn viên với DuckDuckGo fuzzy search
"""

import re
import unicodedata
from typing import List, Dict, Optional
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
import asyncio
from urllib.parse import unquote, urlparse, parse_qs


def normalize_search_query(name: str) -> str:
    """
    Chuẩn hóa tên để tìm kiếm (giữ khoảng trắng, chuyển thành +)
    """
    # Loại bỏ dấu
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    
    # Lowercase và làm sạch
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', '+', name)
    
    return name


async def search_actress_via_duckduckgo(actress_name: str) -> Optional[str]:
    """
    Tìm kiếm actress qua DuckDuckGo và lấy slug chính xác
    
    Logic:
    1. Search "javtiful + actress_name" trên DuckDuckGo
    2. Lấy link javtiful đầu tiên
    3. Extract slug từ URL
    
    Args:
        actress_name: Tên diễn viên (có thể sai chính tả)
    
    Returns:
        Slug của actress, hoặc None nếu không tìm thấy
    """
    search_query = f"javtiful {actress_name}"
    search_query_encoded = search_query.replace(' ', '+')
    ddg_url = f"https://html.duckduckgo.com/html/?q={search_query_encoded}"
    
    print(f"\n🔍 Đang tìm kiếm qua DuckDuckGo: {actress_name}")
    print(f"🔗 URL: {ddg_url}")
    
    try:
        async with AsyncWebCrawler(verbose=False, headless=True) as crawler:
            result = await crawler.arun(
                url=ddg_url,
                bypass_cache=True,
                delay_before_return_html=2.0
            )
            
            if not result.success:
                print(f"⚠️  Lỗi khi search DuckDuckGo: {result.error_message}")
                return None
            
            soup = BeautifulSoup(result.html, 'html.parser')
            
            # DuckDuckGo HTML version uses class "result__a" for result links
            result_links = soup.find_all('a', class_='result__a')
            
            if not result_links:
                print("⚠️  Không tìm thấy kết quả nào từ DuckDuckGo")
                return None
            
            print(f"✅ Tìm thấy {len(result_links)} kết quả từ DuckDuckGo")
            
            # Parse và tìm javtiful actress links
            javtiful_actress_links = []
            
            for link in result_links:
                href = link.get('href', '')
                text = link.get_text().strip()
                
                # DuckDuckGo redirects through uddg parameter
                if 'uddg=' in href:
                    parsed = urlparse(href)
                    params = parse_qs(parsed.query)
                    
                    if 'uddg' in params:
                        actual_url = unquote(params['uddg'][0])
                        
                        # Check if it's a javtiful actress/star link
                        # Support multiple domains: .com, .to, .ru, .info, etc.
                        match = re.search(r'javtiful\.[a-z]+/(actress|star|actor)/([^/?#]+)', actual_url, re.IGNORECASE)
                        
                        if match:
                            slug = match.group(2)
                            javtiful_actress_links.append({
                                'slug': slug,
                                'url': actual_url,
                                'text': text
                            })
            
            if javtiful_actress_links:
                # Lấy link đầu tiên (thường là kết quả tốt nhất)
                first_result = javtiful_actress_links[0]
                slug = first_result['slug']
                
                print(f"\n✅ Tìm thấy actress: {first_result['text'][:60]}")
                print(f"🎯 Slug: {slug}")
                print(f"🔗 Source URL: {first_result['url']}")
                
                return slug
            else:
                print("⚠️  Không tìm thấy actress link trong kết quả")
                return None
    
    except Exception as e:
        print(f"⚠️  Lỗi khi search: {str(e)}")
        return None


def parse_videos_from_html(html_content: str) -> List[Dict[str, str]]:
    """
    Parse HTML và lấy danh sách video
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    videos = []
    
    # Method 1: Tìm theo class có chứa "video"
    video_links = soup.find_all('a', class_=lambda x: x and 'video' in x.lower())
    
    for link in video_links:
        title = link.get('title', '').strip()
        if not title:
            title = link.get_text().strip()
        
        href = link.get('href', '').strip()
        
        # Chỉ lấy link video
        if href and ('/video/' in href or '/watch/' in href or '/movie/' in href):
            if href.startswith('/'):
                href = f"https://javtiful.com{href}"
            
            if title and href:
                videos.append({
                    'title': title,
                    'link': href
                })
    
    # Method 2: Fallback - tìm tất cả link có /video/ hoặc /watch/
    if not videos:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '').strip()
            if '/video/' in href or '/watch/' in href or '/movie/' in href:
                title = link.get('title', '') or link.get_text().strip()
                
                if href.startswith('/'):
                    href = f"https://javtiful.com{href}"
                
                if title:
                    videos.append({
                        'title': title,
                        'link': href
                    })
    
    # Loại bỏ trùng lặp
    seen_links = set()
    unique_videos = []
    for video in videos:
        if video['link'] not in seen_links:
            seen_links.add(video['link'])
            unique_videos.append(video)
    
    return unique_videos


def get_total_pages(html_content: str) -> int:
    """
    Lấy tổng số trang từ pagination
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Tìm pagination
    pagination = soup.find('ul', class_=lambda x: x and 'pagination' in x.lower() if x else False)
    
    if not pagination:
        pagination = soup.find('div', class_=lambda x: x and 'pagination' in x.lower() if x else False)
    
    if not pagination:
        return 1
    
    # Tìm tất cả page links
    page_links = pagination.find_all('a', href=True)
    max_page = 1
    
    for link in page_links:
        page_text = link.get_text().strip()
        
        # Extract số từ text
        numbers = re.findall(r'\d+', page_text)
        if numbers:
            page_num = int(numbers[0])
            max_page = max(max_page, page_num)
        
        # Extract từ href
        href = link.get('href', '')
        page_match = re.search(r'[?&]page=(\d+)', href)
        if page_match:
            page_num = int(page_match.group(1))
            max_page = max(max_page, page_num)
    
    return max_page


async def crawl_actress_by_slug(slug: str) -> List[Dict[str, str]]:
    """
    Crawl tất cả video của actress
    """
    all_videos = []
    seen_links = set()
    
    async with AsyncWebCrawler(verbose=False, headless=True) as crawler:
        first_url = f"https://javtiful.com/actress/{slug}"
        
        print(f"\n📄 Đang crawl trang 1: {first_url}")
        
        try:
            result = await crawler.arun(
                url=first_url,
                bypass_cache=True,
                delay_before_return_html=2.0
            )
            
            # Parse videos từ trang 1
            videos_page1 = parse_videos_from_html(result.html)
            
            # Nếu không tìm thấy video, thử biến thể slug (hina <-> hiina)
            if len(videos_page1) == 0 and result.success:
                print(f"⚠️  Không tìm thấy video với slug: {slug}")
                print(f"🔄 Thử các biến thể của slug...")
                
                # Thử thay đổi: hiina -> hina hoặc ngược lại
                alt_slugs = []
                if 'hiina' in slug:
                    alt_slugs.append(slug.replace('hiina', 'hina'))
                elif 'hina' in slug:
                    alt_slugs.append(slug.replace('hina', 'hiina'))
                if slug == 'eimi-fukada':
                    alt_slugs.append('fukada-eimi')
                
                if alt_slugs:
                    for alt_slug in alt_slugs:
                        alt_url = f"https://javtiful.com/actress/{alt_slug}"
                        print(f"🔄 Thử slug: {alt_slug}")
                        print(f"🔗 URL: {alt_url}")
                        
                        result = await crawler.arun(
                            url=alt_url,
                            bypass_cache=True,
                            delay_before_return_html=2.0
                        )
                        
                        if result.success:
                            videos_page1 = parse_videos_from_html(result.html)
                            
                            if len(videos_page1) > 0:
                                # Thành công với slug mới
                                slug = alt_slug
                                first_url = alt_url
                                print(f"✅ Thành công với slug: {slug}")
                                break
                            else:
                                print(f"❌ Vẫn không tìm thấy video với slug: {alt_slug}")
                        else:
                            print(f"❌ Lỗi với slug: {alt_slug}")
                    
                    if len(videos_page1) == 0:
                        return []
                else:
                    print(f"❌ Không có biến thể slug để thử")
                    return []
            
            if len(videos_page1) == 0:
                print(f"❌ Không tìm thấy video nào!")
                return []
            
            print(f"✅ Tìm thấy {len(videos_page1)} video ở trang 1")
            
            for video in videos_page1:
                if video['link'] not in seen_links:
                    all_videos.append(video)
                    seen_links.add(video['link'])
            
            # Lấy tổng số trang
            total_pages = get_total_pages(result.html)
            
            if total_pages > 1:
                print(f"📚 Tổng số trang: {total_pages}\n")
            
            # Crawl các trang còn lại
            if total_pages > 1:
                for page_num in range(2, total_pages + 1):
                    page_url = f"https://javtiful.com/actress/{slug}?page={page_num}"
                    
                    print(f"📄 Đang crawl trang {page_num}/{total_pages}")
                    
                    try:
                        result = await crawler.arun(
                            url=page_url,
                            bypass_cache=True,
                            delay_before_return_html=1.5
                        )
                        
                        if result.success:
                            videos_page = parse_videos_from_html(result.html)
                            print(f"✅ Tìm thấy {len(videos_page)} video ở trang {page_num}")
                            
                            for video in videos_page:
                                if video['link'] not in seen_links:
                                    all_videos.append(video)
                                    seen_links.add(video['link'])
                        else:
                            print(f"⚠️  Lỗi trang {page_num}: {result.error_message}")
                    
                    except Exception as e:
                        print(f"⚠️  Lỗi trang {page_num}: {str(e)}")
                    
                    await asyncio.sleep(1)
                    
        except Exception as e:
            print(f"❌ Lỗi: {str(e)}")
            return []
    
    return all_videos


async def search_videos_by_actor(actress_name: str) -> List[Dict[str, str]]:
    """
    Tìm kiếm video theo tên diễn viên
    
    Logic:
    1. Search qua DuckDuckGo với "javtiful + actress_name"
    2. Lấy slug từ kết quả đầu tiên
    3. Crawl tất cả video
    """
    print(f"\n{'='*80}")
    print(f"🔍 TÌM KIẾM: {actress_name}")
    print(f"{'='*80}")
    
    # BƯỚC 1: Search qua DuckDuckGo
    slug = await search_actress_via_duckduckgo(actress_name)
    
    if not slug:
        print("\n❌ Không thể tìm thấy actress!")
        return []
    
    # BƯỚC 2: Crawl videos
    print(f"\n{'='*80}")
    print(f"📥 CRAWL VIDEO")
    print(f"{'='*80}")
    
    videos = await crawl_actress_by_slug(slug)
    
    return videos


def display_results(videos: List[Dict[str, str]], actress_name: str):
    """
    Hiển thị kết quả tìm kiếm
    """
    print("\n" + "=" * 80)
    print(f"🎬 KẾT QUẢ: {actress_name.upper()}")
    print("=" * 80)
    
    if not videos:
        print("\n❌ Không tìm thấy video!")
        print("\n💡 Gợi ý:")
        print("  - Kiểm tra tên diễn viên")
        print("  - Ví dụ: 'Melody Marks', 'Yui Hatano'")
        return
    
    print(f"\n✅ Tìm thấy {len(videos)} video")
    print(f"📄 Hiển thị toàn bộ video\n")
    
    for idx in range(len(videos)):
        video = videos[idx]
        print(f"{idx + 1}. {video['title']}")
        print(f"   🔗 {video['link']}")
        print()
    
    print("=" * 80)


def main():
    """
    Hàm chính
    """
    print("=" * 80)
    print("🎥 JAVTIFUL VIDEO CRAWLER v3.1")
    print("   ✨ Fuzzy Search với DuckDuckGo")
    print("=" * 80)
    print("\n📝 Tìm kiếm video theo tên diễn viên")
    print("💡 Hỗ trợ tên sai chính tả (ví dụ: 'melod mar' → 'melody marks')")
    print("💡 Ví dụ: Melody Marks, Yui Hatano, Eimi Fukada")
    print("-" * 80)
    
    actress_name = input("\n👤 Nhập tên diễn viên: ").strip()
    
    if not actress_name:
        print("\n❌ Vui lòng nhập tên diễn viên!")
        return
    
    try:
        videos = asyncio.run(search_videos_by_actor(actress_name))
        display_results(videos, actress_name)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Đã hủy!")
    except Exception as e:
        print(f"\n❌ Lỗi: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
