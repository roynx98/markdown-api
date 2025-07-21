
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse
import httpx
from utils import get_format, get_headers, get_markdown
from datetime import datetime
import hashlib

app = FastAPI()
eTag = {}
lastModified = {}
hashes = {}

class ConvertRequest(BaseModel):
    urls: list[str]
    title: str
    alwaysGenerate: bool = False

@app.post("/convert-to-md", response_class=PlainTextResponse)
async def convert_to_md(
    body: ConvertRequest
):
    urls, title, alwaysGenerate = body.urls, body.title, body.alwaysGenerate
    final_markdown = ""
    was_modified = True 

    for url in urls:
        if not was_modified:
            break

        format = get_format(url)
        headers = get_headers(url)

        if url in eTag:
            headers["If-None-Match"] = eTag[url]
        elif url in lastModified:
            headers["If-Modified-Since"] = lastModified[url]

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 304:
                    was_modified = False
                else:
                    markdown = get_markdown(response, format)
                    hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
                    if hashes.get(url, '') == hash:
                        was_modified = False
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download file: {e}")
        
    if not was_modified and not alwaysGenerate:
        raise HTTPException(status_code=304, detail="No content modified")

    for url in urls:
        format = get_format(url)
        headers = get_headers(url)

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                if 'etag' in response.headers:
                    eTag[url] = response.headers['etag']
                if 'last-modified' in response.headers:
                    lastModified[url] = response.headers['last-modified']
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download file: {e}")

        markdown = get_markdown(response, format)

        hashes[url] = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        final_markdown += markdown + "\n"

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
