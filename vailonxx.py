#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler vailonxx.co: tim video theo ten dien vien, tra ve list dict.
LAP QUA TAT CA CAC TRANG DE LAY 100% VIDEO.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlparse, parse_qs, unquote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

def normalize_name_to_url(name: str) -> str:
    """Chuyen ten dien vien thanh slug cho URL Vailonxx."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "-")
    name = "".join(char for char in name if char.isalnum() or char == "-")
    return name

async def search_vailonxx_slug_via_duckduckgo(actor_name: str) -> Optional[str]:
    """Tim slug Vailonxx qua DuckDuckGo."""
    search_query = f"vailonxx {actor_name}"
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

            m = re.search(r"vailonxx\.[a-z]+/([^/?#]+)", real_url, re.IGNORECASE)
            if m:
                slug = m.group(1)
                if slug not in ["", "video", "search", "category", "tag", "videos", "page"]:
                    candidates.append({"slug": slug, "url": real_url, "text": text})

        if not candidates:
            print("❌ Khong tim thay link vailonxx trong ket qua.")
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
    """Tim so trang toi da tu pagination. GIOI HAN TOI DA 10 TRANG."""
    max_page = 1
    
    pagination_links = soup.find_all("a", href=lambda x: x and "/page/" in x)
    for link in pagination_links:
        href = link.get("href", "")
        page_match = re.search(r"/page/(\d+)", href)
        if page_match:
            page_num = int(page_match.group(1))
            max_page = max(max_page, page_num)
    
    pagination_divs = soup.find_all(["div", "span", "nav", "ul"], class_=lambda x: x and "pag" in x.lower() if x else False)
    for div in pagination_divs:
        text = div.get_text()
        numbers = re.findall(r'\b(\d+)\b', text)
        for num in numbers:
            if int(num) > max_page and int(num) < 1000:
                max_page = int(num)
    
    if max_page > 10:
        print(f"⚠️ Gioi han tim kiem tu {max_page} xuong 10 trang")
        max_page = 10
    
    return max_page

async def crawl_single_page(crawler: AsyncWebCrawler, page_url: str) -> List[Dict[str, str]]:
    """Crawl mot trang va tra ve danh sach video."""
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=page_url, config=run_config)
    
    if not result.success:
        print(f"❌ Khong crawl duoc: {page_url}")
        return []

    soup = BeautifulSoup(result.html, "html.parser")
    
    video_items = soup.find_all("div", class_="post-item")
    if not video_items:
        video_items = soup.find_all("a", href=lambda x: x and "/video/" in x)

    videos: List[Dict[str, str]] = []
    seen_links = set()

    for item in video_items:
        try:
            if item.name == "a":
                link_tag = item
            else:
                link_tag = item.find("a", class_="plain")
            
            if not link_tag:
                continue

            video_link = link_tag.get("href", "")
            if not video_link:
                continue

            if video_link.startswith("/"):
                video_link = f"https://vailonxx.co{video_link}"
            elif not video_link.startswith("http"):
                video_link = f"https://vailonxx.co/{video_link}"

            if video_link in seen_links or "vailonxx.co" not in video_link:
                continue

            title = ""
            title_tag = link_tag.find("h3", class_="post-title")
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            if not title:
                title = link_tag.get("title", "").strip()
            
            if not title:
                title = link_tag.get_text(strip=True)

            if not title or len(title) < 3:
                continue

            seen_links.add(video_link)
            videos.append({"source": "Vailonxx", "title": title[:200], "link": video_link})
        except Exception:
            continue

    return videos

async def crawl_vailonxx_actor_all_pages(crawler: AsyncWebCrawler, actor_url: str) -> List[Dict[str, str]]:
    """Crawl TAT CA cac trang cua actress va tra ve toan bo video."""
    print(f"\n🚀 Bat dau crawl: {actor_url}")
    
    print(f"📄 Crawl trang 1...")
    all_videos = await crawl_single_page(crawler, actor_url)
    print(f"✅ Trang 1: Tim thay {len(all_videos)} video")
    pages_crawled = 1

    if len(all_videos) == 0:
        print("❌ Trang 1 khong co video, dung crawl.")
        return []
    
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=actor_url, config=run_config)
    
    if result.success:
        soup = BeautifulSoup(result.html, "html.parser")
        max_page = extract_max_page_number(soup)
        print(f"📊 Phat hien {max_page} trang")
        
        if max_page > 1:
            for page_num in range(2, max_page + 1):
                if actor_url.endswith("/"):
                    page_url = f"{actor_url}page/{page_num}/"
                else:
                    page_url = f"{actor_url}/page/{page_num}/"
                
                print(f"📄 Crawl trang {page_num}/{max_page}...")
                
                page_videos = await crawl_single_page(crawler, page_url)
                print(f"✅ Trang {page_num}: Tim thay {len(page_videos)} video")
                
                if len(page_videos) == 0:
                    print(f"❌ Trang {page_num} khong co video, dung crawl.")
                    break

                all_videos.extend(page_videos)
                pages_crawled += 1
                
                await asyncio.sleep(1)
    
    unique_videos = []
    seen_links = set()
    for video in all_videos:
        if video["link"] not in seen_links:
            seen_links.add(video["link"])
            unique_videos.append(video)
    
    print(f"\n✅ TONG KET: {len(unique_videos)} video tu {pages_crawled} trang")
    return unique_videos

async def search_videos_by_actor(actor_name: str) -> List[Dict[str, str]]:
    """Tim kiem TAT CA video cua dien vien tren vailonxx.co."""
    try:
        slug = await search_vailonxx_slug_via_duckduckgo(actor_name)
        if not slug:
            slug = normalize_name_to_url(actor_name)
            print(f"⚠️ Dung slug tu normalize: {slug}")

        actor_url = f"https://vailonxx.co/{slug}/"
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            return await crawl_vailonxx_actor_all_pages(crawler, actor_url)
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
    print("VAILONXX.CO VIDEO CRAWLER - LAY TAT CA VIDEO CUA DIEN VIEN")
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
