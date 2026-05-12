from logging_system import server_logger
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from ddgs import DDGS

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

def fetch_and_extract_text(url: str, timeout: int = 10, max_chars: int = 4000) -> dict:
    """Fetch a URL once and return {title, url, extracted_text}."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return {"title": "", "url": url, "extracted_text": f"[Skipped — non-HTML content: {content_type}]"}

        soup = BeautifulSoup(resp.text, "lxml")
        page_title = (soup.title.string.strip() if soup.title and soup.title.string else "")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        container = (
            soup.find("article")
            or soup.find("main")
            or soup.body
        )

        if container is None:
            return {"title": page_title, "url": url, "extracted_text": "[No body content found]"}

        text = container.get_text(separator="\n", strip=True)
        lines = [line for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        if len(text) > max_chars:
            text = text[:max_chars] + "\n[... truncated]"

        answer  = {"title": page_title, "url": url, "extracted_text": text}
        server_logger.info(f"Answer: {answer}")
        return answer

    except requests.Timeout:
        return {"title": "", "url": url, "extracted_text": f"[Error: request timed out after {timeout}s]"}
    except requests.HTTPError as e:
        return {"title": "", "url": url, "extracted_text": f"[Error: HTTP {e.response.status_code}]"}
    except requests.ConnectionError:
        return {"title": "", "url": url, "extracted_text": "[Error: connection failed]"}
    except Exception as e:
        return {"title": "", "url": url, "extracted_text": f"[Error: {e}]"}


@tool(description="Search the web using DuckDuckGo and return the results. Use keywords to search ")
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo and return the results."""
    results = []
    seen_urls = set()

    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            url = r["href"]
            if url not in seen_urls:
                seen_urls.add(url)
                results.append(fetch_and_extract_text(url))

    return results


web_search_tools = [search_web]