import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class SafeWebScraper:
    def __init__(self, allowed_domains):
        """
        allowed_domains: list like ["example.com", "wikipedia.org"]
        """
        self.allowed_domains = set(allowed_domains)

    def is_allowed(self, url):
        domain = urlparse(url).netloc.replace("www.", "")
        return domain in self.allowed_domains

    def scrape(self, url):
        if not self.is_allowed(url):
            raise ValueError(f"Blocked domain: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (SafeWebScraper/1.0)"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove junk
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n")

        # Clean whitespace
        lines = [line.strip() for line in text.splitlines()]
        cleaned = "\n".join(line for line in lines if line)

        return cleaned