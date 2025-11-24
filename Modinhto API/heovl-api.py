#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Expose the HeoVL crawler as an HTTP API.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Ensure we can import heovl.py from the sibling Modinhto folder
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = (BASE_DIR.parent / "Modinhto").resolve()
if WORKSPACE_ROOT.exists() and str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from heovl import search_videos_by_actor  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("heovl_api")

REQUEST_TIMEOUT_SECONDS = 90


class VideoItem(BaseModel):
    source: str
    title: str
    link: str


class SearchRequest(BaseModel):
    actor: str = Field(..., description="Actor/actress name to search", min_length=1)


class SearchResponse(BaseModel):
    count: int
    results: List[VideoItem]


app = FastAPI(title="HeoVL crawler API", version="1.0.0")
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

    logger.info("Searching HeoVL for '%s'", clean_name)
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
    parser = argparse.ArgumentParser(description="HeoVL crawler API server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8001, help="Bind port")
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
