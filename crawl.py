from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin
from typing import TypedDict


class PageData(TypedDict):
    url: str
    heading: str
    first_p: str
    outgoing_links: list[str]
    image_urls: list[str]


def normalize_url(url: str) -> str:
    parsed = urlparse(url)

    full_path = parsed.path.rstrip(("/"))
    return parsed.netloc.lower() + full_path.lower()


def get_heading_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main_header = soup.find("h1")

    if main_header is not None:
        return main_header.get_text(strip=True)
    elif soup.find("h2") is not None:
        return soup.find("h2").get_text(strip=True)
    else:
        return ""


def get_first_paragraph_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")

    if main is not None:
        if main.find("p") is not None:
            return main.find("p").get_text(strip=True)
        else:
            return ""

    elif soup.find("p"):
        return soup.find("p").get_text(strip=True)
    else:
        return ""


def get_urls_from_html(html, base_url):
    soup = BeautifulSoup(html, "html.parser")

    anchors = soup.find_all("a")
    urls = []

    for tag in anchors:
        url = tag.get("href")
        if url is not None and url != "":
            urls.append(urljoin(base_url, url))

    return urls


def get_images_from_html(html, base_url):
    soup = BeautifulSoup(html, "html.parser")

    imgs = soup.find_all("img")
    images = []

    for tag in imgs:
        image = tag.get("src")
        if image is not None and image != "":
            images.append(urljoin(base_url, image))
    return images


def extract_page_data(html: str, page_url: str):

    heading = get_heading_from_html(html)
    first_p = get_first_paragraph_from_html(html)
    links = get_urls_from_html(html, page_url)
    images = get_images_from_html(html, page_url)

    return {
        "url": page_url,
        "heading": heading,
        "first_paragraph": first_p,
        "outgoing_links": links,
        "image_urls": images,
    }
