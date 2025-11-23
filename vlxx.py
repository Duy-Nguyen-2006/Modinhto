#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler vlxx.bz: tim video theo ten dien vien, tra ve list dict cho backend.
"""

import re
import unicodedata
from typing import List, Dict
from urllib.parse import quote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_name(name: str) -> str:
    """Chuan hoa ten (bo dau, lower)."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    return name.lower().strip()


def check_actor_in_content(content: str, actor_name: str) -> bool:
    """Kiem tra tat ca tu trong ten dien vien co trong noi dung."""
    content_normalized = normalize_name(content)
    actor_words = normalize_name(actor_name).split()
    return all(word in content_normalized for word in actor_words)


async def find_actor_tag_page(crawler: AsyncWebCrawler, actor_name: str) -> str | None:
    """Thu tim cac trang tag/actor."""
    slug = quote(actor_name.lower().replace(" ", "-"))
    possible_urls = [
        f"https://vlxx.bz/tag/{slug}/",
        f"https://vlxx.bz/dien-vien/{slug}/",
        f"https://vlxx.bz/actor/{slug}/",
        f"https://vlxx.bz/model/{slug}/",
    ]
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    for url in possible_urls:
        try:
            result = await crawler.arun(url=url, config=run_config)
            if result.success and "404" not in result.html.lower() and "not found" not in result.html.lower():
                return url
        except Exception:
            continue
    return None


async def search_videos_by_actor(actor_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.

    Output: [{'source': 'VLXX', 'title': str, 'link': str}, ...]
    """
    try:
        videos: List[Dict[str, str]] = []
        browser_config = BrowserConfig(headless=True, verbose=False)
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            actor_page = await find_actor_tag_page(crawler, actor_name)
            search_url = actor_page or f"https://vlxx.bz/?s={quote(actor_name)}"

            result = await crawler.arun(url=search_url, config=run_config)
            if not result.success:
                return []

            soup = BeautifulSoup(result.html, "html.parser")
            video_blocks = soup.find_all("article", class_=lambda x: x and "post" in x)
            if not video_blocks:
                video_blocks = soup.find_all("div", class_=lambda x: x and "item" in x)
            if not video_blocks:
                video_blocks = soup.find_all("a", href=lambda x: x and "/video/" in x)

            filter_by_content = not actor_page
            seen_links = set()

            for block in video_blocks:
                link_tag = block.find("a", href=True) if hasattr(block, "find") else block
                if not link_tag:
                    continue

                video_link = link_tag.get("href", "")
                if not video_link:
                    continue

                if video_link.startswith("/"):
                    video_link = f"https://vlxx.bz{video_link}"
                elif not video_link.startswith("http"):
                    video_link = f"https://vlxx.bz/{video_link}"

                if "/video/" not in video_link or video_link in seen_links:
                    continue

                title = link_tag.get("title", "").strip()
                if not title and hasattr(block, "find"):
                    title_tag = block.find(["h2", "h3", "h1"])
                    if title_tag:
                        title = title_tag.get_text().strip()
                if not title and hasattr(link_tag, "get_text"):
                    title = link_tag.get_text().strip()

                if not title or len(title) < 3:
                    continue

                if filter_by_content and not check_actor_in_content(title, actor_name):
                    continue

                seen_links.add(video_link)
                videos.append({"source": "VLXX", "title": title, "link": video_link})

        return videos
    except Exception:
        return []
