import asyncio
import os
import random
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Query, Security, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlmodel import Field, Session, SQLModel, create_engine, select
from groq import Groq
from dotenv import load_dotenv

# Load biến môi trường
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

# --- 2. CẤU HÌNH GROQ (XOAY VÒNG KEY) ---
groq_keys_str = os.getenv("GROQ_API_KEYS", "")
GROQ_KEYS = [k.strip() for k in groq_keys_str.split(",") if k.strip()]

def get_random_groq_client():
    if not GROQ_KEYS: return None
    selected_key = random.choice(GROQ_KEYS)
    # print(f"DEBUG: Đang dùng key {selected_key[:10]}...") 
    return Groq(api_key=selected_key)

def groq_fix_typo(user_query: str, candidate_names: list[str]) -> str | None:
    client = get_random_groq_client()
    if not client or not candidate_names: return None

    names_str = "\n".join([f"- {name}" for name in candidate_names[:300]])
    prompt = f"""You are a spell checker for Japanese AV actresses.
Valid names list:
{names_str}
User query: "{user_query}"
Task: Find the exact matching name from the list for the user query, ignoring typos or spacing differences.
Rules:
1. If found, return ONLY the exact name from the list.
2. If NOT found, return ONLY the string "None".
3. Do not explain."""

    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192", 
            messages=[
                {"role": "system", "content": "Output only the name or None."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=50
        )
        result = completion.choices[0].message.content.strip()
        return result if result != "None" and result in candidate_names else None
    except Exception as e:
        print(f"❌ Groq lỗi: {e}")
        return None

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
except ImportError as e:
    print(f"❌ Lỗi import crawler: {e}")

# --- 4. BẢO MẬT API ---
API_KEY = os.getenv("MY_SECRET_KEY")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY: return api_key
    raise HTTPException(status_code=403, detail="Sai Key rồi thằng ngu")

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/search", dependencies=[Security(verify_api_key)])
async def search_aggregate(q: str = Query(..., min_length=1)):
    clean_query = q.lower().strip()
    
    # Check Cache
    with Session(engine) as session:
        existing_queries = session.exec(select(VideoCache.search_query).distinct()).all()
        target_query = clean_query
        
        if existing_queries:
            corrected = groq_fix_typo(clean_query, existing_queries)
            if corrected:
                print(f"🤖 Groq sửa: '{clean_query}' -> '{corrected}'")
                target_query = corrected

        results_db = session.exec(select(VideoCache).where(VideoCache.search_query == target_query)).all()
        if results_db:
            return {"source": f"DATABASE (Query: {target_query})", "count": len(results_db), "results": results_db}

    # Crawl mới
    print(f"🐢 Crawling: {target_query}...")
    tasks = [func(target_query) for func in crawlers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_data = []
    for res in results:
        if isinstance(res, list): final_data.extend(res)
    
    # Lưu Cache
    if final_data:
        with Session(engine) as session:
            for item in final_data:
                session.add(VideoCache(
                    search_query=target_query,
                    source=item.get('source', 'Unknown'),
                    title=item.get('title', 'No Title'),
                    link=item.get('link', '#')
                ))
            session.commit()
            
    return {"source": "LIVE CRAWL", "count": len(final_data), "results": final_data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3636)