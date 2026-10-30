"""Original anonymous Berlin state-portal HTML contracts; no source scripts.

The actual numbered links retain native entry filters while 'weiter' can drop
one. A public portal advert can differ from its linked employer original.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlsplit

from lxml import html
from lxml.etree import ParserError

from meinpraktikum import clean, safe_primary
from network import Client, SourceError, base_result

ORIGIN = "https://www.karriereportal-stellen.berlin.de"
SOURCE = "berlin_state_jobs"
ENTRY = "https://www.berlin.de/karriereportal/"
FILTER = "filter[taetigkeit_id][]"
INITIAL_FILTER = "filter[taetigkeit_id][28]"
SCOPES = {"all", "student_entry"}
COLUMNS = ["Stellenbezeichnung", "Behörde/Einrichtung", "Entgeltgruppe/Besoldungsgruppe", "Veröffentlicht", "Bewerbungsfrist"]
LIMITS = [
    "This is the Berlin state portal's native advertised supply, not all Berlin, German state/municipal employers or a country/week census.",
    "Student category28 includes school, university, professional placements and student employment. Preserve ambiguous models and acquire the unfiltered complement; no career/degree/employer keyword.",
    "Numbered next links preserve native scope; weiter can drop the filter. Initial native total and selected scope/current offset must reconcile. Moving supply is not silently complete.",
    "A Berlin portal listing can describe an outside-Berlin workplace or point to a separately numbered employer original. Source dates, deadlines, salary groups and Homeoffice benefits are not original-clock, eligibility, exact pay or Germany-remote verdicts.",
    "Full public portal advert text, header and published JobPosting remain separate. Employer originals, attachments, nontext requirements and actual application materials need independent qualification/review.",
    "No script, cookie/session, login, application, subscription, map, contact or payment request; no source implementation is copied.",
]


def arguments(scope, start=0, first_page_total=None):
    if not isinstance(scope, str) or scope not in SCOPES or type(start) is not int or not 0 <= start <= 1000000:
        raise SourceError("Exact native all/student_entry scope and integer offset required")
    if (start == 0 and first_page_total is not None) or (start > 0 and (
        type(first_page_total) is not int or not start < first_page_total <= 1000000
    )):
        raise SourceError("Continuation requires its original native total; initial scope cannot carry one")


def inventory_uri(scope, start=0):
    if scope not in SCOPES or type(start) is not int or not 0 <= start <= 1000000:
        raise SourceError("Invalid native scope/offset")
    if scope == "all" and start == 0:
        return ORIGIN + "/"
    fields = {"start": str(start)} if start else {}
    if scope == "student_entry":
        fields[FILTER if start else INITIAL_FILTER] = "28"
    return ORIGIN + "/stellenangebote.html?" + urlencode(fields)


def native_query(url):
    p = urlsplit(url)
    if p.path == "/" and not p.query:
        return "all", 0
    if p.path != "/stellenangebote.html":
        raise SourceError("Not a native Berlin inventory route")
    try:
        q = parse_qs(p.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise SourceError("Malformed native query") from None
    if set(q) - {"start", FILTER, INITIAL_FILTER} or any(len(v) != 1 for v in q.values()) or FILTER in q and INITIAL_FILTER in q:
        raise SourceError("Only exact native offset/entry filters; no keyword or duplicate fields")
    selected = q.get(FILTER, q.get(INITIAL_FILTER))
    if selected is not None and selected != ["28"]:
        raise SourceError("Unqualified native entry filter")
    offset = q.get("start", ["0"])[0]
    if not re.fullmatch(r"0|[1-9][0-9]{0,6}", offset) or int(offset) > 1000000:
        raise SourceError("Invalid native offset")
    return ("student_entry" if selected else "all"), int(offset)


def checked_url(url, method="GET"):
    if method != "GET" or not isinstance(url, str) or not 0 < len(url) <= 4096 or any(c.isspace() or ord(c) < 32 for c in url):
        raise SourceError("Bounded exact anonymous Berlin GET routes only")
    p = urlsplit(url)
    path = unquote(p.path)
    if p.scheme + "://" + p.netloc != ORIGIN or p.fragment or "%" in path or "\\" in path or any(c.isspace() for c in path):
        raise SourceError("Unqualified Berlin origin or ambiguous route")
    if p.path == "/robots.txt" and not p.query:
        return url
    if re.fullmatch(r"/[A-Za-z0-9_.()~-]+-de-j[1-9][0-9]{0,19}\.html", path) and not p.query and ".." not in path:
        return url
    native_query(url)
    return url


def identity(url):
    checked_url(url)
    match = re.search(r"-de-j([1-9][0-9]{0,19})\.html$", urlsplit(url).path)
    if not match:
        raise SourceError("Exact acquired native advert URI required")
    return match[1]


def document(raw):
    if not isinstance(raw, bytes) or not re.search(rb"</html\s*>\s*$", raw, re.I):
        raise SourceError("Complete native HTML required; no clipped/login/empty substitute")
    try:
        return html.fromstring(raw)
    except (ValueError, TypeError, ParserError) as error:
        raise SourceError("Malformed native HTML") from error


def base(kind):
    return {**base_result(SOURCE, kind), "source_entry_url": ENTRY, "limits": LIMITS}


def parse_inventory(raw, scope="all", start=0, *, first_page_total=None):
    arguments(scope, start, first_page_total)
    tree = document(raw)
    roots = tree.xpath('//*[@id="jobslisting"]')
    tables = tree.xpath('//table[@id="joboffers"]')
    counts = tree.xpath('//h2[contains(concat(" ",normalize-space(@class)," ")," number_jobs ")]')
    selections = tree.xpath('//select[@name="filter[taetigkeit_id][]"]/option[@selected]/@value')
    if len(roots) != 1 or len(tables) != 1 or len(counts) != 1 or selections != (["28"] if scope == "student_entry" else []):
        raise SourceError("Native list and selected entry scope do not reconcile")
    match = re.fullmatch(r"([0-9][0-9.]*) Stellenangebote? gefunden", clean(counts[0].text_content()))
    if not match:
        raise SourceError("Native exact count is missing")
    total = int(match[1].replace(".", ""))
    if total <= start or total > 1000000 or first_page_total is not None and total != first_page_total:
        raise SourceError("Native total changed/out-of-range or unqualified empty format", observed_total=total)
    table = tables[0]
    if [clean(x.text_content()) for x in table.xpath('.//thead//th')] != COLUMNS:
        raise SourceError("Native five-column inventory contract changed")
    metadata = []
    for row in table.xpath('.//tr[td]'):
        cells = row.xpath('./td')
        if len(cells) != 5:
            raise SourceError("Incomplete native row")
        links = cells[0].xpath('.//a[@href]')
        if len(links) != 1:
            raise SourceError("Native row does not bind one advert")
        uri = urljoin(ORIGIN, links[0].get("href"))
        number = identity(uri)
        fields = [clean(x.text_content()) for x in cells]
        if not all(fields):
            raise SourceError("Native row field is missing")
        metadata.append({"id": SOURCE + "::" + number, "native_id": number, "url": uri,
                         "title": clean(links[0].text_content()), "company": fields[1],
                         "native_table_fields": dict(zip(COLUMNS, fields, strict=True)),
                         "native_published_label": fields[3], "native_deadline_label": fields[4],
                         "description": None, "original_published_at": None,
                         "full_posting_reviewed": False, "reviewed_by_model": False})
    if not metadata or len({r["id"] for r in metadata}) != len(metadata) or start + len(metadata) > total:
        raise SourceError("Native rows are absent, duplicated or outside the source count")
    selected = tree.xpath('//*[@id="joblist_navigator"]//li[contains(concat(" ",normalize-space(@class)," ")," stellen_navi_sel ")]/a[@href]')
    if len(selected) != 1 or native_query(urljoin(ORIGIN, selected[0].get("href"))) != (scope, start):
        raise SourceError("Native selected offset/scope does not match the request")
    numbered, other, numbered_links = [], [], []
    for link in tree.xpath('//*[@id="joblist_navigator"]//a[@href]'):
        label = clean(link.text_content())
        href = link.get("href")
        if href == "javascript:void(0);" and label == "...":
            continue
        if href in {"#", ""} or href.startswith("#"):
            if label.isdigit():
                raise SourceError("Numbered continuation has no native URI")
            continue
        uri = urljoin(ORIGIN, href)
        checked_url(uri)
        pair = native_query(uri)
        if label.isdigit():
            numbered_links.append({"native_page_label": label, "url": uri, "scope": pair[0], "start": pair[1]})
        if pair[0] == scope and pair[1] > start and label.isdigit():
            numbered.append((pair[1], uri))
        elif not label.isdigit():
            other.append({"text": label, "url": uri, "retains_scope": pair[0] == scope})
    next_pair = min(numbered) if numbered else None
    more = start + len(metadata) < total
    if more != bool(next_pair) or next_pair and next_pair[0] != start + len(metadata):
        raise SourceError("Whole native rows and exact next numbered offset do not reconcile")
    initial = total if first_page_total is None else first_page_total
    return {**base("berlin_state_inventory"), "requested_url": inventory_uri(scope, start),
            "native_scope": {"provider": "berlin", "scope": scope, "start": start},
            "metadata": metadata, "returned_count": len(metadata), "source_result_count": total,
            "first_page_total": initial, "native_other_paging_links": other,
            "native_numbered_paging_links": numbered_links,
            "next_url": next_pair[1] if next_pair else None,
            "next_request": {"provider": "berlin", "scope": scope, "start": next_pair[0], "first_page_total": initial} if next_pair else None,
            "has_more": more, "all_source_or_student_models_reviewed": False,
            "raw_html_sha256": hashlib.sha256(raw).hexdigest()}


def inventory(scope="all", start=0, *, first_page_total=None, client=None):
    arguments(scope, start, first_page_total)
    transport = client or Client(url_check=checked_url)
    response = transport.get(inventory_uri(scope, start))
    if response.status != 200:
        raise SourceError("Complete native inventory HTTP200 required", http_status=response.status)
    result = parse_inventory(response.body, scope, start, first_page_total=first_page_total)
    result.update(native_HTTP_status=response.status, native_GET_requests=getattr(transport, "get_count", None),
                  native_read_POST_requests=getattr(transport, "read_post_count", None))
    return result


def parse_detail(raw, url):
    number = identity(url)
    tree = document(raw)
    nodes = tree.xpath('//*[@id="jobTplContainer"]')
    canonical = tree.xpath('//link[@rel="canonical"]/@href')
    graph = tree.xpath('//meta[@property="og:url"]/@content')
    if len(nodes) != 1 or canonical != [url] or graph != [url]:
        raise SourceError("Native complete advert/canonical/OpenGraph identity does not reconcile")
    headings = nodes[0].xpath('.//h1')
    if len(headings) != 1 or not clean(headings[0].text_content()):
        raise SourceError("Complete native advert title/header required")
    references = []
    for link in nodes[0].xpath('.//a[@href]'):
        uri = urljoin(url, link.get("href"))
        parsed = urlsplit(uri)
        if (parsed.scheme == "https" and not parsed.username and not parsed.password
                and not re.search(r"session|token|nonce|csrf|password|(?:^|[?&])key=", uri, re.I)
                and not re.search(r"/(?:apply|login|register|bewerben|subscribe|contact|kontakt|maps?|vcard)(?:[/.?]|$)|[?&]ac=(?:application|jobad_map|jobalert)|\.vcf(?:[?#]|$)", uri, re.I)):
            references.append({"url": uri, "text": clean(link.text_content()), "independently_verified": False})
    safe, media = safe_primary(nodes[0])
    text = clean(safe.text_content())
    if len(text) < len(clean(headings[0].text_content())) + 40:
        raise SourceError("Native advert body is missing")
    schemas = []
    for script in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            parsed = json.loads(script)
        except ValueError:
            raise SourceError("Published structured advert is malformed") from None
        queue = parsed if isinstance(parsed, list) else [parsed]
        for item in queue:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("@graph"), list):
                queue.extend(item["@graph"])
            if item.get("@type") == "JobPosting" or isinstance(item.get("@type"), list) and "JobPosting" in item["@type"]:
                schemas.append(item)
    if len(schemas) != 1:
        raise SourceError("Expected exactly one published JobPosting in this qualified complete-advert template")
    return {**base("berlin_state_public_advert"), "id": SOURCE + "::" + number,
            "native_id": number, "url": url, "source_url": url,
            "native_canonical_url": canonical[0], "native_open_graph_url": graph[0],
            "title": clean(headings[0].text_content()), "full_primary_body": html.tostring(safe, encoding="unicode"),
            "source_primary_text": text, "description": text,
            "body_representation": "native_berlin_complete_public_portal_advert",
            "source_body_untruncated": True, "source_active_vacancy_verified": False,
            "published_schema_job_postings": schemas,
            "native_advertised_references": references,
            "native_nontext_media_count": media, "nontext_media_requirements_verified": False,
            "actual_application_form_material_list_verified": False,
            "employer_primary_and_external_attachments_independently_verified": False,
            "source_dates_deadlines_and_worksite_require_reconciliation": True,
            "scripts_controls_hydration_or_nonce_exported": False,
            "original_published_at": None, "returned_count": 1, "source_result_count": None,
            "raw_html_sha256": hashlib.sha256(raw).hexdigest()}


def detail(url, *, client=None):
    identity(url)
    transport = client or Client(url_check=checked_url)
    response = transport.get(url)
    if response.status != 200:
        raise SourceError("Complete native advert HTTP200 required", http_status=response.status)
    result = parse_detail(response.body, url)
    result.update(native_HTTP_status=response.status, native_GET_requests=getattr(transport, "get_count", None),
                  native_read_POST_requests=getattr(transport, "read_post_count", None))
    return result
