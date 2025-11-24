#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler Pornhub: tim video theo ten dien vien qua trang search, tra ve list dict.
Phien ban nay su dung cloudscraper de bypass Cloudflare protection.

NOTE: Do website co bot detection manh, co the can su dung:
1. VPN/Proxy neu IP bi chan
2. Selenium voi undetected-chromedriver (xem porn_hub_selenium.py)
3. API pornhub (neu co)
"""

import unicodedata
from typing import List, Dict
from urllib.parse import quote
import time

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    import requests

from bs4 import BeautifulSoup


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


def crawl_videos(url: str, actor_name: str, debug: bool = False) -> List[Dict]:
    """Crawl trang search va loc video theo ten dien vien."""

    # Tao scraper hoac session
    if CLOUDSCRAPER_AVAILABLE:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            },
            delay=10  # Delay de tranh bi phat hien
        )
    else:
        import requests
        scraper = requests.Session()

    # Headers gia lap browser that
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

    try:
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if debug:
                    print(f"Attempt {attempt + 1}/{max_retries} - Fetching: {url}")

                response = scraper.get(url, headers=headers, timeout=30, allow_redirects=True)

                if response.status_code == 403:
                    if debug:
                        print(f"Got 403, waiting {2 ** attempt} seconds before retry...")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue

                response.raise_for_status()
                break

            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                if debug:
                    print(f"Error on attempt {attempt + 1}: {e}")
                time.sleep(2 ** attempt)

    except Exception as e:
        print(f"Error fetching URL after {max_retries} attempts: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    if debug:
        print(f"Page title: {soup.title.string if soup.title else 'No title'}")
        print(f"Page length: {len(response.text)} characters")

    # Tim video blocks voi nhieu selector
    video_blocks = []
    selectors = [
        {"name": "li", "class": "pcVideoListItem"},
        {"name": "div", "class": "videoBox"},
        {"name": "div", "class": "phimage"},
        {"name": "li", "class": "videoblock"},
    ]

    for selector in selectors:
        video_blocks = soup.find_all(selector["name"], class_=selector["class"])
        if video_blocks:
            if debug:
                print(f"Found {len(video_blocks)} blocks using selector: {selector}")
            break

    # Neu khong tim thay, thu tim tat ca link video
    if not video_blocks:
        video_links = soup.find_all(
            "a", href=lambda x: x and ("/view_video" in x or "/video/" in x or "/viewkey" in x)
        )
        video_blocks = [link.parent for link in video_links if link.parent]
        if debug:
            print(f"Found {len(video_blocks)} blocks using href search")

    videos: List[Dict[str, str]] = []

    for block in video_blocks:
        try:
            # Tim the a chua link
            link_tag = (
                block.find("a", class_=lambda x: x and any(cls in str(x).lower() for cls in ["title", "thumb", "video"]))
                or block.find("a", href=lambda x: x and ("/view_video" in x or "/video/" in x or "/viewkey" in x))
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

            # Tim title
            video_title = ""

            # Thu title attribute
            video_title = link_tag.get("title", "").strip()

            # Thu data-title
            if not video_title:
                video_title = link_tag.get("data-title", "").strip()

            # Thu tim element co class title
            if not video_title:
                title_elem = block.find(
                    ["span", "div", "h2", "h3", "a", "p"],
                    class_=lambda x: x and any(cls in str(x).lower() for cls in ["title", "video-title"])
                )
                if title_elem:
                    video_title = title_elem.get_text().strip()

            # Thu text trong link
            if not video_title:
                video_title = link_tag.get_text().strip()

            # Thu alt/title cua anh
            if not video_title:
                img_tag = link_tag.find("img")
                if img_tag:
                    video_title = img_tag.get("alt", "").strip() or img_tag.get("title", "").strip()

            # Neu van khong co title thi bo qua
            if not video_title or len(video_title) < 3:
                continue

            # Lam sach title
            video_title = ' '.join(video_title.split())

            # Kiem tra ten dien vien co trong title khong
            if not check_actor_in_content(video_title, actor_name):
                continue

            videos.append(
                {
                    "source": "Pornhub",
                    "title": video_title[:200],
                    "link": video_link,
                }
            )
        except Exception as e:
            if debug:
                print(f"Error parsing block: {e}")
            continue

    return videos


def search_videos_by_actor(actor_name: str, debug: bool = False) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.

    Args:
        actor_name: Ten dien vien can tim
        debug: Bat debug mode de xem chi tiet

    Output: [{'source': 'Pornhub', 'title': str, 'link': str}, ...]
    """
    try:
        search_url = f"https://www.pornhub.com/video/search?search={quote(actor_name)}"
        return crawl_videos(search_url, actor_name, debug=debug)
    except Exception as e:
        print(f"Error in search_videos_by_actor: {e}")
        return []


def _print_results(results: List[Dict[str, str]]) -> None:
    """In ket qua ra console."""
    if not results:
        print("Khong tim thay video.")
        return
    for idx, item in enumerate(results, 1):
        print(f"{idx}. [{item.get('source', '')}] {item.get('title', '')} - {item.get('link', '')}")


def _main() -> None:
    actor = input("Nhap ten dien vien: ").strip()
    if not actor:
        print("Ten dien vien khong duoc de trong.")
        return
    print("Dang tim kiem, vui long doi...")
    results = search_videos_by_actor(actor)
    _print_results(results)


if __name__ == "__main__":
    _main()
