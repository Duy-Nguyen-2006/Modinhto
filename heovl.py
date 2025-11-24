#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler HeoVL: tim video theo ten dien vien, tra ve list dict cho backend.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse, parse_qs, unquote, quote_plus

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_name_to_url(name: str) -> str:
    """Chuyen doi ten dien vien thanh format URL cua HeoVL."""
    name = unicodedata.normalize("NFD", name or "")
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "-")
    name = "".join(char for char in name if char.isalnum() or char == "-")
    return name


async def search_actress_slug_via_duckduckgo(actress_name: str) -> Optional[str]:
    """Tim slug actress qua DuckDuckGo (lay tu ket qua heovl.*)."""
    search_query = f"heovl {actress_name}"
    ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}"
    print(f"Tim slug qua DuckDuckGo: {ddg_url}")

    try:
        async with AsyncWebCrawler(verbose=False, headless=True) as crawler:
            result = await crawler.arun(
                url=ddg_url,
                bypass_cache=True,
                delay_before_return_html=2.0
            )

        if not result.success:
            print("Khong lay duoc ket qua DuckDuckGo.")
            return None

        soup = BeautifulSoup(result.html, "html.parser")
        result_links = soup.find_all("a", class_="result__a")
        if not result_links:
            print("DuckDuckGo khong tra ve ket qua nao.")
            return None

        candidates = []
        for link in result_links:
            href = link.get("href", "")
            text = link.get_text().strip()

            if "uddg=" in href:
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                if "uddg" in params:
                    real_url = unquote(params["uddg"][0])
                else:
                    real_url = href
            else:
                real_url = href

            m = re.search(r"heovl\.[a-z]+/actresses/([^/?#]+)", real_url, re.IGNORECASE)
            if m:
                slug = m.group(1)
                candidates.append({"slug": slug, "url": real_url, "text": text})

        if not candidates:
            print("Khong tim thay link heovl trong ket qua.")
            return None

        first = candidates[0]
        print(f"Tim thay actress: {first['text']}")
        print(f"Slug: {first['slug']}")
        print(f"Source: {first['url']}")
        return first["slug"]

    except Exception as exc:
        print(f"Loi khi search DuckDuckGo: {exc}")
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
    Tra ve danh sach video theo ten dien vien.

    Output: [{'source': 'HeoVL', 'title': str, 'link': str}, ...]
    """
    try:
        slug = await search_actress_slug_via_duckduckgo(actress_name)
        if not slug:
            slug = normalize_name_to_url(actress_name)
            print(f"Dung slug tu normalize: {slug}")

        actress_url = f"https://heovl.moe/actresses/{slug}"

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
            return await crawl_heovl_actress(crawler, actress_url)
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
