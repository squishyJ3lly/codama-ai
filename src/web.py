from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

from config import ALLOWED_DOMAINS, REQUEST_TIMEOUT, MAX_HTML_CHARS, MAX_WEB_CHARS
from utils import normalize_url, is_allowed_url, clean_text

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (CODAMA/1.0)"})

def extract_target_url(href: str) -> str:
    href = href.strip()
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    if "uddg" in qs:
        return unquote(qs["uddg"][0])
    return href

def search_web(query: str):
    query = query.strip() + " " + " ".join(f"site:{d}" for d in ALLOWED_DOMAINS)

    resp = SESSION.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text[:MAX_HTML_CHARS], "html.parser")
    results = []

    for a in soup.select("a.result__a"):
        href = a.get("href", "").strip() # type: ignore
        if not href:
            continue

        target = normalize_url(extract_target_url(href))
        if is_allowed_url(target):
            results.append(target)

        if len(results) >= 2:
            break

    return results

def scrape_url(url: str):
    url = normalize_url(url)

    if not is_allowed_url(url):
        raise ValueError(f"Blocked domain: {url}")

    resp = SESSION.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text[:MAX_HTML_CHARS], "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "img", "header", "footer", "aside"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = clean_text(main.get_text(separator="\n"))
    return text[:MAX_WEB_CHARS]

def build_web_context(query: str, direct_url: str = ""):
    if direct_url and is_allowed_url(direct_url):
        urls = [normalize_url(direct_url)]
    else:
        urls = search_web(query)

    if not urls:
        return "No allowed source pages were found."

    parts = []
    for url in urls:
        try:
            text = scrape_url(url)
            parts.append(f"URL: {url}\nCONTENT:\n{text}")
        except Exception as e:
            parts.append(f"URL: {url}\nERROR: {e}")

    return "\n\n---\n\n".join(parts)