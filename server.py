
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse
import httpx
from utils import get_format, get_headers, get_markdown, get_format_from_content_type
from datetime import datetime
import hashlib
import pickle
import os

app = FastAPI()

HASHES_PATH = "hashes.pkl"
if os.path.exists(HASHES_PATH):
    with open(HASHES_PATH, "rb") as f:
        hashes = pickle.load(f)
else:
    hashes = set()

class ConvertRequest(BaseModel):
    scrapeUrl: str
    friendlyUrl: str
    title: str
    alwaysGenerate: bool = False
    format: str | None = None
    cssSelector: str | None = None

@app.post("/convert-to-md", response_class=PlainTextResponse)
async def convert_to_md(
    body: ConvertRequest
):
    scrapeUrl = body.scrapeUrl
    friendlyUrl = body.friendlyUrl
    title = body.title
    alwaysGenerate = body.alwaysGenerate
    req_format = body.format
    css_selector = body.cssSelector
   
    format = req_format if req_format else get_format(scrapeUrl)
    headers = get_headers(scrapeUrl)

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(scrapeUrl, headers=headers)
            response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download file: {e}")

    if not format:
        format = get_format_from_content_type(response.headers.get("Content-Type", ""))

    response_content = response.text if hasattr(response, "text") else str(response.content)
    hash = hashlib.sha256(response_content.encode("utf-8")).hexdigest()

    if hash in hashes and not alwaysGenerate:
        raise HTTPException(status_code=304, detail="No content modified for all URLs")
    markdown = get_markdown(response, format, css_selector)

    hashes.add(hash)
    with open(HASHES_PATH, "wb") as f:
        pickle.dump(hashes, f)

    date_downloaded = datetime.now().strftime("%Y-%m-%d")
    meta = f"""
---
title: {title}
source_url: {friendlyUrl}
date_downloaded: {date_downloaded}
original_format: {format}
---
"""

    return meta + markdown
