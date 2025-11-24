#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler vailonxx.co: tim video theo ten dien vien cho backend.
Co tim kiem qua DuckDuckGo de lay slug chinh xac va thu nhieu bien the.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlparse, parse_qs, unquote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

def normalize_name(name: str) -> str:
    """Chuan hoa ten thanh slug don gian."""
    name = unicodedata.normalize("NFD", name)
    name = name.encode("ascii", "ignore").decode("utf-8")
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"[\s]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name

def generate_slug_variations(slug: str) -> List[str]:
    """
    Tao cac bien the slug.
    Vi du: "eimi-fukada" -> ["eimi-fukada", "fukada-eimi"]
    """
    variations = [slug]
    parts = slug.split("-")
    
    if len(parts) >= 2:
        # Dao nguoc: eimi-fukada -> fukada-eimi
        reversed_slug = "-".join(reversed(parts))
        if reversed_slug != slug:
            variations.append(reversed_slug)
    
    return variations

async def search_vailonxx_slug_via_duckduckgo(actor_name: str) -> List[str]:
    """Tim cac slug vailonxx qua DuckDuckGo, tra ve list cac slug."""
    search_query = f"vailonxx {actor_name}"
    ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}"
    print(f"🔍 Tim slug qua DuckDuckGo: {search_query}")

    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=2.0)
            result = await crawler.arun(url=ddg_url, config=run_config)

        if not result.success:
            print("❌ Khong lay duoc ket qua DuckDuckGo.")
            return []

        soup = BeautifulSoup(result.html, "html.parser")
        links = soup.find_all("a", class_="result__a")
        if not links:
            print("❌ DuckDuckGo khong tra ve ket qua nao.")
            return []

        slugs = []
        for link in links:
            href = link.get("href", "")
            text = link.get_text().strip()
            if "uddg=" in href:
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                real_url = unquote(params.get("uddg", [""])[0]) if params.get("uddg") else href
            else:
                real_url = href

            # Tim pattern vailonxx.co/{slug}
            m = re.search(r"vailonxx\.[a-z]+/([^/?#]+)", real_url, re.IGNORECASE)
            if m:
                slug = m.group(1)
                # Bo qua cac trang khong phai actress
                if slug not in ["", "video", "search", "category", "tag", "videos"]:
                    print(f"  → Tim thay slug: {slug}")
                    slugs.append(slug)

        if slugs:
            print(f"✅ Tim thay {len(slugs)} slug tu DuckDuckGo")
        else:
            print("❌ Khong tim thay slug vailonxx nao")
        
        return slugs
    except Exception as exc:
        print(f"❌ Loi khi search DuckDuckGo: {exc}")
        return []

async def try_crawl_with_slug(crawler: AsyncWebCrawler, slug: str) -> List[Dict[str, str]]:
    """Thu crawl voi mot slug."""
    try:
        url = f"https://vailonxx.co/{slug}/"
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
        result = await crawler.arun(url=url, config=run_config)

        if not result.success:
            return []

        soup = BeautifulSoup(result.html, "html.parser")
        video_items = soup.find_all("div", class_="post-item")
        if not video_items:
            return []

        videos: List[Dict[str, str]] = []
        seen = set()

        for item in video_items:
            link_tag = item.find("a", class_="plain")
            if not link_tag:
                continue

            video_url = link_tag.get("href", "")
            if not video_url or video_url in seen or "vailonxx.co" not in video_url:
                continue

            title_tag = link_tag.find("h3", class_="post-title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            if not title:
                continue

            seen.add(video_url)
            videos.append({"source": "Vailonxx", "title": title, "link": video_url})

        return videos
    except Exception:
        return []

async def search_videos_by_actor(actress_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.
    Tim slug qua DuckDuckGo, thu cac bien the cho den khi tim thay.

    Output: [{'source': 'Vailonxx', 'title': str, 'link': str}, ...]
    """
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            
            # Buoc 1: Tim slug qua DuckDuckGo
            ddg_slugs = await search_vailonxx_slug_via_duckduckgo(actress_name)
            
            # Buoc 2: Tao danh sach slug de thu
            slugs_to_try = []
            
            # Them cac slug tu DuckDuckGo va bien the cua chung
            for slug in ddg_slugs:
                slugs_to_try.extend(generate_slug_variations(slug))
            
            # Them slug tu normalize input va bien the
            normalized_slug = normalize_name(actress_name)
            slugs_to_try.extend(generate_slug_variations(normalized_slug))
            
            # Loai bo trung lap va giu thu tu
            seen = set()
            unique_slugs = []
            for slug in slugs_to_try:
                if slug not in seen:
                    seen.add(slug)
                    unique_slugs.append(slug)
            
            print(f"\n🔄 Se thu {len(unique_slugs)} slug: {unique_slugs}\n")
            
            # Buoc 3: Thu tung slug cho den khi tim thay video
            for idx, slug in enumerate(unique_slugs, 1):
                print(f"📝 [{idx}/{len(unique_slugs)}] Thu slug: {slug}")
                videos = await try_crawl_with_slug(crawler, slug)
                
                if videos:
                    print(f"✅ Tim thay {len(videos)} video voi slug: {slug}\n")
                    return videos
                else:
                    print(f"❌ Khong co video")
                
                # Delay nho giua cac lan thu
                if idx < len(unique_slugs):
                    await asyncio.sleep(0.5)
            
            print("\n❌ Da thu tat ca slug nhung khong tim thay video")
            return []
            
    except Exception as exc:
        print(f"❌ Loi: {exc}")
        return []

def _print_results(results: List[Dict[str, str]]) -> None:
    """In ket qua ra console."""
    if not results:
        print("Khong tim thay video.")
        return
    for idx, item in enumerate(results, 1):
        print(f"{idx}. [{item.get('source', '')}] {item.get('title', '')} - {item.get('link', '')}")

async def _main() -> None:
    actress = input("Nhap ten dien vien: ").strip()
    if not actress:
        print("Ten dien vien khong duoc de trong.")
        return
    print("Dang tim kiem, vui long doi...")
    results = await search_videos_by_actor(actress)
    _print_results(results)

if __name__ == "__main__":
    asyncio.run(_main())
