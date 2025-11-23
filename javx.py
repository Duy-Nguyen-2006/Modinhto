#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler javs.cc: tim video theo ten dien vien, tra ve list dict cho backend.
"""

import asyncio
import urllib.parse
from typing import List, Dict

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler


def create_search_url(actress_name: str) -> str:
    """Tao URL tim kiem tu ten dien vien."""
    base_url = "https://javs.cc/"
    search_query = urllib.parse.quote_plus(actress_name)
    return f"{base_url}?s={search_query}"


async def search_videos_by_actor(actress_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.

    Output: [{'source': 'JAVS.CC', 'title': str, 'link': str}, ...]
    """
    try:
        url = create_search_url(actress_name)
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)

        if not result.success:
            return []

        soup = BeautifulSoup(result.html, "html.parser")
        video_items = soup.find_all("article", class_="loop-video")
        if not video_items:
            return []

        videos: List[Dict[str, str]] = []
        seen = set()

        for item in video_items:
            link_tag = item.find("a")
            if not link_tag:
                continue

            video_url = link_tag.get("href", "")
            title = link_tag.get("title", "") or link_tag.get_text(strip=True)

            if not video_url or not title or video_url in seen or "javs.cc" not in video_url:
                continue

            seen.add(video_url)
            videos.append({"source": "JAVS.CC", "title": title.strip(), "link": video_url})

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
