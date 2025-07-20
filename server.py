
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse
import httpx
import tempfile
import os
from markitdown import MarkItDown
from utils import get_format
from urllib.parse import urlparse
from datetime import datetime

app = FastAPI()
md = MarkItDown()

class ConvertRequest(BaseModel):
    urls: list[str]
    title: str

@app.post("/convert-to-md", response_class=PlainTextResponse)
async def convert_to_md(
    body: ConvertRequest
):
    urls, title = body.urls, body.title
    final_markdown = ""

    for url in urls:
        format = get_format(url)

        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": referer,
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download file: {e}")

        if format == "md":
            final_markdown += "\n" + response.text
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix="." + format) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            try:
                result = md.convert(tmp_path)
            except Exception as e:
                os.unlink(tmp_path)
                raise HTTPException(status_code=500, detail=f"Conversion failed: {e}")
            os.unlink(tmp_path)
            final_markdown += result.text_content

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
