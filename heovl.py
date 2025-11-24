#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler HeoVL: tim video theo ten dien vien su dung DuckDuckGo, tra ve list dict cho backend.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse, parse_qs, quote_plus

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_name_to_url(name: str) -> str:
    """Chuyen doi ten dien vien thanh format URL cua HeoVL."""
    name = unicodedata.normalize("NFD", name or "")
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "-")
    name = "".join(char for char in name if char.isalnum() or char == "-")
    return name


async def search_actress_via_duckduckgo(crawler: AsyncWebCrawler, actress_name: str) -> Optional[str]:
    """
    Tim URL dien vien chinh xac tren HeoVL bang cach search qua DuckDuckGo.
    
    Returns:
        URL slug cua dien vien, hoac None neu khong tim thay
    """
    try:
        # Tao query tim kiem
        search_query = f"{actress_name} site:heovl.moe/actresses"
        encoded_query = quote_plus(search_query)
        duckduckgo_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        print(f"🔍 Tim kiem DuckDuckGo: '{actress_name}'...")
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=5,
            page_timeout=30000,
            js_code="await new Promise(r => setTimeout(r, 3000));",
        )
        
        result = await crawler.arun(url=duckduckgo_url, config=run_config)
        
        if not result.success:
            print("  ✗ Khong ket noi duoc DuckDuckGo")
            return None
        
        soup = BeautifulSoup(result.html, "html.parser")
        
        # Tim tat ca link trong ket qua
        all_links = soup.find_all("a", href=True)
        
        for link in all_links:
            href = link.get("href", "")
            
            # Parse URL redirect cua DuckDuckGo
            if "/l/?uddg=" in href or "uddg=" in href:
                try:
                    parsed = urlparse(href)
                    params = parse_qs(parsed.query)
                    if "uddg" in params:
                        actual_url = params["uddg"][0]
                        href = actual_url
                except:
                    pass
            
            # Kiem tra neu la link heovl.moe/actresses/
            if "heovl.moe/actresses/" in href:
                slug_match = re.search(r"heovl\.moe/actresses/([^/?#]+)", href)
                if slug_match:
                    slug = slug_match.group(1)
                    print(f"  ✓ Tim thay: {slug}")
                    return slug
        
        print("  ✗ Khong tim thay tren DuckDuckGo")
        return None
        
    except Exception as e:
        print(f"  ✗ Loi: {e}")
        return None


async def crawl_heovl_actress(crawler: AsyncWebCrawler, actress_url: str) -> List[Dict[str, str]]:
    """Crawl trang actress cua HeoVL va lay danh sach video."""
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        page_timeout=90000,
        js_code="""
            await new Promise(r => setTimeout(r, 8000));
            window.scrollTo(0, document.body.scrollHeight / 2);
            await new Promise(r => setTimeout(r, 2000));
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(r => setTimeout(r, 2000));
        """,
    )

    result = await crawler.arun(url=actress_url, config=run_config)
    if not result.success:
        return []

    soup = BeautifulSoup(result.html, "html.parser")

    videos_wrapper = soup.select_one("div.videos") or soup
    video_cards = videos_wrapper.select("div.video-box")
    videos: List[Dict[str, str]] = []
    seen_links: set[str] = set()

    for card in video_cards:
        try:
            link_tag = card.select_one("a.video-box__thumbnail__link") or card.find(
                "a", href=lambda x: x and "/videos/" in x
            )
            if not link_tag:
                continue

            raw_link = link_tag.get("href", "")
            if not raw_link:
                continue

            video_link = urljoin("https://heovl.moe", raw_link)
            if video_link in seen_links:
                continue
            seen_links.add(video_link)

            title_tag = link_tag.get("title", "").strip()
            if not title_tag:
                heading = card.select_one(".video-box__heading")
                if heading:
                    title_tag = heading.get_text(strip=True)
            if not title_tag:
                title_tag = link_tag.get_text(strip=True)
            if not title_tag:
                img = link_tag.find("img")
                if img:
                    title_tag = img.get("alt", "").strip() or img.get("title", "").strip()

            if title_tag:
                title_tag = re.sub(r"\d+:\d+(?::\d+)?", "", title_tag).strip()
                title_tag = re.sub(r"[\d.,]+[KM]\s*", "", title_tag).strip()
                title_tag = re.sub(r"\b(HD|4K|FHD|UHD)\b", "", title_tag, flags=re.IGNORECASE).strip()

            if not title_tag or len(title_tag) < 3:
                title_tag = "No title"

            videos.append({"source": "HeoVL", "title": title_tag[:200], "link": video_link})
        except Exception:
            continue

    return videos


async def search_videos_by_actor(actress_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien su dung DuckDuckGo search.

    Output: [{'source': 'HeoVL', 'title': str, 'link': str}, ...]
    """
    try:
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            use_managed_browser=True,
            accept_downloads=False,
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Tim kiem qua DuckDuckGo
            actress_slug = await search_actress_via_duckduckgo(crawler, actress_name)
            
            # Neu khong tim thay, dung cach cu
            if not actress_slug:
                print("⚠️  Thu tim kiem truc tiep...")
                actress_slug = normalize_name_to_url(actress_name)
            
            actress_url = f"https://heovl.moe/actresses/{actress_slug}"
            print(f"🌐 Crawl: {actress_url}")
            
            return await crawl_heovl_actress(crawler, actress_url)
    except Exception as e:
        print(f"❌ Loi: {e}")
        return []


def _print_results(results: List[Dict[str, str]]) -> None:
    """In ket qua ra console."""
    if not results:
        print("\n" + "=" * 80)
        print("❌ KHONG TIM THAY VIDEO")
        print("=" * 80)
        return
    
    print("\n" + "=" * 80)
    print(f"✓ TIM THAY {len(results)} VIDEO")
    print("=" * 80)
    for idx, item in enumerate(results, 1):
        print(f"\n{idx}. [{item.get('source', '')}] {item.get('title', '')}")
        print(f"   🔗 {item.get('link', '')}")
    print("\n" + "=" * 80)


async def _main() -> None:
    print("=" * 80)
    print("         HeoVL VIDEO CRAWLER - DUCKDUCKGO SEARCH")
    print("=" * 80)
    
    actress = input("\n🎬 Ten dien vien: ").strip()
    if not actress:
        print("❌ Ten khong duoc de trong.")
        return
    
    print("\n" + "=" * 80)
    results = await search_videos_by_actor(actress)
    _print_results(results)


if __name__ == "__main__":
    asyncio.run(_main())
