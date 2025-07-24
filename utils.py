from fastapi import HTTPException
from urllib.parse import urlparse
import tempfile
from markitdown import MarkItDown
from bs4 import BeautifulSoup
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

def get_markdown(response, format, css_selector) -> str:
    mardown = ""
    if format == "md":
        mardown = response.text
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + format) as tmp:
            if css_selector and format == "html":
                soup = BeautifulSoup(response.content, "html.parser")
                html_content = soup.select(css_selector)[0]
                for img in html_content.select("img"):
                    img.decompose()
                tmp.write(html_content.encode("utf-8"))
            else:
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
