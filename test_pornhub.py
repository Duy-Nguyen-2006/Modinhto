#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for porn_hub.py
"""
from porn_hub import search_videos_by_actor

def test_actors():
    test_names = ["melody mark", "eva elfie", "eimi fukada"]

    for actor in test_names:
        print(f"\n{'='*80}")
        print(f"Testing with: {actor}")
        print(f"{'='*80}")

        results = search_videos_by_actor(actor)

        if not results:
            print(f"❌ No results found for '{actor}'")
        else:
            print(f"✓ Found {len(results)} videos for '{actor}':")
            for idx, item in enumerate(results[:10], 1):  # Show first 10
                print(f"\n{idx}. Title: {item.get('title', 'N/A')}")
                print(f"   Link: {item.get('link', 'N/A')}")
                print(f"   Source: {item.get('source', 'N/A')}")

        print(f"\nTotal results for {actor}: {len(results)}")

if __name__ == "__main__":
    test_actors()
