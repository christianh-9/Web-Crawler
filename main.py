import sys
import requests
from urllib.parse import urlparse
from crawl import normalize_url, extract_page_data, get_urls_from_html
from json_report import write_json_report
import aiohttp
import asyncio
import ssl
import certifi


class AsyncCrawler:
    def __init__(
        self,
        base_url,
        max_concurrency,
        max_pages,
    ):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.page_data = {}
        self.lock = asyncio.Lock()
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        self.session = None
        self.max_pages = max_pages
        self.should_stop = False
        self.all_tasks = set()
        self.visited_urls: set[str] = set()

    async def __aenter__(self):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def add_page_visit(self, normalized_url):
        async with self.lock:
            if self.should_stop:
                return False
            if normalized_url in self.visited_urls:
                return False
            self.visited_urls.add(normalized_url)
            return True

    async def crawl_page(self, current_url=None):
        if self.should_stop:
            return

        base_url_parsed = urlparse(self.base_url)
        if current_url is None:
            current_url = self.base_url
        current_url_parsed = urlparse(current_url)

        if base_url_parsed.netloc != current_url_parsed.netloc:
            return

        normalized = normalize_url(current_url)

        first_visit = await self.add_page_visit(normalized)

        if not first_visit:
            return

        async with self.semaphore:
            try:
                html = await self.get_html(current_url)
                if html is None:
                    return
            except Exception as e:
                print(f"Error: {e}")
                return

            print(f"Crawling {current_url}")
            page_info = extract_page_data(html, current_url)

        async with self.lock:
            self.page_data[normalized] = page_info
            if len(self.page_data) >= self.max_pages:
                self.should_stop = True
                print("Reached maximum number of pages to crawl")
                for task in self.all_tasks:
                    task.cancel()

        urls = get_urls_from_html(html, self.base_url)
        tasks = []

        for url in urls:
            task = asyncio.create_task(self.crawl_page(url))
            tasks.append(task)
            self.all_tasks.add(task)

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            for task in tasks:
                self.all_tasks.discard(task)

    async def get_html(self, url: str) -> str | None:
        try:
            assert self.session is not None
            async with self.session.get(url) as response:
                if response.status > 399:
                    print(f"Error: HTTP {response.status} for {url}")
                    return None

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    print(f"Error: Non-HTML content {content_type} for {url}")
                    return None

                return await response.text()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    async def crawl(self):
        await self.crawl_page(self.base_url)
        return self.page_data


async def crawl_site_async(base_url, max_concurrency, max_pages):
    async with AsyncCrawler(base_url, max_concurrency, max_pages) as crawler:
        return await crawler.crawl()


"""""
def get_html(url: str) -> str:

    try:
        req = requests.get(url, headers={"User-Agent": "BootCrawler/1.0"})
    except Exception as e:
        raise Exception(f"Error fetching url: {e}")

    if req.status_code >= 400:
        raise Exception(f"Status Code: {req.status_code}")
    if "text/html" not in req.headers.get("Content-Type", "").lower():
        raise Exception("Content-Type header not in text/html")

    return req.text


def crawl_page(base_url, current_url=None, page_data: dict = None):
    base_url_parsed = urlparse(base_url)
    if current_url is None:
        current_url = base_url
    current_url_parsed = urlparse(current_url)

    if base_url_parsed.netloc != current_url_parsed.netloc:
        return page_data

    normalized = normalize_url(current_url)

    if page_data is None:
        page_data = {}

    if normalized in page_data:
        return page_data

    try:
        html = get_html(current_url)
    except Exception as e:
        print(f"Error: {e}")
        return page_data
    print(f"Crawling {current_url}")

    page_data[normalized] = extract_page_data(html, current_url)
    urls = get_urls_from_html(html, current_url)

    for url in urls:
        page_data = crawl_page(base_url, url, page_data)
    return page_data
""" ""


def main():

    if len(sys.argv) < 4:
        print("no website provided")
        sys.exit(1)
    elif len(sys.argv) > 4:
        print("too many arguments provided")
        sys.exit(1)
    else:
        base_url = sys.argv[1]
        max_concurrency = int(sys.argv[2])
        max_pages = int(sys.argv[3])
        print(f"starting crawl of : {base_url}")
        page_data = asyncio.run(crawl_site_async(base_url, max_concurrency, max_pages))
        write_json_report(page_data)


if __name__ == "__main__":
    main()
