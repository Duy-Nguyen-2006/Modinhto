#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler vlxx.bz: tim video theo ten dien vien, tra ve list dict.
LAP QUA TAT CA CAC TRANG DE LAY 100% VIDEO.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import quote, quote_plus, urlparse, parse_qs, unquote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

def normalize_name(name: str) -> str:
    """Chuan hoa ten (bo dau, lower)."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    return name.lower().strip()

def normalize_name_to_slug(name: str) -> str:
    """Chuyen ten dien vien thanh slug cho URL."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = name.lower().strip().replace(" ", "-")
    name = "".join(char for char in name if char.isalnum() or char == "-")
    return name

def check_actor_in_content(content: str, actor_name: str) -> bool:
    """Kiem tra tat ca tu trong ten dien vien co trong noi dung."""
    content_normalized = normalize_name(content)
    actor_words = normalize_name(actor_name).split()
    return all(word in content_normalized for word in actor_words)

async def search_vlxx_url_via_duckduckgo(actor_name: str) -> Optional[str]:
    """Tim URL vlxx.bz cua dien vien qua DuckDuckGo."""
    search_query = f"vlxx.bz {actor_name}"
    ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}"
    print(f"🔍 Tim URL qua DuckDuckGo: {ddg_url}")

    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=2.0)
            result = await crawler.arun(url=ddg_url, config=run_config)

        if not result.success:
            print("❌ Khong lay duoc ket qua DuckDuckGo.")
            return None

        soup = BeautifulSoup(result.html, "html.parser")
        links = soup.find_all("a", class_="result__a")
        if not links:
            print("❌ DuckDuckGo khong tra ve ket qua nao.")
            return None

        candidates = []
        for link in links:
            href = link.get("href", "")
            text = link.get_text().strip()
            
            # Giai ma URL tu DuckDuckGo
            if "uddg=" in href:
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                real_url = unquote(params.get("uddg", [""])[0]) if params.get("uddg") else href
            else:
                real_url = href
            
            # Kiem tra xem co phai URL vlxx.bz khong
            if "vlxx.bz" not in real_url.lower():
                continue
            
            # Tim slug tu URL
            patterns = [
                r"vlxx\.bz/(tag|dien-vien|actor|model)/([^/?#]+)",
                r"vlxx\.bz/video/([^/?#]+)"
            ]

            for pattern in patterns:
                m = re.search(pattern, real_url, re.IGNORECASE)
                if m:
                    if len(m.groups()) >= 2:
                        slug = m.group(2)
                    else:
                        slug = m.group(1)
                    
                    # Uu tien URL tag/dien-vien/actor
                    if m.group(1) in ['tag', 'dien-vien', 'actor', 'model']:
                        candidates.append({"url": real_url, "text": text, "slug": slug, "priority": 1})
                    else:
                        candidates.append({"url": real_url, "text": text, "slug": slug, "priority": 2})
                    break

        if not candidates:
            print("❌ Khong tim thay link vlxx.bz trong ket qua.")
            return None

        # Sap xep theo priority
        candidates.sort(key=lambda x: x.get("priority", 99))
        first = candidates[0]
        print(f"✅ Tim thay: {first['text']}")
        print(f"✅ URL: {first['url']}")
        print(f"✅ Slug: {first.get('slug', 'N/A')}")
        return first["url"]
    except Exception as exc:
        print(f"❌ Loi khi search DuckDuckGo: {exc}")
        return None

async def find_actor_tag_page(crawler: AsyncWebCrawler, actor_name: str) -> Optional[str]:
    """Thu tim cac trang tag/actor."""
    slug = normalize_name_to_slug(actor_name)
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
                print(f"✅ Tim thay trang: {url}")
                return url
        except Exception:
            continue

    print(f"⚠️ Khong tim thay trang tag/actor, dung search")
    return None

def extract_max_page_number(soup: BeautifulSoup) -> int:
    """Tim so trang toi da tu pagination. GIOI HAN TOI DA 10 TRANG."""
    max_page = 1

    # Tim pagination links
    pagination_links = soup.find_all("a", href=lambda x: x and ("/page/" in x or "paged=" in x))

    for link in pagination_links:
        href = link.get("href", "")

        # Pattern: /page/2/, /page/3/...
        page_match = re.search(r"/page/(\d+)/?", href)
        if page_match:
            page_num = int(page_match.group(1))
            max_page = max(max_page, page_num)

        # Pattern: ?paged=2, &paged=3...
        paged_match = re.search(r"[?&]paged=(\d+)", href)
        if paged_match:
            page_num = int(paged_match.group(1))
            max_page = max(max_page, page_num)

    # Kiem tra trong pagination text
    pagination_divs = soup.find_all(["div", "nav", "ul"], class_=lambda x: x and "pag" in x.lower() if x else False)
    for div in pagination_divs:
        text = div.get_text()
        numbers = re.findall(r'\b(\d+)\b', text)
        for num in numbers:
            if int(num) > max_page and int(num) < 1000:  # Reasonable page limit
                max_page = int(num)

    # GIOI HAN TOI DA 10 TRANG
    if max_page > 10:
        max_page = 10
        print(f"⚠️ Gioi han tim kiem toi da 10 trang")
    
    return max_page

async def crawl_single_page(crawler: AsyncWebCrawler, page_url: str, actor_name: str, filter_by_content: bool) -> List[Dict[str, str]]:
    """Crawl mot trang va tra ve danh sach video."""
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=page_url, config=run_config)

    if not result.success:
        print(f"❌ Khong crawl duoc: {page_url}")
        return []

    soup = BeautifulSoup(result.html, "html.parser")

    # Tim video blocks
    video_blocks = soup.find_all("article", class_=lambda x: x and "post" in x)
    if not video_blocks:
        video_blocks = soup.find_all("div", class_=lambda x: x and ("item" in x or "video" in x) if x else False)
    if not video_blocks:
        video_blocks = soup.find_all("a", href=lambda x: x and "/video/" in x)

    videos: List[Dict[str, str]] = []
    seen_links = set()

    for block in video_blocks:
        try:
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

            # Extract title
            title = link_tag.get("title", "").strip()
            if not title and hasattr(block, "find"):
                title_tag = block.find(["h2", "h3", "h1", "a"])
                if title_tag:
                    title = title_tag.get("title", "").strip()
                    if not title:
                        title = title_tag.get_text().strip()
            if not title and hasattr(link_tag, "get_text"):
                title = link_tag.get_text().strip()

            if not title or len(title) < 3:
                continue

            # Filter by actor name if needed
            if filter_by_content and not check_actor_in_content(title, actor_name):
                continue

            seen_links.add(video_link)
            videos.append({"source": "VLXX", "title": title[:200], "link": video_link})
        except Exception:
            continue

    return videos

async def crawl_vlxx_all_pages(crawler: AsyncWebCrawler, base_url: str, actor_name: str, filter_by_content: bool) -> List[Dict[str, str]]:
    """Crawl TAT CA cac trang va tra ve toan bo video."""
    print(f"\n🚀 Bat dau crawl: {base_url}")

    # Crawl trang dau tien
    print(f"📄 Crawl trang 1...")
    all_videos = await crawl_single_page(crawler, base_url, actor_name, filter_by_content)
    print(f"✅ Trang 1: Tim thay {len(all_videos)} video")

    # NEU TRANG DAU KHONG CO VIDEO → DUNG LUON
    if len(all_videos) == 0:
        print(f"❌ Trang dau tien khong co video. DUNG tim kiem.")
        return []

    # Lay noi dung trang dau de phat hien pagination
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=base_url, config=run_config)

    max_page = 1
    if result.success:
        soup = BeautifulSoup(result.html, "html.parser")
        max_page = extract_max_page_number(soup)
        print(f"📊 Phat hien {max_page} trang")

        # Lap qua cac trang con lai
        if max_page > 1:
            for page_num in range(2, max_page + 1):
                # Xu ly URL pagination - PHAN BIET SEARCH VA TAG/ACTOR PAGE
                if "?s=" in base_url:
                    # URL search: https://vlxx.bz/?s=keyword → /page/2/?s=keyword
                    page_url = f"https://vlxx.bz/page/{page_num}/{base_url.split('vlxx.bz')[-1]}"
                elif "/page/" in base_url:
                    page_url = re.sub(r'/page/\d+/?', f'/page/{page_num}/', base_url)
                elif base_url.endswith('/'):
                    page_url = f"{base_url}page/{page_num}/"
                else:
                    page_url = f"{base_url}/page/{page_num}/"

                print(f"📄 Crawl trang {page_num}/{max_page}...")

                page_videos = await crawl_single_page(crawler, page_url, actor_name, filter_by_content)
                print(f"✅ Trang {page_num}: Tim thay {len(page_videos)} video")

                all_videos.extend(page_videos)

                # Delay nho de tranh bi block
                await asyncio.sleep(1)

    # Loai bo trung lap dua tren link
    unique_videos = []
    seen_links = set()
    for video in all_videos:
        if video["link"] not in seen_links:
            seen_links.add(video["link"])
            unique_videos.append(video)

    print(f"\n✅ TONG KET: {len(unique_videos)} video tu {max_page} trang")
    return unique_videos

async def search_videos_by_actor(actor_name: str) -> List[Dict[str, str]]:
    """
    Tim kiem TAT CA video cua dien vien tren vlxx.bz.

    Output: [{'source': 'VLXX', 'title': str, 'link': str}, ...]
    """
    try:
        browser_config = BrowserConfig(headless=True, verbose=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Buoc 1: Tim URL qua DuckDuckGo
            base_url = await search_vlxx_url_via_duckduckgo(actor_name)

            # Buoc 2: Neu khong tim thay, thu tim trang tag/actor
            if not base_url:
                base_url = await find_actor_tag_page(crawler, actor_name)

            # Buoc 3: Neu van khong co, dung search
            filter_by_content = False
            if not base_url:
                base_url = f"https://vlxx.bz/?s={quote(actor_name)}"
                filter_by_content = True
                print(f"⚠️ Dung search URL: {base_url}")

            # Buoc 4: Crawl tat ca cac trang
            return await crawl_vlxx_all_pages(crawler, base_url, actor_name, filter_by_content)
    except Exception as exc:
        print(f"❌ Loi: {exc}")
        return []

def _print_results(results: List[Dict[str, str]]) -> None:
    """In ket qua ra console."""
    if not results:
        print("\n❌ Khong tim thay video.")
        return

    print(f"\n{'='*80}")
    print(f"DANH SACH {len(results)} VIDEO:")
    print(f"{'='*80}\n")

    for idx, item in enumerate(results, 1):
        print(f"{idx}. [{item.get('source', '')}] {item.get('title', '')}")
        print(f"   Link: {item.get('link', '')}\n")

async def _main() -> None:
    print("="*80)
    print("VLXX.BZ VIDEO CRAWLER - LAY TAT CA VIDEO CUA DIEN VIEN")
    print("="*80)

    actor = input("\nNhap ten dien vien: ").strip()
    if not actor:
        print("❌ Ten dien vien khong duoc de trong.")
        return

    print("\n🔄 Dang tim kiem va crawl tat ca cac trang, vui long doi...\n")
    results = await search_videos_by_actor(actor)
    _print_results(results)

if __name__ == "__main__":
    asyncio.run(_main())
