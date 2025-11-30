import asyncio
import os
import random
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Query, Security, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select, desc
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# --- 1. CẤU HÌNH DATABASE ---
class VideoCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    search_query: str = Field(index=True)
    source: str
    title: str
    link: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

sqlite_file_name = "videos_cache.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# --- 2. CẤU HÌNH GEMINI ---
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_KEY: genai.configure(api_key=GOOGLE_KEY)

def gemini_normalize_name(user_query: str) -> str:
    """Dùng Gemini 1.5 Flash để chuẩn hóa tên diễn viên."""
    if not GOOGLE_KEY: return user_query.lower()
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""The user query is "{user_query}". Your ONLY task is to return the correctly spelled name for that JAV/Adult actress. 
    - If the query is a typo, fix it.
    - If correct, return as is.
    - If unsure, return the original query.
    Output ONLY the name in lowercase. Do not explain."""
    
    try:
        response = model.generate_content(prompt)
        result = response.text.strip().lower()
        if len(result) < 2 or "sorry" in result: return user_query.lower()
        return result
    except: return user_query.lower()

# --- 3. IMPORT CRAWLERS ---
crawlers = []
try:
    from vlxx import search_videos_by_actor as s_vlxx; crawlers.append(s_vlxx)
    from heovl import search_videos_by_actor as s_heovl; crawlers.append(s_heovl)
    from vailonxx import search_videos_by_actor as s_vailonxx; crawlers.append(s_vailonxx)
    from javx import search_videos_by_actor as s_javx; crawlers.append(s_javx)
    from xvideo import search_videos_by_actor as s_xvideo; crawlers.append(s_xvideo)
    from pornhub import search_videos_by_actor as s_pornhub; crawlers.append(s_pornhub)
    from thumbzilla import search_videos_by_actor as s_thumbzilla; crawlers.append(s_thumbzilla)
    from javtiful import search_videos_by_actor as s_javtiful; crawlers.append(s_javtiful)
    from xhamster import search_videos_by_actor as s_xhamster; crawlers.append(s_xhamster)
    from sextop1 import search_videos_by_actor as s_sextop1; crawlers.append(s_sextop1)
    from mupvl import search_videos_by_actress as s_mupvl; crawlers.append(s_mupvl)
except: pass

# --- 4. APP & MIDDLEWARE ---
app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

API_KEY = os.getenv("MY_SECRET_KEY")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY: return api_key
    return "public_access"

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# --- API 1: TÌM KIẾM & CRAWL ---
@app.get("/search")
async def search_aggregate(q: str = Query(..., min_length=1)):
    clean_query = q.lower().strip()
    
    # 1. Chuẩn hóa Khóa tìm kiếm (Target Key)
    target_query = gemini_normalize_name(clean_query)
    final_name = target_query.title()
    
    # 2. Tìm trong Cache với KHÓA CHUẨN
    with Session(engine) as session:
        results_db = session.exec(select(VideoCache).where(VideoCache.search_query == target_query)).all()
        
        if results_db:
            print(f"DEBUG: CACHE HIT! Khóa: {target_query}")
            return {"source": "CACHE", "actor_name": final_name, "count": len(results_db), "results": results_db}

    # 3. Crawl mới
    tasks = [func(target_query) for func in crawlers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_data = []
    for res in results:
        if isinstance(res, list): final_data.extend(res)
    
    # 4. Lưu vào kho với KHÓA CHUẨN
    if final_data:
        with Session(engine) as session:
            for item in final_data:
                session.add(VideoCache(
                    search_query=target_query, # LƯU VỚI TÊN ĐÃ CHUẨN HÓA
                    source=item.get('source', 'Unknown'),
                    title=item.get('title', 'No Title'),
                    link=item.get('link', '#')
                ))
            session.commit()
            
    return {"source": "LIVE", "actor_name": final_name, "count": len(final_data), "results": final_data}

# --- API 2: LẤY DANH SÁCH MỚI NHẤT ---
@app.get("/latest")
async def get_latest(limit: int = 9, offset: int = 0):
    with Session(engine) as session:
        statement = select(VideoCache).order_by(desc(VideoCache.created_at)).offset(offset).limit(limit)
        results = session.exec(statement).all()
        return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3636)