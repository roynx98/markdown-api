from fastapi import HTTPException
from urllib.parse import urlparse
import tempfile
from markitdown import MarkItDown
import os

md = MarkItDown()

def get_format(url):
    if "docx" in url:
        return 'docx'
    if "pdf" in url:
        return 'pdf'
    if "msword" in url:
        return 'doc'

    return 'md'

def get_headers(url: str) -> dict:
    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    return {
        "User-Agent": "Mozilla/5.0",
        "Referer": referer,
    }

def get_markdown(response, format) -> str:
    mardown = ""
    if format == "md":
        mardown = response.text
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
            
            mardown = result.text_content
    return mardown
