#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler vlxx.bz: tim video theo ten dien vien, tra ve list dict.
LAP QUA TAT CA CAC TRANG DE LAY 100% VIDEO.
"""

import asyncio
import re
import unicodedata
import requests
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
    search_query = f"site:vlxx.bz {actor_name} tag"
    ddg_url = "https://html.duckduckgo.com/html/"
    print(f"🔍 Tim URL qua DuckDuckGo: {ddg_url}?q={search_query}")

    def decode_duck_link(raw_href: str) -> Optional[str]:
        if not raw_href:
            return None
        if raw_href.startswith("//duckduckgo.com/l/?"):
            parsed = urlparse("https:" + raw_href)
            target = parse_qs(parsed.query).get("uddg", [None])[0]
            return unquote(target) if target else None
        if raw_href.startswith("http"):
            return raw_href
        return None

    try:
        resp = requests.get(ddg_url, params={"q": search_query}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code != 200:
            print("❌ Khong lay duoc ket qua DuckDuckGo.")
            return None

        soup = BeautifulSoup(resp.content, "html.parser")
        links = soup.find_all("a", class_="result__a")
        if not links:
            print("❌ DuckDuckGo khong tra ve ket qua nao.")
            return None

        pattern = re.compile(r"vlxx\.bz/(tag|dien-vien|actor|model)/([^/?#]+)", re.IGNORECASE)
        for link in links:
            target_url = decode_duck_link(link.get("href", ""))
            if not target_url or "vlxx.bz" not in target_url:
                continue
            m = pattern.search(target_url)
            if m:
                slug = m.group(2)
                if not check_actor_in_content(slug.replace("-", " "), actor_name):
                    continue
                print(f"✅ Tim thay qua DuckDuckGo: {target_url}")
                print(f"✅ Slug: {slug}")
                return target_url

        print("❌ Khong tim thay link vlxx.bz/tag/ trong ket qua.")
        return None
    except Exception as exc:
        print(f"❌ Loi khi search DuckDuckGo: {exc}")
        return None


def search_vlxx_url_via_site(actor_name: str) -> Optional[str]:
    """Fallback: dung search noi bo vlxx.bz/?s=... de tim link tag/dien-vien."""
    try:
        search_url = "https://vlxx.bz/"
        resp = requests.get(search_url, params={"s": actor_name}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.content, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if any(key in href for key in ["/tag/", "/dien-vien/", "/actor/", "/model/"]):
                full = href if href.startswith("http") else f"https://vlxx.bz{href if href.startswith('/') else '/' + href}"
                print(f"✅ Tim thay qua search noi bo: {full}")
                return full
        return None
    except Exception:
        return None

async def find_actor_tag_page(crawler: AsyncWebCrawler, actor_name: str) -> Optional[str]:
    """Thu tim cac trang tag/actor voi nhieu bien the slug."""
    # Tao cac bien the cua slug
    base_slug = normalize_name_to_slug(actor_name)
    slug_variants = [base_slug]  # vd: eimi-fukda

    # Bien the: bo sung 'a' cho tu cuoi (eimi fukda → eimi-fukada)
    words = base_slug.split("-")
    if len(words) >= 2 and not words[-1].endswith("a"):
        words[-1] = words[-1] + "a"
        slug_variants.append("-".join(words))

    # Bien the: bo sung 'y' cho tu dau neu ket thuc bang phu am (melod marks → melody-marks)
    words_y = base_slug.split("-")
    if words_y and words_y[0] and words_y[0][-1] not in "aeiouy":
        words_y[0] = words_y[0] + "y"
        slug_variants.append("-".join(words_y))

    # Bien the: neu tu cuoi ket thuc bang 'd' thi them 'ada' (fukd -> fukada)
    words_d = base_slug.split("-")
    if words_d and words_d[-1].endswith("d"):
        words_d[-1] = words_d[-1][:-1] + "ada"
        slug_variants.append("-".join(words_d))

    # Bien the: neu tu cuoi ket thuc bang 'za' hoac 'aiz' thi bo sung 'wa' (aiza -> aizawa)
    words_wa = base_slug.split("-")
    if words_wa:
        last = words_wa[-1]
        if last.endswith("za") or last.endswith("aiz") or last.endswith("aiza"):
            words_wa[-1] = last + "wa" if not last.endswith("wa") else last
            slug_variants.append("-".join(words_wa))

    # Bien the: neu tu dau ket thuc bang phu am thi bo sung 'i' (minam -> minami)
    words_i = base_slug.split("-")
    if words_i and words_i[0] and words_i[0][-1] not in "aeiouy":
        words_i[0] = words_i[0] + "i"
        slug_variants.append("-".join(words_i))

    # Loai bo trung lap, giu thu tu
    slug_variants = list(dict.fromkeys(slug_variants))

    print(f"🔍 Thu cac bien the slug: {slug_variants}")
    
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=10)
    
    for slug in slug_variants:
        possible_urls = [
            f"https://vlxx.bz/tag/{slug}/",
            f"https://vlxx.bz/dien-vien/{slug}/",
            f"https://vlxx.bz/actor/{slug}/",
            f"https://vlxx.bz/model/{slug}/",
        ]
        
        for url in possible_urls:
            try:
                print(f"  → Thu: {url}")
                result = await crawler.arun(url=url, config=run_config)
                if result.success and "404" not in result.html.lower() and "not found" not in result.html.lower():
                    # Kiem tra xem co video khong
                    soup = BeautifulSoup(result.html, "html.parser")
                    video_links = soup.find_all("a", href=lambda x: x and "/video/" in x)
                    if len(video_links) > 0:
                        print(f"✅ Tim thay trang co video: {url}")
                        return url
            except Exception:
                continue
    
    print(f"⚠️ Khong tim thay trang tag/actor")
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
            if int(num) > max_page and int(num) < 1000:
                max_page = int(num)

    # GIOI HAN TOI DA 10 TRANG
    if max_page > 10:
        print(f"⚠️ Gioi han tim kiem tu {max_page} xuong 10 trang")
        max_page = 10
    
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
                # Xu ly URL pagination
                if "/page/" in base_url:
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

            # Buoc 2: Neu khong tim thay, thu dung search noi bo
            if not base_url:
                base_url = search_vlxx_url_via_site(actor_name)

            # Buoc 3: Neu khong tim thay, thu tim trang tag/actor voi bien the slug
            if not base_url:
                base_url = await find_actor_tag_page(crawler, actor_name)

            # Buoc 4: Neu van khong co, dung search (khong nen dung vi khong chinh xac)
            if not base_url:
                print(f"❌ Khong tim thay trang tag/actor cho '{actor_name}'")
                return []

            # Buoc 5: Crawl tat ca cac trang
            return await crawl_vlxx_all_pages(crawler, base_url, actor_name, filter_by_content=False)
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
