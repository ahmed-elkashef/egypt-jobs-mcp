"""Original native AUBI-plus country/model inventory and public-advert reader.

Native company groups expose overlapping offers. The displayed Plaetze count
is retained separately from URI counts; pagination follows published controls.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlsplit

from lxml import html
from lxml.etree import ParserError

from meinpraktikum import clean, safe_primary
from network import Client, SourceError, base_result

ORIGIN = "https://www.aubi-plus.de"
ENTRY = ORIGIN + "/suchmaschine/suche/"
SOURCE = "aubi_plus"
SCOPES = {"all": None, "student_internship": "studentenpraktikum", "working_student": "werkstudent"}
KINDS = {"ausbildung", "duales-studium", "schuelerpraktikum", "praktikum", "werkstudium", "abschlussarbeitsthema", "job"}
DEFAULTS = {"s": "", "anzahl": "10", "fGeo": "25", "fBptl": "0", "mSuggest": "", "aSuggest": "",
            "aSuggestLat": "0", "aSuggestLon": "0", "bAZA": "0", "bAZF": "0", "bAZS": "0", "bAZU": "0", "fBlitzbewerbung": "0"}
LIMITS = [
    "Native German offering views, not the German market, all employers, a historical week or certified university eligibility.",
    "Student-internship labels can include school/EQ/retraining placements; working-student views can include ambiguous study funding and generic job routes. Full-body model reconciliation is required.",
    "Native grouped offers overlap across pages. Preserve every occurrence and context; Plaetze totals are not qualified as distinct advert counts. Never derive pages from total/anzahl.",
    "Source total drift is a limitation, not completion. Follow exact scope/country-retaining next controls, including the observed disabled terminal format.",
    "Strict UTF-8 public HTML header/body/facts and published application information remain separate from source schema, employer originals, nontext requirements and actual application forms.",
    "Malformed published JSON-LD is reported and hashed without silent repair or date/eligibility promotion. Start dates and source labels are not original-publication clocks.",
    "No source script, login, cookie/session, application, bookmark, subscription, contact, map or payment request; no source implementation is copied.",
]


def has_class(node, name):
    return name in node.get("class", "").split()


def native_query(url):
    p = urlsplit(url)
    if p.path != "/suchmaschine/suche/":
        raise SourceError("Exact native search route required")
    try:
        q = parse_qs(p.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise SourceError("Malformed native query") from None
    countries, types = [k for k in q if k in {"fLand[]", "fLand[0]"}], [k for k in q if k in {"fTyp[]", "fTyp[0]"}]
    if (set(q) - {*DEFAULTS, "seite", "fLand[]", "fLand[0]", "fTyp[]", "fTyp[0]"}
            or any(len(v) != 1 for v in q.values()) or len(countries) > 1 or len(types) > 1
            or countries and q[countries[0]] != ["deutschland"]
            or any(q[k] != [v] for k, v in DEFAULTS.items() if k in q)):
        raise SourceError("Only qualified native German model/position fields; no keyword, extra geography or action")
    if p.query and not countries:
        raise SourceError("Native country must remain explicitly Germany")
    selected = q[types[0]][0] if types else None
    matches = [scope for scope, value in SCOPES.items() if value == selected]
    number = q.get("seite", ["1"])[0]
    if not matches or not re.fullmatch(r"[1-9][0-9]{0,4}", number) or int(number) > 10000:
        raise SourceError("Unqualified native model/page")
    return matches[0], int(number)


def checked_url(url, method="GET"):
    if method != "GET" or not isinstance(url, str) or not 0 < len(url) <= 4096:
        raise SourceError("Bounded anonymous native GET only")
    p = urlsplit(url)
    path = unquote(p.path)
    if (p.scheme + "://" + p.netloc != ORIGIN or p.fragment or "%" in path or "\\" in path
            or any(c.isspace() or ord(c) < 32 for c in url + path)):
        raise SourceError("Unqualified origin or ambiguous route")
    if p.path == "/robots.txt" and not p.query:
        return url
    match = re.fullmatch(r"/([a-z-]+)/[A-Za-z0-9_.~-]+-([1-9][0-9]{0,19})/", path)
    if match and match[1] in KINDS and ".." not in path and not p.query:
        return url
    native_query(url)
    return url


def identity(url):
    checked_url(url)
    match = re.fullmatch(r"/([a-z-]+)/[A-Za-z0-9_.~-]+-([1-9][0-9]{0,19})/", urlsplit(url).path)
    if not match or match[1] not in KINDS:
        raise SourceError("Exact acquired native advert URI required")
    return match[1], match[2], SOURCE + "::" + match[1] + "::" + match[2]


def arguments(scope, page=1, first_page_total=None, continuation_url=None):
    if not isinstance(scope, str) or scope not in SCOPES or type(page) is not int or not 1 <= page <= 10000:
        raise SourceError("Exact native scope and bounded integer page required")
    if page == 1:
        if first_page_total is not None or continuation_url is not None:
            raise SourceError("Initial page cannot carry continuation state")
    elif (type(first_page_total) is not int or not 0 < first_page_total <= 10000000
          or not isinstance(continuation_url, str)):
        raise SourceError("Continuation needs its original native counter and acquired next URI")
    else:
        checked_url(continuation_url)
        if native_query(continuation_url) != (scope, page):
            raise SourceError("Acquired next URI changed scope or page")


def initial_uri(scope):
    if scope not in SCOPES:
        raise SourceError("Unknown native scope")
    return ENTRY + ("?" + urlencode([("fLand[]", "deutschland"), ("fTyp[]", SCOPES[scope])]) if SCOPES[scope] else "")


def document(raw):
    if not isinstance(raw, bytes) or not re.search(rb"</html\s*>\s*$", raw, re.I):
        raise SourceError("Whole native HTML required; no clipping or empty/login substitute")
    try:
        return html.fromstring(raw.decode("utf-8"))
    except (ValueError, TypeError, ParserError) as error:
        raise SourceError("Complete strict UTF-8 HTML required") from error


def base(kind):
    return {**base_result(SOURCE, kind), "source_entry_url": ENTRY, "limits": LIMITS}


def parse_inventory(raw, scope="all", page=1, *, first_page_total=None, continuation_url=None):
    arguments(scope, page, first_page_total, continuation_url)
    tree = document(raw)
    forms = tree.xpath('//form[contains(concat(" ",normalize-space(@class)," ")," suchmaschine-form ")]')
    roots = tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," result-container ")]')
    headings = tree.xpath('//title/text()')
    selected = tree.xpath('//input[@name="fTyp[]" and @checked]/@value')
    countries = tree.xpath('//input[@name="fLand[]" and @checked]/@value')
    if (len(forms) != 1 or forms[0].get("action") != ENTRY or forms[0].get("method", "").lower() != "get"
            or len(roots) != 1 or countries != ["deutschland"]
            or selected != ([SCOPES[scope]] if SCOPES[scope] else []) or len(headings) != 1):
        raise SourceError("Native form, complete result root or selected country/model changed")
    counter = re.fullmatch(r"([0-9][0-9.]*) Plätze gefunden", clean(headings[0]))
    if not counter:
        raise SourceError("Native Plaetze counter missing")
    total = int(counter[1].replace(".", ""))
    if not 0 < total <= 10000000 or first_page_total is not None and total != first_page_total:
        raise SourceError("Native counter moved or empty format is unqualified", observed_total=total, first_page_total=first_page_total)
    current = tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," pagination ")]//a[contains(concat(" ",normalize-space(@class)," ")," bg-info ")]')
    if len(current) != 1 or clean(current[0].text_content()) != str(page):
        raise SourceError("Native highlighted page reset or changed")
    current_uri = urljoin(ENTRY, current[0].get("href", ""))
    checked_url(current_uri)
    if native_query(current_uri) != (scope, page):
        raise SourceError("Native highlighted URI changed scope/page")
    groups, group_indices, rows = [], {}, []
    for anchor in roots[0].xpath('.//h2/a[@href]'):
        uri = urljoin(ENTRY, anchor.get("href"))
        kind, number, stable = identity(uri)
        parents = [n for n in anchor.iterancestors("div") if has_class(n, "my-3") and has_class(n, "rounded-3")]
        if not parents or not clean(anchor.text_content()):
            raise SourceError("Native offer/group structure is incomplete")
        group = parents[0]
        key = group.getroottree().getpath(group)
        if key not in group_indices:
            index = len(groups)
            group_indices[key] = index
            safe, _ = safe_primary(group)
            links = [{"url": urljoin(ENTRY, a.get("href")), "label": clean(a.text_content()), "independently_verified": False}
                     for a in group.xpath('.//a[starts-with(@href,"/unternehmen/")]')]
            groups.append({"native_group_index": index, "source_context_text": clean(safe.text_content()),
                           "native_company_links": links, "native_logo_alt_texts": group.xpath('.//img/@alt')})
        index = group_indices[key]
        labels = [r["label"] for r in groups[index]["native_company_links"] if r["label"]]
        offer_rows = [n for n in anchor.iterancestors("div") if has_class(n, "row")]
        if not offer_rows:
            raise SourceError("Native offer row context missing")
        rows.append({"id": stable, "native_kind": kind, "native_id": number, "url": uri,
                     "title": clean(anchor.text_content()), "company": labels[0] if labels else None,
                     "native_group_index": index, "native_offer_row_text": clean(offer_rows[0].text_content()),
                     "description": None, "original_published_at": None, "model_reconciliation_required": True,
                     "full_posting_reviewed": False, "reviewed_by_model": False})
    if not rows:
        raise SourceError("Whole visible native offer rows missing; not zero supply")
    numbered = []
    for anchor in tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," pagination ")]//a[@href]'):
        label = clean(anchor.text_content())
        if not label.isdigit():
            continue
        uri = urljoin(ENTRY, anchor.get("href"))
        checked_url(uri)
        if native_query(uri) != (scope, int(label)):
            raise SourceError("Native numbered URI changed scope/country/page")
        numbered.append({"page": int(label), "url": uri})
    paging = tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," pagination ")]//a[starts-with(@aria-label,"Weiter zu Seite ")]')
    if len(paging) != 1:
        raise SourceError("Exactly one native forward control required")
    control = paging[0]
    label, href = control.get("aria-label"), control.get("href")
    if label == "Weiter zu Seite " and href == "#" and has_class(control.getparent(), "disabled"):
        if any(item["page"] > page for item in numbered):
            raise SourceError("Disabled forward control contradicts native later pages")
        following = None
    elif label == f"Weiter zu Seite {page + 1}":
        following = urljoin(ENTRY, href or "")
        checked_url(following)
        if native_query(following) != (scope, page + 1):
            raise SourceError("Native continuation changed country/model/page")
    else:
        raise SourceError("Unqualified missing or inconsistent forward control")
    initial = total if first_page_total is None else first_page_total
    return {**base("aubi_plus_inventory"), "requested_url": continuation_url or initial_uri(scope),
            "native_scope": {"country": "deutschland", "scope": scope, "page": page},
            "metadata": rows, "native_groups": groups, "returned_count": len(rows),
            "native_group_count": len(groups), "source_result_count": total, "first_page_total": initial,
            "source_count_unit": "native_Plaetze_counter_not_qualified_as_unique_adverts",
            "native_highlighted_page_url": current_uri, "next_url": following, "has_more": following is not None,
            "native_numbered_paging_links": numbered,
            "next_request": {"scope": scope, "page": page + 1, "first_page_total": initial, "continuation_url": following} if following else None,
            "native_duplicate_occurrence_count": len(rows) - len({r["id"] for r in rows}),
            "all_source_or_student_models_reviewed": False, "raw_html_sha256": hashlib.sha256(raw).hexdigest()}


def parse_detail(raw, url):
    kind, number, stable = identity(url)
    tree = document(raw)
    canonical, graph = tree.xpath('//link[@rel="canonical"]/@href'), tree.xpath('//meta[@property="og:url"]/@content')
    headings, descriptions, facts = tree.xpath('//main//h1'), tree.xpath('//*[@id="stellenbeschreibung"]'), tree.xpath('//*[@id="sidebar"]')
    if canonical != [url] or graph != [url] or len(headings) != 1 or len(descriptions) != 1 or len(facts) != 1:
        raise SourceError("Complete native header/body/facts/canonical identity required")
    cards = [n for n in headings[0].iterancestors("div") if has_class(n, "card")]
    if not cards or len(clean(descriptions[0].text_content())) < 80:
        raise SourceError("Native complete header card or description missing")
    parts = [cards[0], descriptions[0], facts[0]]
    applications = tree.xpath('//*[@id="weitere-bewerbungsmoeglichkeiten"]')
    if len(applications) != 1:
        raise SourceError("Published native application-information panel required")
    parts += applications
    composite = html.Element("section")
    media = 0
    for part in parts:
        if any(parent in parts for parent in part.iterancestors()):
            continue
        safe, count = safe_primary(deepcopy(part))
        composite.append(safe)
        media += count
    text = clean(composite.text_content())
    schemas, errors = [], []
    for position, value in enumerate(tree.xpath('//script[@type="application/ld+json"]/text()')):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            errors.append({"native_script_position": position, "error": error.msg, "line": error.lineno,
                           "column": error.colno, "published_fragment_sha256": hashlib.sha256(value.encode()).hexdigest(), "repaired": False})
        else:
            schemas.append(parsed)
    return {**base("aubi_plus_public_advert"), "id": stable, "native_kind": kind, "native_id": number,
            "url": url, "source_url": url, "native_canonical_url": canonical[0], "native_open_graph_url": graph[0],
            "title": clean(headings[0].text_content()), "full_primary_body": html.tostring(composite, encoding="unicode"),
            "source_primary_text": text, "description": text,
            "body_representation": "native_aubi_complete_public_header_body_facts_application_information",
            "source_text_encoding": "utf-8", "source_text_decoding": "strict_utf8_before_HTML",
            "published_structured_data": schemas, "published_structured_data_parse_errors": errors,
            "malformed_published_data_repaired_or_promoted": False, "source_body_untruncated": True,
            "source_active_vacancy_verified": False, "native_nontext_media_count": media,
            "nontext_media_requirements_verified": False, "actual_application_form_material_list_verified": False,
            "employer_primary_and_external_attachments_independently_verified": False,
            "source_dates_deadlines_worksite_and_model_require_reconciliation": True,
            "scripts_controls_hydration_or_nonce_exported": False,
            "original_published_at": None, "returned_count": 1, "source_result_count": None,
            "raw_html_sha256": hashlib.sha256(raw).hexdigest()}


def read(operation, *, scope="all", page=1, first_page_total=None, continuation_url=None, url=None, client=None):
    if operation == "inventory":
        arguments(scope, page, first_page_total, continuation_url)
        requested = continuation_url or initial_uri(scope)
    elif operation == "detail":
        identity(url)
        requested = url
    else:
        raise SourceError("Unknown read-only native operation")
    transport = client or Client(url_check=checked_url)
    response = transport.get(requested)
    fields = [v.strip().lower() for v in response.content_type.split(";")]
    charsets = [v.partition("=")[2].strip(' \"') for v in fields[1:] if v.startswith("charset=")]
    if response.status != 200 or fields[0] != "text/html" or charsets != ["utf-8"]:
        raise SourceError("Exact native HTTP200 UTF-8 HTML required")
    result = (parse_inventory(response.body, scope, page, first_page_total=first_page_total, continuation_url=continuation_url)
              if operation == "inventory" else parse_detail(response.body, url))
    result.update(native_HTTP_status=response.status, native_HTTP_content_type=response.content_type,
                  native_GET_requests=getattr(transport, "get_count", None), native_read_POST_requests=getattr(transport, "read_post_count", None))
    return result
