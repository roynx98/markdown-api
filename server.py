
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
    hashes = {}

class ConvertRequest(BaseModel):
    urls: list[str]
    title: str
    alwaysGenerate: bool = False
    format: str | None = None
    cssSelector: str | None = None

@app.post("/convert-to-md", response_class=PlainTextResponse)
async def convert_to_md(
    body: ConvertRequest
):
    urls, title, alwaysGenerate, req_format, css_selector = body.urls, body.title, body.alwaysGenerate, body.format, body.cssSelector
    final_markdown = ""
    unmodified_count = 0
   
    for url in urls:
        format = req_format if req_format else get_format(url)
        headers = get_headers(url)

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download file: {e}")

        if not format:
            format = get_format_from_content_type(response.headers.get('Content-Type', ''))

        markdown = get_markdown(response, format, css_selector)

        hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        if hashes.get(url, '') == hash and not alwaysGenerate:
            unmodified_count += 1

        hashes[url] = hash
        with open(HASHES_PATH, "wb") as f:
            pickle.dump(hashes, f)

        final_markdown += markdown + "\n"

    if unmodified_count == len(urls):
        raise HTTPException(status_code=304, detail="No content modified for all URLs")

    date_downloaded = datetime.now().strftime("%Y-%m-%d")
    meta = f"""
<!--
title: {title}
source_url: {url}
date_downloaded: {date_downloaded}
original_format: {format}
-->
"""

    final_markdown = meta + final_markdown

    return final_markdown
