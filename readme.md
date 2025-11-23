# Video crawler modules (FastAPI-ready)

All crawler modules now expose a single async entry point:

```python
videos = await search_videos_by_actor(actor_name: str)
```

Return shape (uniform across every file):

```python
[{"source": "SiteName", "title": "Video title", "link": "https://..."}, ...]
```

Errors or empty results return `[]` (never raise).

## Files and sources

- `porn_hub.py` -> Pornhub  
- `xhamster.py` -> XHamster  
- `javx.py` -> JAVS.CC  
- `heovl.py` -> HeoVL  
- `thumbzilla.py` -> Thumbzilla  
- `sextop1.py` -> Sextop1  
- `vlxx.py` -> VLXX  
- `vailonxx.py` -> Vailonxx  
- `mupvl.py` -> Mupvl  
- `xvideo.py` -> XVideos

## Quick local test (no FastAPI)

```python
import asyncio
from porn_hub import search_videos_by_actor

async def demo():
    videos = await search_videos_by_actor("Eimi Fukada")
    print(videos[:3])

asyncio.run(demo())
```

## Using inside FastAPI

```python
from fastapi import APIRouter
from porn_hub import search_videos_by_actor

router = APIRouter()

@router.get("/videos/pornhub")
async def videos(actor: str):
    return await search_videos_by_actor(actor)
```

Each crawler runs its own `AsyncWebCrawler`; no global state required.
