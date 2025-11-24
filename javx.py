#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler javs.cc: tim video theo ten dien vien, tra ve list dict.
LAP QUA TAT CA CAC TRANG DE LAY 100% VIDEO.
SU DUNG DUCKDUCKGO DE TIM SLUG CHINH XAC.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlparse, parse_qs, unquote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_name_to_url(name: str) -> str:
    """Chuyen ten dien vien thanh slug cho URL javs.cc."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "+")
    name = "".join(char for char in name if char.isalnum() or char in ["+", "-"])
    return name


async def search_javs_url_via_duckduckgo(actress_name: str) -> Optional[str]:
    """Tim URL javs.cc qua DuckDuckGo."""
    search_query = f"javs.cc {actress_name}"
    ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}"
    print(f"🔍 Tim URL qua DuckDuckGo: {ddg_url}")

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
            
            # Decode URL neu co uddg parameter
            if "uddg=" in href:
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                real_url = unquote(params.get("uddg", [""])[0]) if params.get("uddg") else href
            else:
                real_url = href

            # Tim URL javs.cc
            if "javs.cc" in real_url.lower():
                candidates.append({"url": real_url, "text": text})

        if not candidates:
            print("❌ Khong tim thay link javs.cc trong ket qua.")
            return None

        first = candidates[0]
        print(f"✅ Tim thay: {first['text']}")
        print(f"✅ URL: {first['url']}")
        return first["url"]
    except Exception as exc:
        print(f"❌ Loi khi search DuckDuckGo: {exc}")
        return None


def extract_max_page_number(soup: BeautifulSoup) -> int:
    """Tim so trang toi da tu pagination."""
    max_page = 1

    # Tim tat ca link pagination
    pagination_links = soup.find_all("a", href=lambda x: x and ("page" in x or "/page/" in x))
    
    for link in pagination_links:
        href = link.get("href", "")
        # Pattern: /page/2/ hoac ?page=2
        page_match = re.search(r'/(page)/(\d+)|[?&]page=(\d+)', href)
        if page_match:
            page_num = int(page_match.group(2) or page_match.group(3))
            max_page = max(max_page, page_num)

    # Kiem tra pagination div
    pagination_divs = soup.find_all(["div", "nav"], class_=lambda x: x and ("pag" in x.lower() if x else False))
    for div in pagination_divs:
        text = div.get_text()
        numbers = re.findall(r'\b(\d+)\b', text)
        for num in numbers:
            if int(num) < 100:  # Tranh nhầm với view count
                max_page = max(max_page, int(num))

    return min(max_page, 10)  # Gioi han toi da 10 trang


async def crawl_single_page(crawler: AsyncWebCrawler, page_url: str) -> List[Dict[str, str]]:
    """Crawl mot trang va tra ve danh sach video."""
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=page_url, config=run_config)
    
    if not result.success:
        print(f"❌ Khong crawl duoc: {page_url}")
        return []

    soup = BeautifulSoup(result.html, "html.parser")
    video_items = soup.find_all("article", class_="loop-video")

    videos: List[Dict[str, str]] = []
    seen_links = set()

    for item in video_items:
        try:
            link_tag = item.find("a")
            if not link_tag:
                continue

            video_link = link_tag.get("href", "")
            title = link_tag.get("title", "") or link_tag.get_text(strip=True)

            if not video_link or not title or video_link in seen_links:
                continue

            if "javs.cc" not in video_link:
                continue

            seen_links.add(video_link)
            videos.append({"source": "JAVS.CC", "title": title.strip()[:200], "link": video_link})
        except Exception:
            continue

    return videos


async def crawl_javs_all_pages(crawler: AsyncWebCrawler, base_url: str) -> List[Dict[str, str]]:
    """Crawl TAT CA cac trang va tra ve toan bo video."""
    print(f"\n🚀 Bat dau crawl: {base_url}")

    # Crawl trang dau tien
    print(f"📄 Crawl trang 1...")
    all_videos = await crawl_single_page(crawler, base_url)
    print(f"✅ Trang 1: Tim thay {len(all_videos)} video")
    pages_crawled = 1

    if len(all_videos) == 0:
        print("Trang 1 khong co video, dung crawl.")
        return []

    # Lay noi dung trang dau de phat hien pagination
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=base_url, config=run_config)

    if result.success:
        soup = BeautifulSoup(result.html, "html.parser")
        max_page = extract_max_page_number(soup)
        print(f"📊 Phat hien {max_page} trang")

        # Lap qua cac trang con lai
        if max_page > 1:
            # Xac dinh format URL pagination
            # javs.cc co the dung /page/2/ hoac ?page=2
            separator = "&" if "?" in base_url else "?"
            
            for page_num in range(2, max_page + 1):
                # Thu 2 format pho bien
                page_url = f"{base_url}{separator}page={page_num}"
                print(f"📄 Crawl trang {page_num}/{max_page}...")

                page_videos = await crawl_single_page(crawler, page_url)
                print(f"✅ Trang {page_num}: Tim thay {len(page_videos)} video")

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


async def search_videos_by_actor(actress_name: str) -> List[Dict[str, str]]:
    """Tim kiem TAT CA video cua dien vien tren javs.cc."""
    try:
        # Buoc 1: Tim URL qua DuckDuckGo
        actress_url = await search_javs_url_via_duckduckgo(actress_name)
        
        if not actress_url:
            # Fallback: Dung search query thong thuong
            search_query = normalize_name_to_url(actress_name)
            actress_url = f"https://javs.cc/?s={search_query}"
            print(f"⚠️ Dung search URL tu normalize: {actress_url}")

        # Buoc 2: Crawl tat ca cac trang
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            return await crawl_javs_all_pages(crawler, actress_url)
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
    print("JAVS.CC VIDEO CRAWLER - LAY TAT CA VIDEO CUA DIEN VIEN")
    print("="*80)

    actress = input("\nNhap ten dien vien: ").strip()
    if not actress:
        print("❌ Ten dien vien khong duoc de trong.")
        return

    print("\n🔄 Dang tim kiem va crawl tat ca cac trang, vui long doi...\n")
    results = await search_videos_by_actor(actress)
    _print_results(results)


if __name__ == "__main__":
    asyncio.run(_main())
