#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed script: crawl một danh sách diễn viên và nạp dữ liệu vào SQLite.
"""

import asyncio
from typing import List

from sqlmodel import Session

from main import engine, fetch_and_cache, init_db


DEFAULT_ACTORS: List[str] = [
    "Eimi Fukada",
    "Yua Mikami",
    "Mia Malkova",
    "Riley Reid",
    "Melody Marks",
]


async def seed(actors: List[str]) -> None:
    init_db()
    with Session(engine) as session:
        for name in actors:
            await fetch_and_cache(name, session)


if __name__ == "__main__":
    asyncio.run(seed(DEFAULT_ACTORS))
