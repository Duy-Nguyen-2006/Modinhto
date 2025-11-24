
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler xvideos.com: tim video theo ten dien vien, tra ve list dict cho backend.
Co chuan hoa ten qua DuckDuckGo.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlparse, parse_qs, unquote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_name_to_url(name: str) -> str:
    """Chuan hoa ten dien vien thanh slug cho URL XVideos."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "-")
    name = "".join(char for char in name if char.isalnum() or char == "-")
    return name


async def search_xvideos_slug_via_duckduckgo(actor_name: str) -> Optional[str]:
    """Tim slug pornstar XVideos qua DuckDuckGo."""
    search_query = f"xvideos pornstars {actor_name}"
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

            # Pattern cho xvideos, xvideos2, xvideos3, etc.
            m = re.search(r"xvideos[0-9]*\.[a-z]+/pornstars/([^/?#]+)", real_url, re.IGNORECASE)
            if m:
                slug = m.group(1)
                candidates.append({"slug": slug, "url": real_url, "text": text})

        if not candidates:
            print("❌ Khong tim thay link xvideos trong ket qua.")
            return None

        first = candidates[0]
        print(f"✅ Tim thay actress: {first['text']}")
        print(f"✅ Slug: {first['slug']}")
        print(f"✅ URL: {first['url']}")
        return first["slug"]
    except Exception as exc:
        print(f"❌ Loi khi search DuckDuckGo: {exc}")
        return None


def is_valid_video(video_element) -> bool:
    """Kiem tra video item co title/link hop le khong."""
    try:
        thumb_under = video_element.find("div", class_="thumb-under")
        if not thumb_under:
            return False
        title_element = thumb_under.find("p", class_="title")
        if not title_element:
            return False
        link_element = title_element.find("a")
        if not link_element:
            return False
        title = link_element.get("title", "").strip()
        href = link_element.get("href", "").strip()
        return bool(title and href)
    except Exception:
        return False


async def search_videos_by_actor(actress_name: str, base_url: str = "https://www.xvideos.com") -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.
    Co chuan hoa ten qua DuckDuckGo.

    Output: [{'source': 'XVideos', 'title': str, 'link': str}, ...]
    """
    try:
        # Buoc 1: Tim slug qua DuckDuckGo
        slug = await search_xvideos_slug_via_duckduckgo(actress_name)
        if not slug:
            slug = normalize_name_to_url(actress_name)
            print(f"⚠️ Dung slug tu normalize: {slug}")

        actress_url = f"{base_url}/pornstars/{slug}"
        videos: List[Dict[str, str]] = []
        seen_urls = set()

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                url=actress_url,
                word_count_threshold=10,
                bypass_cache=True,
                js_code="""
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 2000));
                """
            )

        if not result.success:
            return []

        soup = BeautifulSoup(result.html, "html.parser")
        video_items = []
        mozaique = soup.find("div", class_="mozaique")
        if mozaique:
            video_items.extend(mozaique.find_all("div", class_="thumb-block"))

        if not video_items:
            return []

        for video_item in video_items:
            try:
                if not is_valid_video(video_item):
                    continue

                thumb_under = video_item.find("div", class_="thumb-under")
                title_p = thumb_under.find("p", class_="title") if thumb_under else None
                link_tag = title_p.find("a") if title_p else None
                if not link_tag:
                    continue

                title = link_tag.get("title", "").strip()
                video_link = link_tag.get("href", "").strip()
                if not title or not video_link:
                    continue

                if not video_link.startswith("http"):
                    video_link = f"{base_url}{video_link}"

                if video_link in seen_urls:
                    continue
                seen_urls.add(video_link)

                videos.append({"source": "XVideos", "title": title, "link": video_link})
            except Exception:
                continue

        return videos
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
    actress = input("Nhap ten dien vien: ").strip()
    if not actress:
        print("Ten dien vien khong duoc de trong.")
        return
    print("Dang tim kiem, vui long doi...")
    results = await search_videos_by_actor(actress)
    _print_results(results)


if __name__ == "__main__":
    asyncio.run(_main())
