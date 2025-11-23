#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI aggregation server: chạy song song các crawler, cache kết quả vào SQLite.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import func

from heovl import search_videos_by_actor as search_heovl
from javx import search_videos_by_actor as search_javx
from xhamster import search_videos_by_actor as search_xhamster
from porn_hub import search_videos_by_actor as search_pornhub
from vlxx import search_videos_by_actor as search_vlxx
from sextop1 import search_videos_by_actor as search_sextop1
from thumbzilla import search_videos_by_actor as search_thumbzilla
from vailonxx import search_videos_by_actor as search_vailonxx
from mupvl import search_videos_by_actor as search_mupvl
from xvideo import search_videos_by_actor as search_xvideo


# ---------------------- Database models ---------------------- #
class Actor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    avatar_url: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class Video(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor_id: int = Field(foreign_key="actor.id")
    title: str
    link: str
    source: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


DB_PATH = "sqlite:///./data.db"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


# ---------------------- Crawlers registry ---------------------- #
CRAWLERS: List[Callable[[str], Awaitable[List[Dict[str, str]]]]] = [
    search_heovl,
    search_javx,
    search_xhamster,
    search_pornhub,
    search_vlxx,
    search_sextop1,
    search_thumbzilla,
    search_vailonxx,
    search_mupvl,
    search_xvideo,
]


# ---------------------- FastAPI app ---------------------- #
app = FastAPI(title="Video Crawler Aggregator", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


async def run_with_timeout(coro: Awaitable[List[Dict[str, str]]], timeout: float) -> List[Dict[str, str]]:
    """Chạy một crawler với timeout, trả [] nếu lỗi hoặc hết thời gian."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except Exception:
        return []


async def aggregate_crawlers(actor_name: str, total_timeout: float = 30.0) -> List[Dict[str, str]]:
    """Chạy tất cả crawler song song và hợp nhất kết quả, giới hạn tổng thời gian."""
    async def gather_all():
        tasks = [run_with_timeout(crawler(actor_name), timeout=total_timeout) for crawler in CRAWLERS]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        merged: List[Dict[str, str]] = []
        for items in results:
            if isinstance(items, list):
                merged.extend(items)
        return merged

    try:
        return await asyncio.wait_for(gather_all(), timeout=total_timeout)
    except asyncio.TimeoutError:
        return []


async def fetch_and_cache(actor_name: str, session: Session) -> List[Dict[str, str]]:
    """Kiem tra cache, crawl nếu cần, lưu DB và trả kết quả."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    stmt = select(Actor).where(func.lower(Actor.name) == actor_name.lower())
    actor_obj = session.exec(stmt).first()

    if actor_obj and actor_obj.last_updated >= cutoff:
        videos_db = session.exec(
            select(Video).where(Video.actor_id == actor_obj.id).order_by(Video.created_at.desc())
        ).all()
        return [{"source": v.source, "title": v.title, "link": v.link} for v in videos_db]

    # Crawl mới
    results = await aggregate_crawlers(actor_name)

    if not actor_obj:
        actor_obj = Actor(name=actor_name, last_updated=datetime.utcnow())
        session.add(actor_obj)
        session.commit()
        session.refresh(actor_obj)
    else:
        actor_obj.last_updated = datetime.utcnow()
        # Xóa video cũ
        old_videos = session.exec(select(Video).where(Video.actor_id == actor_obj.id)).all()
        for v in old_videos:
            session.delete(v)

    # Lưu video mới
    for item in results:
        session.add(
            Video(
                actor_id=actor_obj.id,
                title=item.get("title", ""),
                link=item.get("link", ""),
                source=item.get("source", ""),
                created_at=datetime.utcnow(),
            )
        )

    session.commit()
    session.refresh(actor_obj)

    return results


@app.get("/api/search")
async def search(
    actor: str = Query(..., min_length=1, description="Tên diễn viên cần tìm"),
    session: Session = Depends(get_session),
):
    actor_name = actor.strip()
    if not actor_name:
        raise HTTPException(status_code=400, detail="actor is required")

    results = await fetch_and_cache(actor_name, session)
    return {"actor": actor_name, "count": len(results), "results": results}


@app.get("/api/home")
def home(session: Session = Depends(get_session)):
    actors = session.exec(select(Actor)).all()
    payload = []
    for actor in actors:
        videos = session.exec(
            select(Video)
            .where(Video.actor_id == actor.id)
            .order_by(Video.created_at.desc())
            .limit(3)
        ).all()
        payload.append(
            {
                "actor": {
                    "id": actor.id,
                    "name": actor.name,
                    "avatar_url": actor.avatar_url,
                    "last_updated": actor.last_updated,
                },
                "videos": [
                    {"source": v.source, "title": v.title, "link": v.link, "created_at": v.created_at}
                    for v in videos
                ],
            }
        )
    return payload


@app.get("/", include_in_schema=False)
def root():
    return {"message": "Video crawler service is running. Use /api/search?actor=<name>."}
