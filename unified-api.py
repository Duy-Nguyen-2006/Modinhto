#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified API Wrapper - Tổng hợp kết quả từ tất cả các scraper.
Khi gọi với tên diễn viên, API sẽ tìm kiếm trên TẤT CẢ các nguồn và trả về kết quả tổng hợp.
"""

import asyncio
from typing import List, Dict
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import tất cả các module scraper
import vlxx
import thumbzilla
import heovl
import javtiful
import javx
import mupvl
import pornhub
import sextop1
import vailonxx
import xhamster
import xvideo

app = FastAPI(
    title="Unified Video Search API",
    description="API tổng hợp tìm kiếm video từ tất cả các nguồn",
    version="1.0.0"
)

# CORS middleware để cho phép request từ mọi nguồn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def safe_search(scraper_name: str, search_func, actress_name: str) -> List[Dict[str, str]]:
    """
    Gọi hàm search của một scraper và xử lý lỗi.
    Trả về kết quả hoặc list rỗng nếu có lỗi.
    """
    try:
        print(f"🔍 [{scraper_name}] Đang tìm kiếm '{actress_name}'...")
        results = await search_func(actress_name)
        print(f"✅ [{scraper_name}] Tìm thấy {len(results)} video")
        return results
    except Exception as e:
        print(f"❌ [{scraper_name}] Lỗi: {e}")
        return []


@app.get("/")
async def root():
    """Endpoint gốc - thông tin API"""
    return {
        "message": "Unified Video Search API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "Tìm kiếm video theo tên diễn viên",
            "/docs": "API Documentation",
        },
        "usage": "/search?q=eimi+fukada"
    }


@app.get("/search")
async def search_all_sources(
    q: str = Query(..., description="Tên diễn viên cần tìm kiếm", min_length=1)
):
    """
    Tìm kiếm video từ TẤT CẢ các nguồn và trả về kết quả tổng hợp.

    Parameters:
        q: Tên diễn viên (ví dụ: "eimi fukada", "yua mikami", ...)

    Returns:
        JSON object chứa:
        - query: Tên diễn viên đã tìm
        - total: Tổng số video tìm thấy
        - sources: Số nguồn đã tìm thành công
        - results: Danh sách tất cả video từ mọi nguồn
        - by_source: Kết quả phân loại theo từng nguồn
    """
    actress_name = q.strip()

    if not actress_name:
        return JSONResponse(
            status_code=400,
            content={"error": "Query không được để trống"}
        )

    print(f"\n{'='*80}")
    print(f"🎬 TÌM KIẾM: '{actress_name}'")
    print(f"{'='*80}\n")

    # Gọi tất cả các scraper ĐỒNG THỜI
    all_tasks = [
        safe_search("VLXX", vlxx.search_videos_by_actor, actress_name),
        safe_search("Thumbzilla", thumbzilla.search_videos_by_actor, actress_name),
        safe_search("HeoVL", heovl.search_videos_by_actor, actress_name),
        safe_search("Javtiful", javtiful.search_videos_by_actor, actress_name),
        safe_search("JavX", javx.search_videos_by_actor, actress_name),
        safe_search("MupVL", mupvl.search_videos_by_actor, actress_name),
        safe_search("Pornhub", pornhub.search_videos_by_actor, actress_name),
        safe_search("SexTop1", sextop1.search_videos_by_actor, actress_name),
        safe_search("VailonXX", vailonxx.search_videos_by_actor, actress_name),
        safe_search("XHamster", xhamster.search_videos_by_actor, actress_name),
        safe_search("XVideo", xvideo.search_videos_by_actor, actress_name),
    ]

    # Chạy tất cả đồng thời
    all_results = await asyncio.gather(*all_tasks)

    # Tổng hợp kết quả
    combined_results = []
    by_source = {}
    sources_found = 0

    source_names = [
        "VLXX", "Thumbzilla", "HeoVL", "Javtiful", "JavX",
        "MupVL", "Pornhub", "SexTop1", "VailonXX", "XHamster", "XVideo"
    ]

    for idx, results in enumerate(all_results):
        source_name = source_names[idx]
        if results:
            sources_found += 1
            combined_results.extend(results)
            by_source[source_name] = {
                "count": len(results),
                "videos": results
            }
        else:
            by_source[source_name] = {
                "count": 0,
                "videos": []
            }

    print(f"\n{'='*80}")
    print(f"✅ HOÀN TẤT: Tìm thấy {len(combined_results)} video từ {sources_found} nguồn")
    print(f"{'='*80}\n")

    return {
        "query": actress_name,
        "total": len(combined_results),
        "sources_found": sources_found,
        "total_sources": len(source_names),
        "results": combined_results,
        "by_source": by_source
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "unified-api"}


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*80)
    print("🚀 UNIFIED VIDEO SEARCH API")
    print("="*80)
    print("📍 API sẽ chạy tại: http://localhost:8000")
    print("📖 Docs tại: http://localhost:8000/docs")
    print("🔍 Ví dụ: http://localhost:8000/search?q=eimi+fukada")
    print("="*80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
