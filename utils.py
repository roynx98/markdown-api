from fastapi import HTTPException
from urllib.parse import urlparse
import tempfile
from markitdown import MarkItDown
from bs4 import BeautifulSoup
import os

md = MarkItDown()

def get_format_from_content_type(content_type: str) -> str:
    content_type = content_type.lower()
    if 'wordprocessingml' in content_type:
        return 'docx'
    if 'pdf' in content_type:
        return 'pdf'
    if 'msword' in content_type or 'doc' in content_type:
        return 'doc'
    if 'odt' in content_type:
        return 'odt'
    return 'md'

def get_format(url):
    if "docx" in url:
        return 'docx'
    if "pdf" in url:
        return 'pdf'
    if "msword" in url:
        return 'doc'
    if "odt" in url:
        return 'odt'
    if ".md" in url:
        return 'md'
    return ''

def get_headers(url: str) -> dict:
    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Referer": referer,
        "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8a',
        "Accept-Language": 'en',
    }

def get_markdown(response, format, css_selector) -> str:
    mardown = ""
    if format == "md":
        mardown = response.text
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + format) as tmp:
            if format == "html" and css_selector:
                soup = BeautifulSoup(response.content, "html.parser")
                html_content = soup.select(css_selector)[0]
                for img in html_content.select("img"):
                    img.decompose()
                tmp.write(html_content.encode("utf-8"))
                tmp_path = tmp.name
            elif format == "doc" or format == "odt":
                tmp.write(response.content)
                tmp_path = tmp.name
                docx_path = tmp_path.replace('.' + format, '.docx')

                libreoffice_cmd = f'libreoffice --headless --convert-to docx --outdir {os.path.dirname(tmp_path)} {tmp_path}'
                exit_code = os.system(libreoffice_cmd)
                if exit_code != 0 or not os.path.exists(docx_path):
                    os.unlink(tmp_path)
                    raise HTTPException(status_code=500, detail="DOCX conversion failed using LibreOffice.")

                os.unlink(tmp_path)
                tmp_path = docx_path
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
