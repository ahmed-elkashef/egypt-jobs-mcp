"""Original Jobware sitemap and permitted native-advertisement iframe parsing."""

import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

from lxml import html


class JobwareError(ValueError):
    pass


def identity(url):
    parts = urlsplit(url)
    match = re.fullmatch(r"/job/[^/]+-([0-9]{9})", parts.path)
    if (
        parts.scheme != "https"
        or parts.netloc != "www.jobware.de"
        or parts.query
        or parts.fragment
        or not match
    ):
        raise JobwareError("Exact native public advertisement URL is required")
    return match[1]


def inventory(body):
    root = ElementTree.fromstring(body)
    if root.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset":
        raise JobwareError("One complete official advertisements URL set required")
    rows = []
    for element in root:
        fields = {node.tag.rsplit("}", 1)[-1]: node.text for node in element}
        url = fields.get("loc")
        if not url:
            raise JobwareError("Native advertisement URL missing")
        rows.append(
            {
                "id": identity(url),
                "url": url,
                "title": None,
                "original_source_date": None,
                "source_last_modified": fields.get("lastmod"),
                "source_expires": fields.get("expires"),
                "source_body_complete": False,
                "applicant_fit_assessed": False,
                "metadata_basis": "Official whole advertisements sitemap; native advert supplies title/model/geography",
            }
        )
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise JobwareError("Native advertisement inventory missing or source identities duplicated")
    return {
        "listings": rows,
        "returned_count": len(rows),
        "reported_total": None,
        "pagination": {
            "native_whole_sitemap_response": True,
            "next_url": None,
            "historical_coverage_verified": False,
        },
        "clock_basis": "Sitemap lastmod and expires are distinct from original employer publication.",
    }


def embedded_url(wrapper, url):
    identifier = identity(url)
    frames = html.fromstring(wrapper).xpath("//iframe[@src]/@src")
    if len(frames) != 1:
        raise JobwareError("One complete native advertisement iframe required")
    target = urljoin(url, frames[0])
    parts = urlsplit(target)
    if (
        parts.scheme != "https"
        or parts.netloc != "www.jobware.de"
        or parts.query
        or parts.fragment
        or not re.fullmatch(r"/jobsearch/embed/job/(?:[0-9]+/)+index\.html", parts.path)
        or identifier not in parts.path.split("/")
    ):
        raise JobwareError("Native iframe origin/path/advertisement identity differs")
    return target


def _postings(value):
    if isinstance(value, list):
        for item in value:
            yield from _postings(item)
    elif isinstance(value, dict):
        if value.get("@type") == "JobPosting":
            yield value
        if "@graph" in value:
            yield from _postings(value["@graph"])


def detail(wrapper, url, embedded_body, actual_embedded_url):
    if embedded_url(wrapper, url) != actual_embedded_url:
        raise JobwareError("Full body differs from native iframe reference")
    native = []
    for script in html.fromstring(wrapper).xpath('//script[@type="application/ld+json"]'):
        try:
            native.extend(_postings(json.loads(script.text or "")))
        except ValueError:
            continue
    containers = html.fromstring(embedded_body).xpath("//body")
    if len(native) != 1 or len(containers) != 1:
        raise JobwareError("One native structured advert and complete iframe body required")
    container = containers[0]
    for unwanted in container.xpath(".//script|.//style|.//noscript"):
        unwanted.drop_tree()
    text = " ".join(container.text_content().split())
    if not text:
        raise JobwareError("Native body has no readable text; no snippet fallback")
    return {
        "id": identity(url),
        "title": native[0].get("title"),
        "native_job_posting": native[0],
        "native_embedded_body_url": actual_embedded_url,
        "native_embedded_body_sha256": hashlib.sha256(embedded_body).hexdigest(),
        "description": text,
        "description_html": html.tostring(container, encoding="unicode"),
        "source_body_untruncated": True,
        "full_posting_reviewed": False,
        "requirements_completeness_verified": False,
    }
