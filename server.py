
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
import httpx
import tempfile
import os
from markitdown import MarkItDown

app = FastAPI()
md = MarkItDown()

@app.post("/convert-to-md", response_class=PlainTextResponse)
async def convert_to_md(
    url: str = Query(..., description="URL to a .docx or .doc file"),
    title: str = Query("NVCA Model Term Sheet", description="Title for the document"),
    source_url: str = Query("https://nvca.org/model-legal-documents", description="Source URL for the document"),
    date_downloaded: str = Query("2025-07-15", description="Date the document was downloaded (YYYY-MM-DD)"),
    original_format: str = Query("DOCX", description="Original format of the document")
):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://easylegaldocs.com",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download file: {e}")

    is_doc = 'msword' in url

    with tempfile.NamedTemporaryFile(delete=False, suffix=".doc" if is_doc else ".docx") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        result = md.convert(tmp_path)
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {e}")
    os.unlink(tmp_path)

    lines = result.text_content.splitlines()
    meta = f"""
---
title: {title}
source_url: {source_url}
date_downloaded: {date_downloaded}
original_format: {original_format}
---
    """
    markdown = meta.strip() + "\n" + "\n".join(lines)
    return markdown
