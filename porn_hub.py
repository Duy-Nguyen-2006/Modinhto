#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler Pornhub: tim video theo ten dien vien qua trang search, tra ve list dict.
"""

import unicodedata
from typing import List, Dict
from urllib.parse import quote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_name(name: str) -> str:
    """Bo dau va chuan hoa ten de so khop."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    return name.lower().strip()


def check_actor_in_content(content: str, actor_name: str) -> bool:
    """Kiem tra ten dien vien co xuat hien trong chuoi khong."""
    normalized_content = normalize_name(content)
    normalized_actor = normalize_name(actor_name)

    if normalized_actor in normalized_content:
        return True

    actor_words = normalized_actor.split()
    if len(actor_words) >= 2:
        matches = sum(1 for word in actor_words if word in normalized_content)
        return matches >= 2

    return False


async def crawl_videos(crawler: AsyncWebCrawler, url: str, actor_name: str) -> List[Dict]:
    """Crawl trang search va loc video theo ten dien vien."""
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=url, config=run_config)
    if not result.success:
        return []

    soup = BeautifulSoup(result.html, "html.parser")

    video_blocks = soup.find_all("li", class_="pcVideoListItem")
    if not video_blocks:
        video_blocks = soup.find_all("div", class_="videoBox")
    if not video_blocks:
        video_blocks = soup.find_all(
            ["li", "div"], class_=lambda x: x and "video" in x.lower()
        )
    if not video_blocks:
        video_links = soup.find_all(
            "a", href=lambda x: x and ("/view_video" in x or "/video/" in x)
        )
        video_blocks = [link.parent for link in video_links]

    videos: List[Dict[str, str]] = []

    for block in video_blocks:
        try:
            link_tag = (
                block.find("a", class_=lambda x: x and "title" in x.lower())
                or block.find("a", href=lambda x: x and ("/view_video" in x or "/video/" in x))
                or block.find("a", href=True)
            )
            if not link_tag:
                continue

            video_link = link_tag.get("href", "")
            if not video_link:
                continue
            if video_link.startswith("/"):
                video_link = f"https://www.pornhub.com{video_link}"
            elif not video_link.startswith("http"):
                continue

            video_title = link_tag.get("title", "").strip()
            if not video_title:
                title_elem = block.find(
                    ["span", "div", "h2", "h3"], class_=lambda x: x and "title" in x.lower()
                )
                if title_elem:
                    video_title = title_elem.get_text().strip()
            if not video_title:
                video_title = link_tag.get_text().strip()
            if not video_title:
                img_tag = link_tag.find("img")
                if img_tag:
                    video_title = img_tag.get("alt", "").strip() or img_tag.get("title", "").strip()
            if not video_title or len(video_title) < 3:
                video_title = "No title"

            if not check_actor_in_content(video_title, actor_name):
                continue

            videos.append(
                {
                    "source": "Pornhub",
                    "title": video_title[:200],
                    "link": video_link,
                }
            )
        except Exception:
            continue

    return videos


async def search_videos_by_actor(actor_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.

    Output: [{'source': 'Pornhub', 'title': str, 'link': str}, ...]
    """
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            search_url = f"https://www.pornhub.com/video/search?search={quote(actor_name)}"
            return await crawl_videos(crawler, search_url, actor_name)
    except Exception:
        return []
