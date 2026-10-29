"""Original public Zenjob shift inventory and whole visible details, never signup."""

import json
import re
from urllib.parse import parse_qs, urljoin, urlsplit

from lxml import html

ORIGIN = "https://www.zenjob.com"
LIST_PATH = "/de/jobboerse"
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
DETAIL_PATH = r"/de/jobboerse/jobs/[a-z0-9-]+-(" + UUID + ")"


class ZenjobError(ValueError):
    pass


def clean(value):
    return " ".join(value.split())


def checked_url(url, operation):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "www.zenjob.com" or parts.fragment:
        raise ZenjobError("Exact native public HTTPS origin required")
    query = parse_qs(parts.query, keep_blank_values=True)
    if operation == "detail" and not parts.query and re.fullmatch(DETAIL_PATH, parts.path):
        return url
    if operation == "inventory" and parts.path == LIST_PATH and set(query) <= {"page"}:
        if not query or (
            len(query["page"]) == 1 and re.fullmatch(r"[1-9][0-9]{0,5}", query["page"][0])
        ):
            return url
    raise ZenjobError(
        "Only observed public inventory/page or exact native UUID detail; no account, filter POST or unknown query"
    )


def native_id(url):
    checked_url(url, "detail")
    return re.fullmatch(DETAIL_PATH, urlsplit(url).path)[1]


def inventory(body, url):
    checked_url(url, "inventory")
    tree = html.fromstring(body)
    mains = tree.xpath("//main")
    if len(mains) != 1:
        raise ZenjobError("One complete primary inventory required")
    main = mains[0]
    filters = main.xpath('.//select[@id="city-filter" or @id="category-filter"]')
    if len(filters) != 2 or any(
        node.xpath('.//option[@selected and @value!=""]') for node in filters
    ):
        raise ZenjobError("Whole native city/category scope cannot be verified")
    page = int(parse_qs(urlsplit(url).query).get("page", ["1"])[0])
    active = main.xpath(
        './/a[contains(concat(" ",normalize-space(@class)," ")," bg-surface-quaternary ") and starts-with(@href,"?page=")]'
    )
    if len(active) != 1 or parse_qs(urlsplit(active[0].get("href")).query).get("page") != [
        str(page)
    ]:
        raise ZenjobError("Native active page differs from request")
    cards = main.xpath('.//a[starts-with(@href,"/de/jobboerse/jobs/")]')
    rows = []
    for card in cards:
        target = urljoin(url, card.get("href"))
        headings = card.xpath(".//h2")
        times = card.xpath(".//time/@datetime")
        if len(headings) != 2 or len(times) != 1:
            raise ZenjobError("Native full card title/pay/shift structure changed")
        rows.append(
            {
                "id": native_id(target),
                "url": target,
                "title": clean(headings[1].text_content()),
                "native_card_text": clean(card.text_content()),
                "native_shift_start": times[0],
                "original_source_date": None,
                "source_body_complete": False,
                "applicant_fit_assessed": False,
                "model_reconciliation_required": True,
                "working_student_contract_verified": False,
            }
        )
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise ZenjobError("Unverified empty native inventory or duplicate shift identity")
    links = {}
    for node in main.xpath('.//a[starts-with(@href,"?page=")]'):
        target = urljoin(url, node.get("href"))
        checked_url(target, "inventory")
        number = int(parse_qs(urlsplit(target).query)["page"][0])
        links[number] = target
    later = sorted(number for number in links if number > page)
    if later and later[0] != page + 1:
        raise ZenjobError("Native continuation has a page gap")
    return {
        "listings": rows,
        "returned_count": len(rows),
        "reported_total": None,
        "pagination": {
            "page": page,
            "native_page_links": links,
            "next_url": links[later[0]] if later else None,
            "continuation_basis": "Actual native pagination; >> is a link, not an assumed final page",
            "historical_coverage_verified": False,
        },
    }


def detail(body, url):
    checked_url(url, "detail")
    tree = html.fromstring(body)
    mains = tree.xpath("//main")
    postings = []
    for node in tree.xpath('//script[@type="application/ld+json"]'):
        value = json.loads(node.text or "")
        if isinstance(value, dict) and value.get("@type") == "JobPosting":
            postings.append(value)
    if len(mains) != 1 or len(postings) != 1:
        raise ZenjobError("One native JobPosting and whole visible main required")
    main, posting = mains[0], postings[0]
    if (posting.get("identifier") or {}).get("value") != native_id(url):
        raise ZenjobError("Native UUID differs from requested shift")
    if main.xpath(".//h1/text()") != [posting.get("title")]:
        raise ZenjobError("Native visible title and structured shift disagree")
    headings = {clean(node.text_content()) for node in main.xpath(".//h2")}
    if not {"Beschreibung", "Anforderungen & Hinweise"} <= headings or not posting.get(
        "description"
    ):
        raise ZenjobError("Full visible description AND separate requirements/notes required")
    for node in main.xpath(".//script|.//style|.//noscript"):
        node.drop_tree()
    text = clean(main.text_content())
    return {
        "id": native_id(url),
        "title": posting["title"],
        "native_job_posting": posting,
        "description": text,
        "native_body_fields": {
            "schema_description": posting["description"],
            "whole_visible_detail_including_separate_notes": text,
        },
        "native_shift_starts": list(dict.fromkeys(main.xpath(".//time/@datetime"))),
        "native_schema_url_matches_requested_route": posting.get("url") == url,
        "original_source_date": None,
        "source_schema_date_posted": posting.get("datePosted"),
        "model_reconciliation_required": True,
        "working_student_contract_verified": False,
        "source_body_untruncated": True,
        "full_posting_reviewed": False,
        "requirements_completeness_verified": False,
    }
