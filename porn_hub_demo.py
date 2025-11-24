#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script cho porn_hub.py voi du lieu mau
Hien thi cach su dung va ket qua mong doi
"""

from typing import List, Dict


def get_sample_data(actor_name: str) -> List[Dict[str, str]]:
    """
    Tra ve du lieu mau cho cac dien vien
    Day la data demo de hien thi cach module hoat dong
    """
    sample_database = {
        "melody mark": [
            {
                "source": "Pornhub",
                "title": "Melody Mark - Beautiful Asian Teen First Time",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f8a3b2c1d9e0"
            },
            {
                "source": "Pornhub",
                "title": "Melody Mark Gets Creampie - Hot Scene",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f8a3b2c1d9e1"
            },
            {
                "source": "Pornhub",
                "title": "Melody Mark POV Blowjob HD",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f8a3b2c1d9e2"
            },
            {
                "source": "Pornhub",
                "title": "Melody Mark Hardcore Compilation",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f8a3b2c1d9e3"
            },
            {
                "source": "Pornhub",
                "title": "Melody Mark Threesome Action",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f8a3b2c1d9e4"
            },
        ],
        "eva elfie": [
            {
                "source": "Pornhub",
                "title": "Eva Elfie - Russian Beauty Solo",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f9b4c3d2e1f0"
            },
            {
                "source": "Pornhub",
                "title": "Eva Elfie Passionate Sex with Boyfriend",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f9b4c3d2e1f1"
            },
            {
                "source": "Pornhub",
                "title": "Eva Elfie Blonde Teen POV",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f9b4c3d2e1f2"
            },
            {
                "source": "Pornhub",
                "title": "Eva Elfie Creampie Compilation 2024",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f9b4c3d2e1f3"
            },
            {
                "source": "Pornhub",
                "title": "Eva Elfie and Friend Lesbian Scene",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f9b4c3d2e1f4"
            },
        ],
        "eimi fukada": [
            {
                "source": "Pornhub",
                "title": "Eimi Fukada - Japanese Pornstar Best Scenes",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f0c5d4e3f2g0"
            },
            {
                "source": "Pornhub",
                "title": "Eimi Fukada Office Lady Fantasy",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f0c5d4e3f2g1"
            },
            {
                "source": "Pornhub",
                "title": "Eimi Fukada Uncensored HD Premium",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f0c5d4e3f2g2"
            },
            {
                "source": "Pornhub",
                "title": "Eimi Fukada Compilation Top 10 Scenes",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f0c5d4e3f2g3"
            },
            {
                "source": "Pornhub",
                "title": "Eimi Fukada Group Sex Wild Party",
                "link": "https://www.pornhub.com/view_video.php?viewkey=ph5f0c5d4e3f2g4"
            },
        ],
    }

    actor_lower = actor_name.lower().strip()
    return sample_database.get(actor_lower, [])


def test_with_sample_data():
    """Test voi du lieu mau"""
    test_names = ["melody mark", "eva elfie", "eimi fukada"]

    print("=" * 80)
    print("PORNHUB VIDEO SCRAPER - DEMO MODE")
    print("=" * 80)
    print("\nNOTE: Day la demo voi du lieu mau.")
    print("Trong thuc te, module se crawl du lieu tu Pornhub.com")
    print("=" * 80)

    for actor in test_names:
        print(f"\n{'='*80}")
        print(f"Tim kiem: {actor}")
        print(f"{'='*80}")

        results = get_sample_data(actor)

        if not results:
            print(f"❌ Khong tim thay video cho '{actor}'")
        else:
            print(f"✓ Tim thay {len(results)} video cho '{actor}':\n")
            for idx, item in enumerate(results, 1):
                print(f"{idx}. Title: {item.get('title', 'N/A')}")
                print(f"   Link: {item.get('link', 'N/A')}")
                print(f"   Source: {item.get('source', 'N/A')}")
                print()

        print(f"Tong ket qua: {len(results)} videos")


def demonstrate_api_usage():
    """Hien thi cach su dung API"""
    print("\n" + "=" * 80)
    print("CACH SU DUNG API")
    print("=" * 80)

    code_example = '''
# Import module
from porn_hub import search_videos_by_actor

# Tim kiem video theo ten dien vien
actor_name = "melody mark"
results = search_videos_by_actor(actor_name)

# Hien thi ket qua
for video in results:
    print(f"Title: {video['title']}")
    print(f"Link: {video['link']}")
    print(f"Source: {video['source']}")
    print()

# Su dung debug mode
results = search_videos_by_actor(actor_name, debug=True)
'''

    print(code_example)

    print("\n" + "=" * 80)
    print("CAC VAN DE THUONG GAP VA GIAI PHAP")
    print("=" * 80)
    print("""
1. Loi 403 Forbidden:
   - Website co bot detection manh
   - Giai phap: Su dung VPN, proxy, hoac selenium

2. Khong tim thay video:
   - Kiem tra ten dien vien co dung khong
   - Thu voi ten khac (vd: stage name)
   - Bat debug mode de xem chi tiet: debug=True

3. Du lieu bi thieu:
   - Website co the thay doi HTML structure
   - Can cap nhat selector trong code
   - Xem porn_hub_selenium.py cho phuong phap thay the

4. Cai dat dependencies:
   pip install beautifulsoup4 lxml cloudscraper requests

5. Su dung Selenium (tot hon cho bypass bot):
   pip install selenium undetected-chromedriver
   Xem file: porn_hub_selenium.py
""")


if __name__ == "__main__":
    test_with_sample_data()
    demonstrate_api_usage()
