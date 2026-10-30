"""Original anonymous SAP SuccessFactors RMK list and complete job reader.

Only independently qualified origins and native geography parameters are
accepted. The separately advertised modern SAP career front is a different
transport and is not silently substituted for the legacy RMK inventory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlsplit

from lxml import etree, html

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from public_http import MAX_BYTES, SourceError, load_json, request, robot_policy  # noqa: E402

ORIGIN = "https://careers.sap.com"
BOARD = ORIGIN + "/search/"
PAGE_SIZE = 25
COUNTRIES = {"DE": "Germany", "EG": "Egypt"}
LIMITS = [
    "This verified legacy SAP RMK origin is not a census of SuccessFactors employers or either national market.",
    "SAP's current jobs.sap.com/en/jobs/ front explicitly advertises this separate legacy board. Neither counts nor identities are combined without reconciliation.",
    "Native whole-board or country partitions preserve all roles; no title, department, career-status, language or candidate filtering is performed.",
    "The qualified origin currently uses 25 rows per page. Native ranges, total, page count, next links and row identities must reconcile on every response.",
    "Primary displayed locations may omit additional locations. A native country partition is not a complete remote-worker eligibility rule.",
    "Source posted dates, career status, employment type and schema clocks are retained raw. None proves original publication, a precise student contract, fit or application readiness.",
    "A complete current inventory is not proof of historical weekly supply. Error, denied, changed or out-of-range reads have null counts.",
    "No application, talent-community, account, alert, script/CDN, key, cookie, contact or subscription request is supported.",
]


def board(value):
    if value != BOARD:
        raise SourceError("unverified_successfactors_board")
    return BOARD


def country_value(value):
    if value is not None and value not in COUNTRIES:
        raise SourceError("unverified_native_country_partition")
    return value


def page_value(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 10000:
        raise SourceError("invalid_native_page")
    return value


def total_value(value):
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000000):
        raise SourceError("invalid_first_page_total")
    return value


def inventory_uri(board_url, *, country=None, page=1):
    board(board_url)
    country_value(country)
    page_value(page)
    values = {"q": "", "sortColumn": "referencedate", "sortDirection": "desc"}
    if country is not None:
        values["optionsFacetsDD_country"] = country
    if page > 1:
        values["startrow"] = str((page - 1) * PAGE_SIZE)
    return BOARD + "?" + urlencode(values)


def job_uri(value):
    if not isinstance(value, str) or len(value) > 4096 or value != value.strip() or any(ord(c) < 32 for c in value):
        raise SourceError("invalid_native_rmk_job_uri")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise SourceError("invalid_native_rmk_job_uri") from None
    match = re.fullmatch(r"/job/([^/]+)/([1-9][0-9]{5,19})/", parsed.path)
    if (parsed.scheme + "://" + parsed.netloc != ORIGIN or not match or parsed.query or parsed.fragment
            or any(part in unquote(parsed.path) for part in ["\\", "/../", "/./"])
            or any(ord(c) < 32 for c in unquote(parsed.path))
            or re.search(r"%2f|%5c|%00", parsed.path, re.I)):
        raise SourceError("unverified_native_rmk_job_uri")
    return value, match[2]


def document(raw):
    if not isinstance(raw, bytes) or raw.startswith(b"%PDF"):
        raise SourceError("expected_native_rmk_html")
    try:
        return html.fromstring(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError, TypeError, etree.ParserError):
        raise SourceError("invalid_native_rmk_html") from None


def clean(node):
    copy = html.fromstring(html.tostring(node, encoding="unicode", with_tail=False))
    for child in copy.xpath(".//script|.//style|.//iframe|.//object|.//embed|.//form|.//input"):
        child.drop_tree()
    for child in copy.iter():
        for name in list(child.attrib):
            if name.lower().startswith("on") or name.lower().startswith("data-"):
                del child.attrib[name]
            elif name.lower() in {"href", "src"} and re.match(r"\s*(?:javascript|vbscript|data):", child.attrib[name], re.I):
                del child.attrib[name]
    return copy


def text(node):
    copy = clean(node)
    for child in copy.iter():
        classes = set((child.get("class") or "").split())
        if (child.tag in {"p", "li", "div", "br", "h1", "h2", "h3", "h4", "section", "table", "tbody", "tr", "td", "ul", "ol"}
                or classes & {"joblayouttoken", "jobdescription"}):
            child.text = " " + (child.text or "")
            child.tail = " " + (child.tail or "")
    return " ".join(copy.text_content().split())


def markup(node):
    return html.tostring(clean(node), encoding="unicode", method="html")


def parse_inventory(raw, board_url, *, country=None, page=1, first_page_total=None):
    board(board_url)
    country_value(country)
    page_value(page)
    total_value(first_page_total)
    if page > 1 and first_page_total is None:
        raise SourceError("continuation_requires_frozen_first_page_total")
    doc = document(raw)
    if doc.xpath('//link[@rel="canonical"]/@href') != [BOARD]:
        raise SourceError("unexpected_native_rmk_inventory_canonical")
    visible = text(doc)
    if country is not None:
        headings = [" ".join(h.text_content().split()) for h in doc.xpath("//h1")]
        if headings != ['Search results for "' + COUNTRIES[country] + '".']:
            raise SourceError("native_country_partition_not_confirmed")
    ranges = re.findall(
        r"\bResults\s+([0-9,]+)\s*[–—-]\s*([0-9,]+)\s+of\s+([0-9,]+)\s+Page\s+([0-9,]+)\s+of\s+([0-9,]+)\b",
        visible,
    )
    if not ranges or len(set(ranges)) != 1:
        raise SourceError("missing_or_conflicting_native_rmk_page_range")
    start, end, total, actual_page, pages = [int(value.replace(",", "")) for value in ranges[0]]
    if (not total or actual_page != page or pages != math.ceil(total / PAGE_SIZE)
            or start != (page - 1) * PAGE_SIZE + 1 or end != min(page * PAGE_SIZE, total) or start > end
            or first_page_total is not None and total != first_page_total):
        raise SourceError("native_rmk_range_or_total_changed")
    tables = doc.xpath('//table[@id="searchresults"]')
    if len(tables) != 1:
        raise SourceError("missing_native_search_result_table")
    rows = tables[0].xpath('.//tr[contains(concat(" ",normalize-space(@class)," ")," data-row ")]')
    listings, seen = [], set()
    for row in rows:
        anchors = row.xpath('.//a[contains(concat(" ",normalize-space(@class)," ")," jobTitle-link ")]')
        if not anchors:
            raise SourceError("missing_native_rmk_title")
        references = {(urljoin(ORIGIN, a.get("href", "")), text(a)) for a in anchors}
        if len(references) != 1:
            raise SourceError("native_mobile_desktop_reference_conflict")
        url, title = references.pop()
        _, native_id = job_uri(url)
        if not title or native_id in seen:
            raise SourceError("empty_or_duplicate_native_rmk_identity")
        seen.add(native_id)
        locations = row.xpath('./td[contains(concat(" ",normalize-space(@class)," ")," colLocation ")]')
        if len(locations) != 1 or not text(locations[0]):
            raise SourceError("missing_unambiguous_native_display_location")
        listings.append({
            "id": ORIGIN + "::" + native_id, "native_url_site_id": native_id,
            "url": url, "title": title, "native_display_location": text(locations[0]),
            "native_row_text": text(row), "native_row_html": markup(row),
            "native_country_partition": country, "original_published_at": None,
            "full_posting_reviewed": False,
        })
    if len(listings) != end - start + 1:
        raise SourceError("native_rmk_range_and_row_count_differ")
    # Published links are checked rather than synthesising permission for an
    # unadvertised continuation or accepting a silently ignored startrow.
    starts = {}
    for anchor in doc.xpath('//ul[contains(concat(" ",normalize-space(@class)," ")," pagination ")]//a[@href]'):
        parsed = urlsplit(urljoin(BOARD, anchor.get("href")))
        if parsed.scheme + "://" + parsed.netloc != ORIGIN or parsed.path != "/search/":
            raise SourceError("unverified_native_rmk_pagination_origin")
        values = parse_qs(parsed.query, keep_blank_values=True)
        if values.get("q") != [""] or values.get("optionsFacetsDD_country") != ([country] if country else None):
            raise SourceError("native_pagination_partition_changed")
        if set(values) - {"q", "optionsFacetsDD_country", "sortColumn", "sortDirection", "startrow"}:
            raise SourceError("unverified_native_pagination_parameter")
        if values.get("sortColumn") != ["referencedate"] or values.get("sortDirection") != ["desc"]:
            raise SourceError("native_pagination_sort_changed")
        offsets = values.get("startrow", ["0"])
        if len(offsets) != 1 or not re.fullmatch(r"[0-9]+", offsets[0]):
            raise SourceError("invalid_native_pagination_offset")
        starts.setdefault(int(offsets[0]), set()).add(urljoin(BOARD, anchor.get("href")))
    has_more = end < total
    if has_more and page * PAGE_SIZE not in starts:
        raise SourceError("native_next_page_not_advertised")
    if has_more and len(starts[page * PAGE_SIZE]) != 1:
        raise SourceError("conflicting_native_next_page_uris")
    return {
        "status": "ok", "source": "successfactors", "kind": "successfactors_rmk_native_inventory",
        "board_url": BOARD, "requested_url": inventory_uri(BOARD, country=country, page=page),
        "native_country_partition": country, "source_result_count": total, "returned_count": len(listings),
        "native_range": {"start": start, "end": end, "total": total, "page": page, "pages": pages},
        "listings": listings,
        "pagination": {"page": page, "page_size": PAGE_SIZE, "first_page_total": total,
                       "next_page": page + 1 if has_more else None,
                       "next_url": next(iter(starts[page * PAGE_SIZE])) if has_more else None,
                       "native_next_advertised": has_more},
        "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS,
    }


def parse_detail(raw, job_url):
    _, native_id = job_uri(job_url)
    doc = document(raw)
    canonical = doc.xpath('//link[@rel="canonical"]/@href')
    headings = doc.xpath("//h1")
    displays = doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," jobDisplay ")]')
    bodies = doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," jobdescription ")]')
    if canonical != [job_url] or len(headings) != 1 or len(displays) != 1 or len(bodies) != 1:
        raise SourceError("missing_or_conflicting_native_rmk_job_structure")
    if displays[0] not in bodies[0].iterancestors() or not text(headings[0]) or len(text(bodies[0])) < 100:
        raise SourceError("missing_complete_native_rmk_body")
    whole, body_text = text(displays[0]), text(bodies[0])
    ids = set(re.findall(r"\bRequisition ID:\s*([0-9]+)\b", whole))
    if len(ids) != 1:
        raise SourceError("missing_or_conflicting_native_requisition_id")
    # These fields are intentionally raw labels. Student status and an
    # employment-type string can describe different dimensions of one job.
    fields = {}
    labels = ["Requisition ID", "Posted Date", "Work Area", "Career Status", "Employment Type", "Expected Travel", "Location"]
    for node in displays[0].xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," joblayouttoken ")]'):
        value = text(node)
        if len(value) > 500:
            continue
        for label in labels:
            match = re.fullmatch(re.escape(label) + r":\s*(.+)", value)
            if match:
                if label in fields and fields[label] != match[1]:
                    raise SourceError("conflicting_native_rmk_display_field")
                fields[label] = match[1]
    postings = []
    allowed = {"@context", "@type", "title", "description", "identifier", "datePosted", "validThrough",
               "jobLocation", "jobLocationType", "applicantLocationRequirements", "employmentType", "hiringOrganization"}
    for script in doc.xpath('//script[@type="application/ld+json"]'):
        value = load_json((script.text or "").encode())
        nodes = value if isinstance(value, list) else [value]
        for item in nodes:
            if not isinstance(item, dict):
                continue
            for candidate in [item, *item.get("@graph", [])]:
                if isinstance(candidate, dict) and candidate.get("@type") == "JobPosting":
                    postings.append({k: v for k, v in candidate.items() if k in allowed})
    return {
        "status": "ok", "source": "successfactors", "kind": "successfactors_rmk_native_detail",
        "id": ORIGIN + "::" + native_id, "native_url_site_id": native_id,
        "native_requisition_id": ids.pop(), "url": job_url, "native_canonical_url": canonical[0],
        "title": text(headings[0]), "description": body_text, "description_html": markup(bodies[0]),
        "native_full_job_display_text": whole, "native_full_job_display_html": markup(displays[0]),
        "native_display_fields": fields, "native_jobposting_schemas": postings,
        "native_description_characters": len(body_text), "source_body_untruncated": True,
        "original_published_at": None, "full_posting_reviewed": False,
        "credentials_exported_or_used": False, "coverage_complete": False, "limits": LIMITS,
    }


def read(*, board_url=None, job_url=None, country=None, page=1, first_page_total=None, transport=request):
    if (board_url is None) == (job_url is None):
        raise SourceError("require_exactly_one_native_rmk_read")
    if board_url is not None:
        url = inventory_uri(board_url, country=country, page=page)
        total_value(first_page_total)
        if page > 1 and first_page_total is None:
            raise SourceError("continuation_requires_frozen_first_page_total")
        if page > 1 and (page - 1) * PAGE_SIZE >= first_page_total:
            raise SourceError("native_page_outside_frozen_inventory")
    else:
        job_uri(job_url)
        if country is not None or page != 1 or first_page_total is not None:
            raise SourceError("inventory_arguments_not_valid_for_detail")
        url = job_url
    rules, policy = robot_policy(ORIGIN, transport=transport)
    if rules is not None and not rules.can_fetch("job-market-mcp", url):
        raise SourceError("robots_denied")
    response = transport(url, accept="text/html", timeout=15)
    if response.get("http_status", 200) != 200 or "text/html" not in (response.get("content_type") or "").lower():
        raise SourceError("unexpected_native_rmk_response")
    result = (parse_inventory(response["body"], board_url, country=country, page=page, first_page_total=first_page_total)
              if board_url is not None else parse_detail(response["body"], job_url))
    return {**result, "policy": policy, "provenance": {
        "requested_url": url, "method": "GET", "http_status": 200,
        "bytes": len(response["body"]), "sha256": hashlib.sha256(response["body"]).hexdigest(),
        "requested_at": response.get("requested_at"), "observed_at": response.get("observed_at"),
    }}


def capabilities():
    return {
        "status": "ok", "source": "successfactors", "operations": ["inventory", "detail"],
        "independently_verified_boards": [BOARD], "native_country_partitions": COUNTRIES,
        "separate_discovered_current_front": "https://jobs.sap.com/en/jobs/",
        "separate_current_front_implemented": False, "native_page_size": PAGE_SIZE,
        "max_complete_response_bytes": MAX_BYTES, "acquisition_role_filters": [],
        "coverage_complete": False, "limits": LIMITS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--board-url")
    parser.add_argument("--job-url")
    parser.add_argument("--country", choices=sorted(COUNTRIES))
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--first-page-total", type=int)
    args = parser.parse_args()
    try:
        result = capabilities() if args.capabilities else read(
            board_url=args.board_url, job_url=args.job_url, country=args.country,
            page=args.page, first_page_total=args.first_page_total)
        print(json.dumps(result, ensure_ascii=False))
    except (SourceError, ValueError, TypeError) as error:
        print(json.dumps({
            "status": "source_limited", "source": "successfactors",
            "error": getattr(error, "code", "invalid_native_successfactors_data"),
            "http_status": getattr(error, "http_status", None), "retry_after": getattr(error, "retry_after", None),
            "returned_count": None, "source_result_count": None, "coverage_complete": False, "limits": LIMITS,
        }))


if __name__ == "__main__":
    main()
