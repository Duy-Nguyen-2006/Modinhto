#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler Thumbzilla: tim video theo ten dien vien, tra ve list dict.
"""

import re
import unicodedata
from typing import List, Dict
from urllib.parse import quote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_name_to_url(name: str) -> str:
    """Chuyen ten dien vien thanh slug cho URL Thumbzilla."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "-")
    name = "".join(char for char in name if char.isalnum() or char == "-")
    return name


async def crawl_thumbzilla_actor(crawler: AsyncWebCrawler, actor_url: str) -> List[Dict[str, str]]:
    """Crawl trang pornstar cua Thumbzilla va tra ve video list."""
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=actor_url, config=run_config)
    if not result.success:
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


async def search_videos_by_actor(actor_name: str) -> List[Dict[str, str]]:
    """Tim kiem video cua dien vien tren Thumbzilla."""
    try:
        actor_url_name = normalize_name_to_url(actor_name)
        actor_url = f"https://www.thumbzilla.com/pornstars/{actor_url_name}"
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            return await crawl_thumbzilla_actor(crawler, actor_url)
    except Exception:
        return []
