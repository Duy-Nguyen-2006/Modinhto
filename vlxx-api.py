#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Expose the vlxx crawler as a small HTTP API.
"""

import argparse
import asyncio
import logging
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from vlxx import search_videos_by_actor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("vlxx_api")

REQUEST_TIMEOUT_SECONDS = 90


class VideoItem(BaseModel):
    source: str
    title: str
    link: str


class SearchRequest(BaseModel):
    actor: str = Field(..., description="Actor name to search", min_length=1)


class SearchResponse(BaseModel):
    count: int
    results: List[VideoItem]


app = FastAPI(title="VLXX crawler API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _run_search(actor_name: str) -> SearchResponse:
    """Run the crawler search with input validation and timeout handling."""
    clean_name = actor_name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Actor name must not be empty")

    logger.info("Searching VLXX for actor '%s'", clean_name)
    try:
        videos = await asyncio.wait_for(
            search_videos_by_actor(clean_name), timeout=REQUEST_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Search timeout after %s seconds for '%s'",
            REQUEST_TIMEOUT_SECONDS,
            clean_name,
        )
        raise HTTPException(
            status_code=504,
            detail=f"Search timeout after {REQUEST_TIMEOUT_SECONDS} seconds",
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Search failed for '%s'", clean_name)
        raise HTTPException(status_code=500, detail="Internal error during search") from exc

    return {"count": len(videos), "results": videos}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
async def search_post(payload: SearchRequest) -> SearchResponse:
    return await _run_search(payload.actor)


@app.get("/search", response_model=SearchResponse)
async def search_get(
    actor: str = Query(..., description="Actor name to search", min_length=1)
) -> SearchResponse:
    return await _run_search(actor)


def main() -> None:
    global REQUEST_TIMEOUT_SECONDS
    parser = argparse.ArgumentParser(description="VLXX crawler API server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument(
        "--timeout",
        type=int,
        default=REQUEST_TIMEOUT_SECONDS,
        help="Per-request timeout in seconds",
    )
    args = parser.parse_args()

    REQUEST_TIMEOUT_SECONDS = args.timeout

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
