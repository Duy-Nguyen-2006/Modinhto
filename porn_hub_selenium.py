#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler Pornhub: tim video theo ten dien vien qua trang search, tra ve list dict.
Su dung Selenium de bypass bot detection.
"""

import unicodedata
import time
from typing import List, Dict
from urllib.parse import quote
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


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


def get_selenium_driver():
    """Tao Selenium WebDriver voi cau hinh chong phat hien bot."""
    if not SELENIUM_AVAILABLE:
        raise ImportError("Selenium khong duoc cai dat. Chay: pip install selenium")

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def crawl_videos_selenium(url: str, actor_name: str) -> List[Dict]:
    """Crawl trang search va loc video theo ten dien vien su dung Selenium."""
    driver = None
    try:
        driver = get_selenium_driver()
        driver.get(url)

        # Doi trang load xong
        time.sleep(5)

        # Lay page source
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        # Try different selectors to find video blocks
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
            video_blocks = [link.parent for link in video_links if link.parent]

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
                        ["span", "div", "h2", "h3", "a"], class_=lambda x: x and "title" in x.lower()
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
                    continue

                # Check if actor name is in the title
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
                continue

        return videos

    except Exception as e:
        print(f"Error with Selenium: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def search_videos_by_actor(actor_name: str) -> List[Dict[str, str]]:
    """
    Tra ve danh sach video theo ten dien vien.

    Output: [{'source': 'Pornhub', 'title': str, 'link': str}, ...]
    """
    try:
        search_url = f"https://www.pornhub.com/video/search?search={quote(actor_name)}"
        return crawl_videos_selenium(search_url, actor_name)
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
