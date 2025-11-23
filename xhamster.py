#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler xhamster: tim video theo ten dien vien, tra ve list dict cho backend.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig


def normalize_slug(text: str) -> str:
    """Convert text to slug-ish form for matching."""
    text = unicodedata.normalize("NFD", text or "")
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    text = re.sub(r"-+", "-", text)
    return text


def create_actress_url(actress_name: str) -> str:
    """Build pornstar page URL from actor name."""
    base_url = "https://vi.xhamster2.com/pornstars"
    return f"{base_url}/{normalize_slug(actress_name)}"


def actor_matches_item(actress_slug: str, title: str, models: list) -> bool:
    """Check if video item belongs to actress via model links or title."""
    if not actress_slug:
        return True
    for m in models:
        href = m.get("href", "")
        if href and actress_slug in normalize_slug(href.split("/")[-1]):
            return True
        model_name = normalize_slug(m.get_text(strip=True))
        if model_name and (
            model_name == actress_slug
            or actress_slug in model_name
            or model_name in actress_slug
        ):
            return True

    title_slug = normalize_slug(title)
    return bool(title_slug and (actress_slug in title_slug or title_slug in actress_slug))


async def search_videos_by_actor(actress_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.

    Output: [{'source': 'XHamster', 'title': str, 'link': str}, ...]
    """
    try:
        url = create_actress_url(actress_name)
        actress_slug = normalize_slug(actress_name)
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, config=run_config)

        if not result.success:
            return []

        soup = BeautifulSoup(result.html, "html.parser")
        video_items = soup.find_all("div", class_="video-thumb")
        if not video_items:
            return []

        videos: List[Dict[str, str]] = []
        seen = set()

        for item in video_items:
            try:
                if "JmEZ-XnZcam-thumb" in item.get("class", []):
                    continue

                link_tag = item.find("a", class_="video-thumb-info__name") or item.find(
                    "a", href=lambda x: x and "/videos/" in x
                )
                if not link_tag:
                    continue

                video_url = link_tag.get("href", "")
                title = link_tag.get("title") or link_tag.get_text(strip=True)
                if not video_url or not title:
                    continue

                video_url = urljoin("https://vi.xhamster2.com", video_url)
                if "xhamster" not in video_url or video_url in seen:
                    continue

                model_links = item.select('a[href*="/pornstar"], a[href*="/pornstars"]')
                matched = actor_matches_item(actress_slug, title, model_links) if model_links else True
                if not matched:
                    continue

                videos.append({"source": "XHamster", "title": title.strip(), "link": video_url})
                seen.add(video_url)
            except Exception:
                continue

        if not videos:
            for item in video_items:
                try:
                    link_tag = item.find("a", class_="video-thumb-info__name") or item.find(
                        "a", href=lambda x: x and "/videos/" in x
                    )
                    if not link_tag:
                        continue
                    video_url = urljoin("https://vi.xhamster2.com", link_tag.get("href", ""))
                    title = (link_tag.get("title") or link_tag.get_text(strip=True)).strip()
                    if "xhamster" not in video_url or not title or video_url in seen:
                        continue
                    videos.append({"source": "XHamster", "title": title, "link": video_url})
                    seen.add(video_url)
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
