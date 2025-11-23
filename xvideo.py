#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler xvideos3.com: tim video theo ten dien vien, tra ve list dict cho backend.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler


def normalize_name(name: str) -> str:
    """Chuan hoa ten thanh slug don gian."""
    name_normalized = unicodedata.normalize("NFKD", name or "")
    name_no_accents = "".join([c for c in name_normalized if not unicodedata.combining(c)])
    name_lower = name_no_accents.lower()
    name_clean = re.sub(r"[^a-z0-9\s-]", "", name_lower)
    slug = re.sub(r"\s+", "-", name_clean.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def create_actress_url(actress_name: str, base_url: str = "https://www.xvideos3.com") -> str:
    """Tao URL trang dien vien."""
    slug = normalize_name(actress_name)
    return f"{base_url}/pornstars/{slug}"


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


async def search_videos_by_actor(actress_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.

    Output: [{'source': 'XVideos', 'title': str, 'link': str}, ...]
    """
    try:
        actress_url = create_actress_url(actress_name)
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
                    video_link = f"https://www.xvideos3.com{video_link}"

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
