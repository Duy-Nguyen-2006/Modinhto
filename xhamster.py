#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler XHamster: tim video theo ten dien vien, tra ve list dict.
LAP QUA TAT CA CAC TRANG DE LAY 100% VIDEO.
Co chuan hoa ten qua DuckDuckGo.
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin, urlparse, parse_qs, unquote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


def normalize_slug(text: str) -> str:
    """Convert text to slug-ish form for matching."""
    text = unicodedata.normalize("NFD", text or "")
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    text = re.sub(r"-+", "-", text)
    return text


async def search_xhamster_slug_via_duckduckgo(actor_name: str) -> Optional[str]:
    """Tim slug pornstar XHamster qua DuckDuckGo."""
    search_query = f"xhamster pornstars {actor_name}"
    ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}"
    print(f"🔍 Tim slug qua DuckDuckGo: {ddg_url}")

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
            
            # Giai ma URL tu DuckDuckGo redirect
            if "uddg=" in href:
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                real_url = unquote(params.get("uddg", [""])[0]) if params.get("uddg") else href
            else:
                real_url = href

            # Tim URL xhamster pornstars
            # Pattern: xhamster.com/pornstars/{slug} hoac xhamster2.com/pornstars/{slug}
            m = re.search(r"xhamster\d*\.[a-z]+/pornstars/([^/?#]+)", real_url, re.IGNORECASE)
            if m:
                slug = m.group(1)
                candidates.append({"slug": slug, "url": real_url, "text": text})

        if not candidates:
            print("❌ Khong tim thay link xhamster trong ket qua.")
            return None

        first = candidates[0]
        print(f"✅ Tim thay actress: {first['text']}")
        print(f"✅ Slug: {first['slug']}")
        print(f"✅ URL: {first['url']}")
        return first["slug"]
    except Exception as exc:
        print(f"❌ Loi khi search DuckDuckGo: {exc}")
        return None


def extract_max_page_number(soup: BeautifulSoup) -> int:
    """Tim so trang toi da tu pagination."""
    max_page = 1

    # Tim tat ca cac link co page= trong href
    pagination_links = soup.find_all("a", href=lambda x: x and "page=" in x)
    for link in pagination_links:
        href = link.get("href", "")
        page_match = re.search(r"[?&]page=(\d+)", href)
        if page_match:
            page_num = int(page_match.group(1))
            max_page = max(max_page, page_num)

    # Kiem tra pagination div hoac span (class co chua "pag")
    pagination_divs = soup.find_all(
        ["div", "span", "ul"], 
        class_=lambda x: x and any(term in x.lower() for term in ["pag", "page"]) if x else False
    )
    for div in pagination_divs:
        text = div.get_text()
        numbers = re.findall(r'\b(\d+)\b', text)
        for num in numbers:
            max_page = max(max_page, int(num))

    # Gioi han toi da 10 trang
    return min(max_page, 10)


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


async def crawl_single_page(crawler: AsyncWebCrawler, page_url: str, actress_slug: str) -> List[Dict[str, str]]:
    """Crawl mot trang va tra ve danh sach video."""
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=page_url, config=run_config)
    
    if not result.success:
        print(f"❌ Khong crawl duoc: {page_url}")
        return []

    soup = BeautifulSoup(result.html, "html.parser")
    video_items = soup.find_all("div", class_="video-thumb")
    
    if not video_items:
        return []

    videos: List[Dict[str, str]] = []
    seen = set()

    for item in video_items:
        try:
            # Bo qua cac thumb quang cao
            if "JmEZ-XnZcam-thumb" in item.get("class", []):
                continue

            # Tim link video
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

            # Kiem tra xem video co phai cua actress nay khong
            model_links = item.select('a[href*="/pornstar"], a[href*="/pornstars"]')
            matched = actor_matches_item(actress_slug, title, model_links) if model_links else True
            if not matched:
                continue

            videos.append({
                "source": "XHamster",
                "title": title.strip()[:200],
                "link": video_url
            })
            seen.add(video_url)
        except Exception:
            continue

    # Neu khong co video nao matched, lay tat ca (fallback)
    if not videos:
        for item in video_items:
            try:
                if "JmEZ-XnZcam-thumb" in item.get("class", []):
                    continue
                    
                link_tag = item.find("a", class_="video-thumb-info__name") or item.find(
                    "a", href=lambda x: x and "/videos/" in x
                )
                if not link_tag:
                    continue
                    
                video_url = urljoin("https://vi.xhamster2.com", link_tag.get("href", ""))
                title = (link_tag.get("title") or link_tag.get_text(strip=True)).strip()
                
                if "xhamster" not in video_url or not title or video_url in seen:
                    continue
                    
                videos.append({
                    "source": "XHamster",
                    "title": title[:200],
                    "link": video_url
                })
                seen.add(video_url)
            except Exception:
                continue

    return videos


async def crawl_xhamster_actor_all_pages(crawler: AsyncWebCrawler, actor_url: str, actress_slug: str) -> List[Dict[str, str]]:
    """Crawl TAT CA cac trang cua pornstar va tra ve toan bo video."""
    print(f"\n🚀 Bat dau crawl: {actor_url}")

    # Crawl trang dau tien
    print(f"📄 Crawl trang 1...")
    all_videos = await crawl_single_page(crawler, actor_url, actress_slug)
    print(f"✅ Trang 1: Tim thay {len(all_videos)} video")
    pages_crawled = 1

    # Neu trang dau tien khong co video thi dung lai
    if len(all_videos) == 0:
        print("⚠️ Trang 1 khong co video, dung crawl.")
        return []

    # Lay noi dung trang dau de phat hien pagination
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    result = await crawler.arun(url=actor_url, config=run_config)

    if result.success:
        soup = BeautifulSoup(result.html, "html.parser")
        max_page = extract_max_page_number(soup)
        print(f"📊 Phat hien {max_page} trang")

        # Lap qua cac trang con lai
        if max_page > 1:
            separator = "?" if "?" not in actor_url else "&"

            for page_num in range(2, max_page + 1):
                page_url = f"{actor_url}{separator}page={page_num}"
                print(f"📄 Crawl trang {page_num}/{max_page}...")

                page_videos = await crawl_single_page(crawler, page_url, actress_slug)
                print(f"✅ Trang {page_num}: Tim thay {len(page_videos)} video")

                # Neu trang nay khong co video thi dung lai
                if len(page_videos) == 0:
                    print("⚠️ Trang khong co video, dung crawl cac trang tiep theo.")
                    break

                all_videos.extend(page_videos)
                pages_crawled += 1

                # Delay nho de tranh bi block
                await asyncio.sleep(1)

    # Loai bo trung lap dua tren link
    unique_videos = []
    seen_links = set()
    for video in all_videos:
        if video["link"] not in seen_links:
            seen_links.add(video["link"])
            unique_videos.append(video)

    print(f"\n✅ TONG KET: {len(unique_videos)} video tu {pages_crawled} trang")
    return unique_videos


async def search_videos_by_actor(actress_name: str) -> List[Dict[str, str]]:
    """
    Tim kiem TAT CA video cua dien vien tren XHamster.
    Co chuan hoa ten qua DuckDuckGo.

    Output: [{'source': 'XHamster', 'title': str, 'link': str}, ...]
    """
    try:
        # Buoc 1: Tim slug qua DuckDuckGo
        slug = await search_xhamster_slug_via_duckduckgo(actress_name)
        if not slug:
            slug = normalize_slug(actress_name)
            print(f"⚠️ Dung slug tu normalize: {slug}")

        # Buoc 2: Crawl tat ca cac trang
        actor_url = f"https://vi.xhamster2.com/pornstars/{slug}"
        browser_config = BrowserConfig(headless=True, verbose=False)
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            return await crawl_xhamster_actor_all_pages(crawler, actor_url, slug)
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
    print("XHAMSTER VIDEO CRAWLER - LAY TAT CA VIDEO CUA DIEN VIEN")
    print("="*80)

    actress = input("\nNhap ten dien vien: ").strip()
    if not actress:
        print("❌ Ten dien vien khong duoc de trong.")
        return

    print("\n🔄 Dang tim kiem va crawl tat ca cac trang, vui long doi...\n")
    results = await search_videos_by_actor(actress)
    _print_results(results)


if __name__ == "__main__":
    asyncio.run(_main())
