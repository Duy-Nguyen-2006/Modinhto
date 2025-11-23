#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler vailonxx.co: tim video theo ten dien vien cho backend.
"""

import re
import unicodedata
from typing import List, Dict

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler


def normalize_name(name: str) -> str:
    """Chuan hoa ten thanh slug don gian."""
    name = unicodedata.normalize("NFD", name)
    name = name.encode("ascii", "ignore").decode("utf-8")
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"[\s]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name


def create_actress_url(actress_name: str) -> str:
    """Tao URL trang dien vien."""
    slug = normalize_name(actress_name)
    return f"https://vailonxx.co/{slug}/"


async def search_videos_by_actor(actress_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.

    Output: [{'source': 'Vailonxx', 'title': str, 'link': str}, ...]
    """
    try:
        url = create_actress_url(actress_name)
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)

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
