#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler sextop1.movie: tim video theo ten dien vien, tra ve list dict cho backend.
"""

import unicodedata
from typing import List, Dict

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_name(name: str) -> str:
    """Chuan hoa ten (bo dau, lower)."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    return name.lower().strip()


def create_actress_url(actor_name: str) -> str:
    """Tao slug dien vien."""
    slug = normalize_name(actor_name).replace(" ", "-")
    return f"https://sextop1.movie/actresses/{slug}"


async def search_videos_by_actor(actor_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.

    Output: [{'source': 'Sextop1', 'title': str, 'link': str}, ...]
    """
    try:
        actress_url = create_actress_url(actor_name)
        browser_config = BrowserConfig(headless=True, verbose=False)
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=actress_url, config=run_config)

        if not result.success:
            return []

        soup = BeautifulSoup(result.html, "html.parser")
        video_blocks = soup.find_all("div", class_="item")
        if not video_blocks:
            return []

        videos: List[Dict[str, str]] = []
        seen = set()

        for block in video_blocks:
            for link_tag in block.find_all("a", href=True):
                video_link = link_tag.get("href", "")
                if "/phim-sex/" not in video_link:
                    continue

                video_title = link_tag.get("title", "").strip()
                if not video_title:
                    title_h4 = link_tag.find("h4", class_="item__title")
                    if title_h4:
                        video_title = title_h4.get_text().strip()

                if video_link.startswith("/"):
                    video_link = f"https://sextop1.movie{video_link}"
                elif not video_link.startswith("http"):
                    video_link = f"https://sextop1.movie/{video_link}"

                if not video_title or len(video_title) < 3 or video_link in seen:
                    continue

                seen.add(video_link)
                videos.append({"source": "Sextop1", "title": video_title, "link": video_link})

        return videos
    except Exception:
        return []
