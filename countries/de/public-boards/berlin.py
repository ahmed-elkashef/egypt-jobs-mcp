"""Original whole-category discovery and native BerlinStartupJobs reading."""

import json
import re
from urllib.parse import urljoin, urlsplit

from lxml import html

ORIGIN = "https://berlinstartupjobs.com"
CATEGORIES = {
    "engineering",
    "marketing",
    "design-ux",
    "operations",
    "sales",
    "product-management",
    "hr-recruiting",
    "finance",
    "internships",
    "contracting-positions",
    "seeking-co-founders",
    "other",
}


class BerlinError(ValueError):
    pass


def checked_url(url, operation):
    p = urlsplit(url)
    if p.scheme != "https" or p.netloc != "berlinstartupjobs.com" or p.query or p.fragment:
        raise BerlinError("Exact native anonymous origin and route required")
    parts = p.path.strip("/").split("/")
    if operation == "inventory":
        if p.path == "/":
            return url
        if parts[0] not in CATEGORIES or not p.path.endswith("/"):
            raise BerlinError("Observed native category partition required")
        if len(parts) == 1:
            return url
        if (
            len(parts) == 3
            and parts[1] == "page"
            and re.fullmatch("[1-9][0-9]{0,5}", parts[2])
            and (int(parts[2]) > 1)
        ):
            return url
    if (
        operation == "detail"
        and len(parts) == 2
        and (parts[0] in CATEGORIES)
        and re.fullmatch("[a-z0-9-]+", parts[1])
        and p.path.endswith("/")
    ):
        return url
    raise BerlinError(
        "Unsupported native inventory/detail path; no arbitrary taxonomy or API route"
    )


def catalogue(body):
    t = html.fromstring(body)
    heads = t.xpath('//h4[normalize-space(.)="Jobs by category"]')
    if len(heads) != 1:
        raise BerlinError("Complete native category navigation is not verified")
    result = []
    for a in heads[0].getparent().xpath(".//ul/li/a[@href]"):
        url = urljoin(ORIGIN, a.get("href"))
        p = urlsplit(url)
        label = " ".join(a.text_content().split())
        match = re.search("\\(([0-9]+)\\)\\s*$", label)
        if (
            p.scheme != "https"
            or p.netloc != "berlinstartupjobs.com"
            or p.query
            or p.fragment
            or (not re.fullmatch("/[a-z][a-z0-9-]*/", p.path))
            or (not match)
        ):
            raise BerlinError("Native category identity/count is ambiguous")
        result.append(
            {
                "url": url,
                "native_label": label,
                "native_count": int(match[1]),
                "reader_route_supported": p.path.strip("/") in CATEGORIES,
            }
        )
    if not result or len({row["url"] for row in result}) != len(result):
        raise BerlinError("Category catalogue missing or duplicate")
    return result


def inventory(body, url):
    checked_url(url, "inventory")
    partitions = catalogue(body)
    p = urlsplit(url)
    if p.path == "/":
        return {
            "kind": "german_public_board_partition_catalogue",
            "native_partitions": partitions,
            "featured_homepage_is_complete_inventory": False,
            "coverage_complete": False,
            "operator_requirement": "Enumerate every native category and continuation; never acquire only applicant-interest categories.",
        }
    segments = p.path.strip("/").split("/")
    page = int(segments[2]) if len(segments) == 3 else 1
    base = ORIGIN + "/" + segments[0] + "/"
    own = [row for row in partitions if row["url"] == base]
    if len(own) != 1:
        raise BerlinError("Current category is absent from the complete native taxonomy")
    total = own[0]["native_count"]
    t = html.fromstring(body)
    active = [
        " ".join(e.text_content().split())
        for e in t.xpath(
            '//*[contains(concat(" ",normalize-space(@class)," ")," page-numbers ") and contains(concat(" ",normalize-space(@class)," ")," current ")]'
        )
    ]
    if active != [str(page)] and (active or page > 1 or total > 25):
        raise BerlinError("Native selected page differs or is missing")
    cards = t.xpath(
        '//ul[contains(concat(" ",normalize-space(@class)," ")," jobs-list-items ")]/li[contains(concat(" ",normalize-space(@class)," ")," bjs-jlid ")]'
    )
    rows = []
    for node in cards:
        links = node.xpath(
            './/h4[contains(concat(" ",normalize-space(@class)," ")," bjs-jlid__h ")]/a[@href]'
        )
        if len(links) != 1:
            raise BerlinError("Primary source title/detail identity is ambiguous")
        target = urljoin(url, links[0].get("href"))
        checked_url(target, "detail")
        rows.append(
            {
                "id": target,
                "url": target,
                "title": " ".join(links[0].text_content().split()),
                "native_card_text": " ".join(node.text_content().split()),
                "source_body_complete": False,
                "original_source_date": None,
                "applicant_fit_assessed": False,
            }
        )
    nexts = {
        urljoin(url, a.get("href"))
        for a in t.xpath(
            '//a[contains(concat(" ",normalize-space(@class)," ")," next ") and contains(concat(" ",normalize-space(@class)," ")," page-numbers ") and @href]'
        )
    }
    if len(nexts) > 1:
        raise BerlinError("Conflicting native continuation")
    next_url = next(iter(nexts), None)
    if next_url:
        checked_url(next_url, "inventory")
        if next_url != base + "page/" + str(page + 1) + "/":
            raise BerlinError("Native continuation changes partition or skips a page")
    if (
        len({row["id"] for row in rows}) != len(rows)
        or (not rows and total != 0)
        or (next_url and len(rows) != 25)
        or (not next_url and (page - 1) * 25 + len(rows) != total)
    ):
        raise BerlinError(
            "Native records/count/continuation disagree; no false exhausted partition"
        )
    return {
        "listings": rows,
        "returned_count": len(rows),
        "reported_total": total,
        "native_partitions": partitions,
        "pagination": {"page": page, "next_url": next_url, "historical_coverage_verified": False},
        "scope": "One whole native category partition. Category counts overlap; the homepage and one category are not the whole source.",
    }


def _postings(v):
    if isinstance(v, list):
        for x in v:
            yield from _postings(x)
    elif isinstance(v, dict):
        if v.get("@type") == "JobPosting":
            yield v
        if "@graph" in v:
            yield from _postings(v["@graph"])


def detail(body, url):
    checked_url(url, "detail")
    t = html.fromstring(body)
    posts = []
    for script in t.xpath('//script[@type="application/ld+json"]'):
        try:
            posts.extend(_postings(json.loads(script.text or "")))
        except ValueError:
            continue
    nodes = t.xpath(
        '//div[contains(concat(" ",normalize-space(@class)," ")," bsj-template__content ")]'
    )
    if len(posts) != 1 or len(nodes) != 1:
        raise BerlinError("One structured job and full visible native body required")
    for e in nodes[0].xpath(".//script|.//style|.//noscript"):
        e.drop_tree()
    text = " ".join(nodes[0].text_content().split())
    if not text or not posts[0].get("description"):
        raise BerlinError("Complete native description missing; no snippet fallback")
    return {
        "id": url,
        "title": posts[0].get("title"),
        "native_job_posting": posts[0],
        "description": text,
        "description_html": html.tostring(nodes[0], encoding="unicode"),
        "source_date_posted": posts[0].get("datePosted"),
        "original_source_date": None,
        "source_body_untruncated": True,
        "full_posting_reviewed": False,
        "requirements_completeness_verified": False,
    }
