#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler Thumbzilla: tim video theo ten dien vien, tra ve list dict.
LAP QUA TAT CA CAC TRANG DE LAY 100% VIDEO.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import quote, urlparse, parse_qs, unquote, quote_plus

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

def normalize_name_to_url(name: str) -> str:
    """Chuyen ten dien vien thanh slug cho URL Thumbzilla."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "-")
    name = "".join(char for char in name if char.isalnum() or char == "-")
    return name

async def search_thumbzilla_slug_via_duckduckgo(actor_name: str) -> Optional[str]:
    """Tim slug pornstar Thumbzilla qua DuckDuckGo."""
    search_query = f"thumbzilla pornstars {actor_name}"
    ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}"
    print(f"🔍 Tim slug qua DuckDuckGo: {ddg_url}")

    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=2.0)
            result = await crawler.arun(url=ddg_url, config=run_config)

        if not result.success:
            print("❌ Khong lay duoc ket qua DuckDuckGo.")
            return None

        soup = BeautifulSoup(result.html, "html.parser")
        links = soup.find_all("a", class_="result__a")
        if not links:
            print("❌ DuckDuckGo khong tra ve ket qua nao.")
            return None

        candidates = []
        for link in links:
            href = link.get("href", "")
            text = link.get_text().strip()
            if "uddg=" in href:
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                real_url = unquote(params.get("uddg", [""])[0]) if params.get("uddg") else href
            else:
                real_url = href

            m = re.search(r"thumbzilla\.[a-z]+/pornstars/([^/?#]+)", real_url, re.IGNORECASE)
            if m:
                slug = m.group(1)
                candidates.append({"slug": slug, "url": real_url, "text": text})

        if not candidates:
            print("❌ Khong tim thay link thumbzilla trong ket qua.")
            return None

        first = candidates[0]
        print(f"✅ Tim thay actress: {first['text']}")
        print(f"✅ Slug: {first['slug']}")
        print(f"✅ URL: {first['url']}")
        return first["slug"]
    except Exception as exc:
        print(f"❌ Loi khi search DuckDuckGo: {exc}")
        return None

def extract_max_page_number(soup: BeautifulSoup) -> int:
    """Tim so trang toi da tu pagination."""
    pagination_links = soup.find_all("a", href=lambda x: x and "page=" in x)
    max_page = 1
    
    for link in pagination_links:
        href = link.get("href", "")
        page_match = re.search(r"[?&]page=(\d+)", href)
        if page_match:
            page_num = int(page_match.group(1))
            max_page = max(max_page, page_num)
    
    # Kiem tra pagination div hoac span
    pagination_divs = soup.find_all(["div", "span"], class_=lambda x: x and "page" in x.lower() if x else False)
    for div in pagination_divs:
        text = div.get_text()
        numbers = re.findall(r'\b(\d+)\b', text)
        for num in numbers:
            max_page = max(max_page, int(num))
    
    return min(max_page, 10)

async def crawl_single_page(crawler: AsyncWebCrawler, page_url: str) -> List[Dict[str, str]]:
    """Crawl mot trang va tra ve danh sach video."""
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=page_url, config=run_config)
    if not result.success:
        print(f"❌ Khong crawl duoc: {page_url}")
        return []

    soup = BeautifulSoup(result.html, "html.parser")
    video_links = soup.find_all("a", href=lambda x: x and "/video/" in x)

    videos: List[Dict[str, str]] = []
    seen_links = set()

    for link_tag in video_links:
        try:
            video_link = link_tag.get("href", "")
            if not video_link:
                continue

            if video_link.startswith("/"):
                video_link = f"https://www.thumbzilla.com{video_link}"
            elif not video_link.startswith("http"):
                continue

            if video_link in seen_links:
                continue
            seen_links.add(video_link)

            video_title = link_tag.get_text(strip=True)
            duration_pattern = r"\d+:\d+(?::\d+)?(?:HD)?$"
            video_title = re.sub(duration_pattern, "", video_title).strip()
            viewcount_pattern = r"^[\d.,]+[KM]\s*"
            video_title = re.sub(viewcount_pattern, "", video_title).strip()
            if video_title.endswith("HD"):
                video_title = video_title[:-2].strip()
            if not video_title or len(video_title) < 3:
                video_title = "No title"

            videos.append({"source": "Thumbzilla", "title": video_title[:200], "link": video_link})
        except Exception:
            continue

    return videos

async def crawl_thumbzilla_actor_all_pages(crawler: AsyncWebCrawler, actor_url: str) -> List[Dict[str, str]]:
    """Crawl TAT CA cac trang cua pornstar va tra ve toan bo video."""
    print(f"\n🚀 Bat dau crawl: {actor_url}")
    
    # Crawl trang dau tien
    print(f"📄 Crawl trang 1...")
    all_videos = await crawl_single_page(crawler, actor_url)
    print(f"✅ Trang 1: Tim thay {len(all_videos)} video")
    pages_crawled = 1

    # Neu trang dau tien khong co video thi dung lai
    if len(all_videos) == 0:
        print("Trang 1 khong co video, dung crawl.")
        return []
    
    # Lay noi dung trang dau de phat hien pagination
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=actor_url, config=run_config)
    
    if result.success:
        soup = BeautifulSoup(result.html, "html.parser")
        max_page = extract_max_page_number(soup)
        print(f"📊 Phat hien {max_page} trang")
        
        # Lap qua cac trang con lai
        if max_page > 1:
            separator = "?" if "?" not in actor_url else "&"
            
            for page_num in range(2, max_page + 1):
                page_url = f"{actor_url}{separator}page={page_num}"
                print(f"📄 Crawl trang {page_num}/{max_page}...")
                
                page_videos = await crawl_single_page(crawler, page_url)
                print(f"✅ Trang {page_num}: Tim thay {len(page_videos)} video")
                
                # Neu trang nay khong co video thi dung lai
                if len(page_videos) == 0:
                    print("Trang khong co video, dung crawl cac trang tiep theo.")
                    break

                all_videos.extend(page_videos)
                pages_crawled += 1
                
                # Delay nho de tranh bi block
                await asyncio.sleep(1)
    
    # Loai bo trung lap dua tren link
    unique_videos = []
    seen_links = set()
    for video in all_videos:
        if video["link"] not in seen_links:
            seen_links.add(video["link"])
            unique_videos.append(video)
    
    print(f"\n✅ TONG KET: {len(unique_videos)} video tu {pages_crawled} trang")
    return unique_videos

async def search_videos_by_actor(actor_name: str) -> List[Dict[str, str]]:
    """Tim kiem TAT CA video cua dien vien tren Thumbzilla."""
    try:
        # Buoc 1: Tim slug qua DuckDuckGo
        slug = await search_thumbzilla_slug_via_duckduckgo(actor_name)
        if not slug:
            slug = normalize_name_to_url(actor_name)
            print(f"⚠️ Dung slug tu normalize: {slug}")

        # Buoc 2: Crawl tat ca cac trang
        actor_url = f"https://www.thumbzilla.com/pornstars/{slug}"
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            return await crawl_thumbzilla_actor_all_pages(crawler, actor_url)
    except Exception as exc:
        print(f"❌ Loi: {exc}")
        return []

def _print_results(results: List[Dict[str, str]]) -> None:
    """In ket qua ra console."""
    if not results:
        print("\n❌ Khong tim thay video.")
        return
    
    print(f"\n{'='*80}")
    print(f"DANH SACH {len(results)} VIDEO:")
    print(f"{'='*80}\n")
    
    for idx, item in enumerate(results, 1):
        print(f"{idx}. [{item.get('source', '')}] {item.get('title', '')}")
        print(f"   Link: {item.get('link', '')}\n")

async def _main() -> None:
    print("="*80)
    print("THUMBZILLA VIDEO CRAWLER - LAY TAT CA VIDEO CUA DIEN VIEN")
    print("="*80)
    
    actor = input("\nNhap ten dien vien: ").strip()
    if not actor:
        print("❌ Ten dien vien khong duoc de trong.")
        return
    
    print("\n🔄 Dang tim kiem va crawl tat ca cac trang, vui long doi...\n")
    results = await search_videos_by_actor(actor)
    _print_results(results)

if __name__ == "__main__":
    asyncio.run(_main())
