"""Original anonymous onlyfy.jobs native inventory and full job-frame reader.

Uses observed public career-page pagination and complete native ad HTML,
separate from the authenticated account API and application endpoints.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

from lxml import etree, html

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from public_http import MAX_BYTES, SourceError, load_json, request, robot_policy  # noqa: E402

PAGE_SIZE = 10
LOCALES = {"en", "de"}
HANDLE = r"[a-z0-9]{8,128}"
LIMITS = [
    "An independently identified employer's *.onlyfy.jobs board is not an employer or country census.",
    "Current native pages and a stable advertised count do not establish historical weekly coverage or a first-publication/reopening instant.",
    "Supported native English/German UI routes do not establish job language or qualification; native handles remain distinct from schema identifiers and human reference codes.",
    "The shell's JobPosting description may be only a200-character summary. Full body comes from the independently observed native job/show full HTML route, not the schema summary or print PDF.",
    "Primary main content and additional published export variants remain separate. Extra template/export text is not automatically a visible ad requirement.",
    "Schema datePosted, TELECOMMUTE and applicant-location values are preserved but do not override physical worksites/meetings or prove Germany-based remote eligibility.",
    "No account API, key, cookie, script/CDN fetch, application, print/PDF, contact or subscription request is supported.",
    "Legacy onlyfy.io published-handle feeds are a distinct contract; this reader does not guess a feed handle or claim their live coverage.",
]


def board(value):
    if not isinstance(value, str) or len(value) > 2048 or value != value.strip() or any(ord(c) < 32 for c in value):
        raise SourceError("invalid_verified_onlyfy_board")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise SourceError("invalid_verified_onlyfy_board") from None
    tenant = re.fullmatch(r"([a-z0-9]+(?:-[a-z0-9]+)*)\.onlyfy\.jobs", parsed.netloc)
    if (parsed.scheme != "https" or not tenant or tenant[1] in {"www", "api", "admin", "static", "support"}
            or parsed.path not in {"/en", "/de"} or parsed.query or parsed.fragment):
        raise SourceError("unverified_onlyfy_board")
    return value, "https://" + parsed.netloc, parsed.path[1:]


def native_job_url(value, base):
    if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 32 for c in value):
        raise SourceError("invalid_native_onlyfy_job_url")
    parsed = urlsplit(value)
    expected, origin, locale = board(base)
    match = re.fullmatch(r"/" + locale + "/job/(" + HANDLE + ")", parsed.path)
    query = parse_qs(parsed.query, keep_blank_values=True)
    if (parsed.scheme + "://" + parsed.netloc != origin or not match or parsed.fragment
            or query and (set(query) != {"career_page_search"} or len(query["career_page_search"]) != 1
                          or not re.fullmatch(r"page=[1-9][0-9]*", query["career_page_search"][0]))):
        raise SourceError("invalid_native_onlyfy_job_url")
    return value, origin, locale, match[1]


def document(raw):
    if not isinstance(raw, bytes) or raw.startswith(b"%PDF"):
        raise SourceError("expected_native_html_not_pdf")
    try:
        return html.fromstring(raw.decode("utf-8-sig"))
    except (etree.ParserError, ValueError, TypeError, UnicodeDecodeError):
        raise SourceError("invalid_native_onlyfy_html") from None


def text(node):
    copy = html.fromstring(html.tostring(node, encoding="unicode", with_tail=False))
    for child in copy.xpath(".//script|.//style|.//iframe|.//object|.//embed"):
        child.drop_tree()
    for child in copy.iter():
        if child.tag in {"p", "li", "div", "br", "h1", "h2", "h3", "h4", "main"}:
            child.tail = " " + (child.tail or "")
    return " ".join(copy.text_content().split())


def markup(node):
    return html.tostring(node, encoding="unicode", method="html")


def parse_inventory(raw, board_url, *, page=1, first_page_total=None):
    base, origin, locale = board(board_url)
    doc = document(raw)
    visible = " ".join(" ".join(doc.xpath('//body//text()[not(ancestor::script) and not(ancestor::style)]')).split())
    ranges = re.findall(r"\b([0-9]+)-([0-9]+)\s+(?:out of|von)\s+([0-9]+)\s+[Jj]obs\b", visible)
    cards = doc.xpath('//a[contains(@href,"/' + locale + '/job/")]')
    if not ranges:
        if (page == 1 and not cards and re.search(r"\b0\s+(?:jobs found|Jobs gefunden)\b", visible)
                and not doc.xpath('//button[@aria-label="Go to next page" and not(@disabled)]')):
            start, end, total = 0, 0, 0
        else:
            raise SourceError("missing_unambiguous_native_page_range")
    elif len(set(ranges)) == 1:
        start, end, total = map(int, ranges[0])
    else:
        raise SourceError("conflicting_native_page_ranges")
    if (first_page_total is not None and first_page_total != total
            or total and (start != (page - 1) * PAGE_SIZE + 1 or end != min(page * PAGE_SIZE, total))
            or total and end < start):
        raise SourceError("native_pagination_total_or_range_changed")
    rows, identities = [], set()
    for card in cards:
        url = urljoin(origin, card.get("href"))
        _, _, _, handle = native_job_url(url, base)
        title = card.get("aria-label")
        headings = card.xpath('.//h3')
        if not title or len(headings) != 1 or text(headings[0]) != " ".join(title.split()):
            raise SourceError("missing_or_conflicting_native_card_title")
        identity = origin + "::" + handle
        if identity in identities:
            raise SourceError("duplicate_native_onlyfy_handle_on_page")
        identities.add(identity)
        rows.append({"id": identity, "native_handle": handle, "url": url, "title": title,
                     "native_card_text": text(card), "native_card_html": markup(card),
                     "original_published_at": None, "full_posting_reviewed": False})
    if (total and len(rows) != end - start + 1) or (not total and rows):
        raise SourceError("native_page_range_and_card_count_differ")
    next_buttons = doc.xpath('//nav[@aria-label="pagination"]//button[@aria-label="Go to next page"]')
    current = doc.xpath('//nav[@aria-label="pagination"]//button[@aria-current="page"]')
    has_more = bool(total and end < total)
    if total and (len(next_buttons) != 1 or len(current) != 1 or text(current[0]) != str(page)
                  or (next_buttons[0].get("disabled") is None) != has_more):
        raise SourceError("native_next_button_or_current_page_does_not_reconcile")
    return {"status": "ok", "source": "onlyfy", "kind": "onlyfy_native_inventory",
            "board_url": base, "requested_url": base + ("?page=" + str(page) if page > 1 else ""),
            "returned_count": len(rows), "source_result_count": total, "listings": rows,
            "native_range": {"start": start, "end": end, "total": total},
            "pagination": {"page": page, "page_size": PAGE_SIZE, "first_page_total": total,
                           "next_page": page + 1 if has_more else None,
                           "next_url": base + "?page=" + str(page + 1) if has_more else None,
                           "native_next_button_enabled": has_more},
            "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS}


def parse_shell(shell_raw, job_url):
    parsed = urlsplit(job_url)
    base = "https://" + parsed.netloc + "/" + parsed.path.split("/")[1]
    _, origin, locale, handle = native_job_url(job_url, base)
    shell = document(shell_raw)
    schemas = shell.xpath('//script[@type="application/ld+json" and @data-testid="job-posting-json-ld"]/text()')
    if len(schemas) != 1:
        raise SourceError("missing_unambiguous_native_job_schema")
    schema = load_json(schemas[0])
    if not isinstance(schema, dict) or schema.get("@type") != "JobPosting" or not isinstance(schema.get("title"), str):
        raise SourceError("invalid_native_job_schema")
    print_links = shell.xpath('//a[@data-testid="print"]/@href')
    if len(print_links) != 1:
        raise SourceError("native_legacy_full_frame_contract_not_advertised")
    printing = urlsplit(urljoin(origin, print_links[0]))
    if (printing.scheme + "://" + printing.netloc != origin
            or printing.path != "/candidate/job/print/" + handle or printing.fragment
            or parse_qs(printing.query) != {"mode": ["print"], "lang": [locale]}):
        raise SourceError("native_print_identity_or_locale_does_not_match")
    return base, origin, locale, handle, schema


def parse_detail(shell_raw, full_raw, job_url):
    base, origin, locale, handle, schema = parse_shell(shell_raw, job_url)
    full = document(full_raw)
    components = full.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," job-ad-component ")]')
    if len(components) != 1:
        raise SourceError("missing_complete_native_job_component")
    component = components[0]
    primary = component.xpath('./main[contains(concat(" ",normalize-space(@class)," ")," main-element ")]')
    if len(primary) != 1:
        raise SourceError("missing_unambiguous_primary_native_ad")
    titles = primary[0].xpath('.//h1')
    if len(titles) != 1 or text(titles[0]) != " ".join(schema["title"].split()):
        raise SourceError("native_shell_and_full_body_title_mismatch")
    apply_links = primary[0].xpath('.//a[contains(@href,"/application/apply/")]/@href')
    for value in apply_links:
        apply = urlsplit(urljoin(origin, value))
        if apply.scheme + "://" + apply.netloc != origin or apply.path != "/application/apply/" + handle:
            raise SourceError("native_full_body_posting_identity_mismatch")
    body = text(primary[0])
    if not body or body == text(titles[0]):
        raise SourceError("missing_complete_native_ad_body")
    variants = [{"source_class": node.get("class"), "html": markup(node), "text": text(node),
                 "visible_or_requirement_verified": False}
                for node in component.xpath('./div[contains(concat(" ",normalize-space(@class)," ")," step-stone-job-ad ")]')]
    return {"status": "ok", "source": "onlyfy", "kind": "onlyfy_native_detail", "board_url": base,
            "id": origin + "::" + handle, "native_handle": handle, "url": job_url, "title": schema["title"],
            "description": body, "description_html": markup(primary[0]),
            "body_representation": "native_onlyfy_primary_full_html", "source_body_untruncated": True,
            "visible_description": None, "native_job_posting": schema,
            "native_schema_description_length": len(schema.get("description", "")),
            "schema_description_used_as_full_body": False, "source_schema_date_posted": schema.get("datePosted"),
            "native_schema_identifier": schema.get("identifier"), "original_published_at": None,
            "native_body_variants": variants, "native_full_component_html": markup(component),
            "body_variants_require_reconciliation": True, "application_links_data_only": apply_links,
            "print_pdf_requested": False, "full_posting_reviewed": False,
            "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS}


def read(*, board_url=None, page=1, first_page_total=None, job_url=None, transport=request):
    if type(page) is not int or page < 1 or page > 1000000:
        raise SourceError("invalid_native_page_number")
    if first_page_total is not None and (type(first_page_total) is not int or not 0 <= first_page_total <= 10000000):
        raise SourceError("invalid_first_page_total")
    if job_url is not None:
        if board_url is not None or page != 1 or first_page_total is not None:
            raise SourceError("invalid_detail_read_arguments")
        parsed = urlsplit(job_url)
        if len(parsed.path.split("/")) < 3:
            raise SourceError("invalid_native_onlyfy_job_url")
        base, origin, locale = board("https://" + parsed.netloc + "/" + parsed.path.split("/")[1])
        _, _, _, handle = native_job_url(job_url, base)
    else:
        base, origin, locale = board(board_url)
        if page > 1 and first_page_total is None:
            raise SourceError("continuation_requires_observed_first_page_total")
        if first_page_total is not None and page > max(1, (first_page_total + PAGE_SIZE - 1) // PAGE_SIZE):
            raise SourceError("page_outside_observed_initial_total")
    rules, policy = robot_policy(origin, transport=transport)
    provenance = []
    def get(url):
        if rules is not None and not rules.can_fetch("job-market-mcp", url):
            raise SourceError("robots_denied")
        response = transport(url, accept="text/html")
        if "text/html" not in (response.get("content_type") or "").lower():
            raise SourceError("unexpected_native_html_content_type")
        provenance.append({"url": url, "method": "GET", "bytes": len(response["body"]),
                           "sha256": hashlib.sha256(response["body"]).hexdigest(),
                           "requested_at": response.get("requested_at"), "observed_at": response.get("observed_at")})
        return response["body"]
    if job_url is None:
        result = parse_inventory(get(base + ("?page=" + str(page) if page > 1 else "")), base,
                                 page=page, first_page_total=first_page_total)
    else:
        shell = get(job_url)
        parse_shell(shell, job_url)
        # This public frame route was observed in the ordinary native job UI;
        # omission of its transient cache-buster was verified byte-for-byte.
        frame_url = origin + "/job/show/" + handle + "/full?lang=" + locale + "&mode=candidate"
        result = parse_detail(shell, get(frame_url), job_url)
    return {**result, "policy": policy, "provenance": provenance}


def capabilities():
    return {"status": "ok", "source": "onlyfy", "operations": ["inventory", "detail"], "seed_required": True,
            "board_contract": "Exact independently identified HTTPS <tenant>.onlyfy.jobs/en or /de, no query/account/application path.",
            "native_page_size": PAGE_SIZE, "continuation": "Observed ?page=N, native range/current-page/next-button and initial total must reconcile.",
            "body_contract": "Native shell JobPosting summary remains separate; primary full job/show HTML plus additional export variants, no scripts/PDF/applications.",
            "max_complete_response_bytes": MAX_BYTES, "acquisition_filters": [], "coverage_complete": False, "limits": LIMITS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--board-url")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--first-page-total", type=int)
    parser.add_argument("--job-url")
    args = parser.parse_args()
    try:
        result = capabilities() if args.capabilities else read(board_url=args.board_url, page=args.page,
                    first_page_total=args.first_page_total, job_url=args.job_url)
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        result = {"status": "source_limited", "source": "onlyfy", "returned_count": None,
                  "source_result_count": None, "error": error.code if isinstance(error, SourceError) else "invalid_native_source_response",
                  "http_status": getattr(error, "http_status", None), "retry_after": getattr(error, "retry_after", None),
                  "coverage_complete": False, "reviewed_by_model": False}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
