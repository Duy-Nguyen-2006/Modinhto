#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared helpers to expose the crawler scripts as FastAPI services.
Each API module calls create_api(...) with its crawler module and search function.
"""

import argparse
import asyncio
import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Callable, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
MODULE_ROOT = (BASE_DIR.parent / "Modinhto").resolve()
if MODULE_ROOT.exists() and str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


class VideoItem(BaseModel):
    source: str
    title: str
    link: str


class SearchRequest(BaseModel):
    actor: str = Field(..., min_length=1, description="Actor or actress name to search")


class SearchResponse(BaseModel):
    count: int
    results: List[VideoItem]


def load_search_function(module_name: str, func_name: str) -> Callable[[str], object]:
    """Import the crawler module and grab its search function."""
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError(f"Cannot import module '{module_name}': {exc}") from exc

    func = getattr(module, func_name, None)
    if not func or not callable(func):
        raise RuntimeError(f"Module '{module_name}' missing callable '{func_name}'")
    return func


def create_api(
    module_name: str,
    search_func_name: str,
    title: str,
    *,
    version: str = "1.0.0",
    default_timeout: int = 90,
    default_port: int = 8000,
):
    """Factory that builds a FastAPI app and a CLI runner for a crawler module."""
    search_func = load_search_function(module_name, search_func_name)
    logger = logging.getLogger(f"{module_name}_api")
    timeout_seconds = default_timeout

    app = FastAPI(title=title, version=version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    async def run_search(actor_name: str) -> SearchResponse:
        clean_name = actor_name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Actor name must not be empty")

        logger.info("Searching %s for '%s'", module_name, clean_name)
        try:
            result = search_func(clean_name)
            if inspect.iscoroutine(result):
                videos = await asyncio.wait_for(result, timeout=timeout_seconds)
            else:
                videos = await asyncio.wait_for(
                    asyncio.to_thread(search_func, clean_name),
                    timeout=timeout_seconds,
                )
        except asyncio.TimeoutError:
            logger.warning(
                "Search timeout after %s seconds for '%s'",
                timeout_seconds,
                clean_name,
            )
            raise HTTPException(
                status_code=504,
                detail=f"Search timeout after {timeout_seconds} seconds",
            )
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Search failed for '%s'", clean_name)
            raise HTTPException(
                status_code=500, detail="Internal error during search"
            ) from exc

        return {"count": len(videos), "results": videos}

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/search", response_model=SearchResponse)
    async def search_post(payload: SearchRequest) -> SearchResponse:
        return await run_search(payload.actor)

    @app.get("/search", response_model=SearchResponse)
    async def search_get(
        actor: str = Query(..., description="Actor name to search", min_length=1)
    ) -> SearchResponse:
        return await run_search(actor)

    def main() -> None:
        nonlocal timeout_seconds
        parser = argparse.ArgumentParser(description=f"{title} server")
        parser.add_argument("--host", default="0.0.0.0", help="Bind host")
        parser.add_argument("--port", type=int, default=default_port, help="Bind port")
        parser.add_argument(
            "--timeout",
            type=int,
            default=default_timeout,
            help="Per-request timeout in seconds",
        )
        args = parser.parse_args()
        timeout_seconds = args.timeout
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")

    return app, main
