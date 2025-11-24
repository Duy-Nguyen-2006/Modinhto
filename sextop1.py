
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler sextop1.movie: tim video theo ten dien vien, tra ve list dict.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict
from urllib.parse import quote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

def normalize_name_to_url(name: str) -> str:
    """Chuyen ten dien vien thanh slug cho URL sextop1."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "-")
    name = "".join(char for char in name if char.isalnum() or char == "-")
    return name

async def search_actress_on_duckduckgo(crawler: AsyncWebCrawler, actor_name: str) -> str:
    """Tim kiem URL chinh xac cua dien vien qua DuckDuckGo."""
    try:
        query = f"site:sextop1.movie/actresses {actor_name}"
        search_url = f"https://duckduckgo.com/html/?q={quote(query)}"
        
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=5)
        result = await crawler.arun(url=search_url, config=run_config)
        
        if not result.success:
            # Neu khong tim duoc, tra ve URL mac dinh
            return f"https://sextop1.movie/actresses/{normalize_name_to_url(actor_name)}"
        
        soup = BeautifulSoup(result.html, "html.parser")
        
        # Tim ket qua dau tien chua /actresses/
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "sextop1.movie/actresses/" in href:
                match = re.search(r'https?://sextop1\.movie/actresses/([^&?\s/]+)', href)
                if match:
                    actress_slug = match.group(1)
                    return f"https://sextop1.movie/actresses/{actress_slug}"
        
        # Neu khong tim thay, tra ve URL mac dinh
        return f"https://sextop1.movie/actresses/{normalize_name_to_url(actor_name)}"
    except Exception:
        return f"https://sextop1.movie/actresses/{normalize_name_to_url(actor_name)}"

async def crawl_sextop1_actress_page(crawler: AsyncWebCrawler, actress_url: str, page: int) -> List[Dict[str, str]]:
    """Crawl mot trang cua dien vien tren sextop1 va tra ve video list."""
    if page > 1:
        page_url = f"{actress_url}?page={page}"
    else:
        page_url = actress_url
    
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=page_url, config=run_config)
    if not result.success:
        return []

    soup = BeautifulSoup(result.html, "html.parser")
    video_blocks = soup.find_all("div", class_="item")
    
    videos: List[Dict[str, str]] = []
    seen_links = set()

    for block in video_blocks:
        try:
            link_tags = block.find_all("a", href=True)
            for link_tag in link_tags:
                video_link = link_tag.get("href", "")
                if not video_link or "/phim-sex/" not in video_link:
                    continue

                if video_link.startswith("/"):
                    video_link = f"https://sextop1.movie{video_link}"
                elif not video_link.startswith("http"):
                    video_link = f"https://sextop1.movie/{video_link}"

                if video_link in seen_links:
                    continue
                seen_links.add(video_link)

                video_title = link_tag.get("title", "").strip()
                if not video_title:
                    title_h4 = link_tag.find("h4", class_="item__title")
                    if title_h4:
                        video_title = title_h4.get_text(strip=True)
                
                if not video_title or len(video_title) < 3:
                    video_title = "No title"

                videos.append({"source": "Sextop1", "title": video_title[:200], "link": video_link})
        except Exception:
            continue

    return videos

async def search_videos_by_actor(actor_name: str) -> List[Dict[str, str]]:
    """Tim kiem video cua dien vien tren sextop1 qua DuckDuckGo va crawl nhieu trang."""
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Buoc 1: Tim kiem qua DuckDuckGo de lay URL chinh xac
            actress_url = await search_actress_on_duckduckgo(crawler, actor_name)
            
            # Buoc 2: Crawl tung trang (toi da 10 trang)
            all_videos: List[Dict[str, str]] = []
            seen_all = set()
            
            for page in range(1, 11):
                videos = await crawl_sextop1_actress_page(crawler, actress_url, page)
                
                # Loc video trung lap
                new_videos = []
                for video in videos:
                    if video['link'] not in seen_all:
                        seen_all.add(video['link'])
                        new_videos.append(video)
                
                # Dung neu trang khong co video moi
                if not new_videos:
                    break
                
                all_videos.extend(new_videos)
                
                # Dung neu da den trang 10
                if page == 10:
                    break
            
            return all_videos
    except Exception:
        return []

def _print_results(results: List[Dict[str, str]]) -> None:
    """In ket qua ra console."""
    if not results:
        print("Khong tim thay video.")
        return
    for idx, item in enumerate(results, 1):
        print(f"{idx}. [{item.get('source', '')}] {item.get('title', '')} - {item.get('link', '')}")

async def _main() -> None:
    actor = input("Nhap ten dien vien: ").strip()
    if not actor:
        print("Ten dien vien khong duoc de trong.")
        return
    print("Dang tim kiem, vui long doi...")
    results = await search_videos_by_actor(actor)
    _print_results(results)

if __name__ == "__main__":
    asyncio.run(_main())
