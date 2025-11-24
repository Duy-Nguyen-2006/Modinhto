#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler SexTop1.movie: Tim video theo ten dien vien su dung Crawl4AI
Tinh nang:
- Tu dong tim ten dung qua DuckDuckGo
- Thu nhieu dang URL (first-last, last-first)
- Crawl toi da 10 trang
- Loai bo trung lap
"""

import asyncio
import re
import unicodedata
from urllib.parse import urlparse, parse_qs, unquote
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_name_to_url(name: str) -> str:
    """Chuyen ten dien vien thanh slug cho URL."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "-")
    name = "".join(char for char in name if char.isalnum() or char == "-")
    name = re.sub(r'-+', '-', name).strip('-')
    return name


def search_actress_on_duckduckgo(actress_name: str) -> Optional[str]:
    """Tim ten dung cua dien vien qua DuckDuckGo."""
    try:
        print(f"[DuckDuckGo] Tim kiem: {actress_name}")
        
        query = f"site:sextop1.movie {actress_name} actresses"
        search_url = "https://html.duckduckgo.com/html/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, params={"q": query}, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        results = soup.find_all('a', class_='result__a')
        
        for link_tag in results:
            raw_href = link_tag.get("href") or ""
            target_url = None
            
            if raw_href.startswith("//duckduckgo.com/l/?"):
                parsed = urlparse("https:" + raw_href)
                target_url = parse_qs(parsed.query).get("uddg", [None])[0]
                if target_url:
                    target_url = unquote(target_url)
            elif raw_href.startswith("http"):
                target_url = raw_href
            
            if not target_url or "sextop1.movie" not in target_url:
                continue
            
            parsed_target = urlparse(target_url)
            path = parsed_target.path
            
            if "/actresses/" in path:
                slug = path.split("/actresses/", 1)[-1].strip("/").split("/")[0]
                slug = normalize_name_to_url(slug)
                print(f"[DuckDuckGo] URL: {target_url}")
                print(f"[DuckDuckGo] Slug: {slug}")
                return slug
            
            if "/search/" in path:
                slug = path.split("/search/", 1)[-1].strip("/").split("/")[0]
                slug = normalize_name_to_url(slug)
                print(f"[DuckDuckGo] URL tim kiem: {target_url}")
                print(f"[DuckDuckGo] Slug tim kiem: {slug}")
                return slug
        
        return None
        
    except Exception as e:
        print(f"[DuckDuckGo] Loi: {e}")
        return None


async def crawl_sextop1_page(crawler: AsyncWebCrawler, page_url: str) -> List[Dict[str, str]]:
    """Crawl mot trang cua dien vien va tra ve video list."""
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=page_url, config=run_config)
    
    if not result.success:
        return []

    soup = BeautifulSoup(result.html, "html.parser")
    
    # Tim container chua video
    items_container = soup.find('div', class_='items')
    if not items_container:
        return []
    
    # Tim tat ca video items
    video_items = items_container.find_all('div', class_='item')

    videos: List[Dict[str, str]] = []

    for item in video_items:
        try:
            # Tim the <a> co class "item__title"
            link_tag = item.find('a', class_='item__title')
            
            if not link_tag:
                continue
            
            video_link = link_tag.get("href", "")
            if not video_link:
                continue

            if video_link.startswith("/"):
                video_link = f"https://sextop1.movie{video_link}"
            elif not video_link.startswith("http"):
                continue

            # Lay tieu de
            title_tag = link_tag.find('h4', class_='item__title')
            if title_tag:
                video_title = title_tag.get_text(strip=True)
            else:
                video_title = link_tag.get_text(strip=True)
            
            if not video_title or len(video_title) < 2:
                video_title = "No title"

            videos.append({
                "source": "SexTop1",
                "title": video_title[:200],
                "link": video_link
            })
            
        except Exception:
            continue

    return videos


async def try_actress_url(crawler: AsyncWebCrawler, url: str) -> bool:
    """Kiem tra xem URL co hop le khong."""
    try:
        videos = await crawl_sextop1_page(crawler, url)
        return len(videos) > 0
    except Exception:
        return False


async def search_videos_by_actor(actor_name: str, max_pages: int = 10) -> List[Dict[str, str]]:
    """Tim kiem video cua dien vien tren SexTop1.movie."""
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print(f"\n{'='*60}")
            print(f"CRAWL DIEN VIEN: {actor_name}")
            print(f"{'='*60}\n")
            
            # Thu dung DuckDuckGo tim ten dung
            correct_slug = search_actress_on_duckduckgo(actor_name)
            
            if not correct_slug:
                print(f"[URL] Dung ten nhap: {actor_name}")
                correct_slug = normalize_name_to_url(actor_name)
            
            # Tao danh sach URL de thu
            base_url = "https://sextop1.movie"
            urls_to_try = [f"{base_url}/actresses/{correct_slug}"]
            
            # Thu dao nguoc (last-first)
            parts = correct_slug.split('-')
            if len(parts) >= 2:
                reversed_slug = '-'.join(reversed(parts))
                urls_to_try.append(f"{base_url}/actresses/{reversed_slug}")
            
            # Thu trang tim kiem noi site (phong truong hop khong co trang actress)
            search_slug = correct_slug or normalize_name_to_url(actor_name)
            urls_to_try.append(f"{base_url}/search/{search_slug}")
            
            # Loai bo trung lap, giu nguyen thu tu thu nghiem
            urls_to_try = list(dict.fromkeys(urls_to_try))
            
            print(f"[URL] Thu cac URL:")
            for idx, url in enumerate(urls_to_try, 1):
                print(f"  {idx}. {url}")
            
            # Tim URL hop le
            valid_url = None
            for url in urls_to_try:
                print(f"\n[Test] {url}")
                if await try_actress_url(crawler, url):
                    print(f"[Test] ✓ URL hop le!")
                    valid_url = url
                    break
                else:
                    print(f"[Test] ✗ Khong co video")
            
            if not valid_url:
                print("\n[LOI] Khong tim thay URL hop le!")
                print("Vui long kiem tra lai ten dien vien.")
                return []
            
            print(f"\n[OK] Su dung: {valid_url}\n")
            
            # Crawl cac trang
            all_videos: List[Dict[str, str]] = []
            seen_links = set()
            
            for page_num in range(1, max_pages + 1):
                try:
                    if page_num == 1:
                        page_url = valid_url
                    else:
                        page_url = f"{valid_url}?page={page_num}"
                    
                    print(f"[Trang {page_num}] {page_url}")
                    
                    page_videos = await crawl_sextop1_page(crawler, page_url)
                    
                    if not page_videos:
                        print(f"[Trang {page_num}] Khong co video. Dung lai.")
                        break
                    
                    # Loc trung lap
                    new_count = 0
                    for video in page_videos:
                        if video['link'] not in seen_links:
                            seen_links.add(video['link'])
                            all_videos.append(video)
                            new_count += 1
                    
                    print(f"[Trang {page_num}] +{new_count} video moi")
                    
                    if new_count == 0:
                        print(f"[Trang {page_num}] Khong con video moi. Dung lai.")
                        break
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"[Trang {page_num}] Loi: {e}")
                    continue
            
            return all_videos
            
    except Exception as e:
        print(f"[LOI] {e}")
        return []


def _print_results(results: List[Dict[str, str]]) -> None:
    """In ket qua ra console."""
    if not results:
        print("\n" + "="*60)
        print("KHONG TIM THAY VIDEO!")
        print("="*60)
        return
    
    print("\n" + "="*60)
    print(f"TONG: {len(results)} VIDEO")
    print("="*60 + "\n")
    
    for idx, item in enumerate(results, 1):
        print(f"{idx}. [{item.get('source', '')}] {item.get('title', '')}")
        print(f"   {item.get('link', '')}\n")


async def _main() -> None:
    """Ham main."""
    print("\n" + "="*60)
    print("SEXTOP1.MOVIE CRAWLER")
    print("="*60)
    
    actor = input("\nNhap ten dien vien: ").strip()
    if not actor:
        print("\nTen dien vien khong duoc de trong!")
        return
    
    print("\nDang crawl, vui long doi...")
    results = await search_videos_by_actor(actor, max_pages=10)
    _print_results(results)


if __name__ == "__main__":
    asyncio.run(_main())
