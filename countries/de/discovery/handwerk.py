"""Original Handwerk HTML read contracts; no source JavaScript or application API.

The native pages have variable, overlapping row sets. Preserve each entire
response and its advertised next page; neither a fixed page size nor an exact
total is inferred. Radar inline fields and standalone chamber primaries differ.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from lxml import html
from lxml.etree import ParserError

from meinpraktikum import clean, safe_primary
from network import Client, SourceError, base_result, personal_use, positive_page

ORIGIN = "https://www.lehrstellen-radar.de"
LIST = ORIGIN + "/5100,0,lsrlist.html"
ENTRY = ORIGIN + "/5100,0,lsrsearch.html"
TERMS = ORIGIN + "/impressum_lehrstellenradar"
PRIMARY = {
    "https://www.hwk-wiesbaden.de": "44",
    "https://www.hwk-ufr.de": "78",
}
SCOPES = {"internships": "search-pr", "apprenticeships": "search-ls"}
LIMITS = [
    "Only the explicit native postcode/radius offering scope is read. A circle is not a Hesse, Germany, employer or weekly census.",
    "Native first/next pages can contain variable and overlapping records. Preserve all source IDs and native continuations; do not multiply page count by an assumed page size or sum repeated rows.",
    "Training firms are organisation context, not vacancy rows. Only native internship or apprenticeship offer switches are exposed; no career, skill, degree or employer acquisition query.",
    "Native inline offer fields can omit requirements present on a standalone chamber primary. Two exact ODAV chamber origins are qualified; other primary links remain unverified references without automatic redirects.",
    "A source internship label, minimum school qualification, full-time header or firm address does not establish university recognition, applicant eligibility or Germany-based remote permission.",
    "Source start dates, dates in descriptions and observation are not verified original publication, reopening or a complete historical week.",
    "No source script, consent widget, image, map, contact, vCard, application, account, session or credential operation. Source scripts are not fetched even when the HTML refers to them.",
]


def scope_arguments(scope, postal_code, radius_km, page):
    if not isinstance(scope, str) or scope not in SCOPES or not isinstance(postal_code, str) or not re.fullmatch(r"[0-9]{5}", postal_code):
        raise SourceError("Explicit native offer scope and five-digit postcode required")
    if type(radius_km) is not int or not 1 <= radius_km <= 1000:
        raise SourceError("Radius must be an integer1..1000; this is a client bound, not verified national membership")
    positive_page(page)
    return {"scope": scope, "postal_code": postal_code, "radius_km": radius_km, "page": page}


def inventory_uri(scope, postal_code, radius_km=25, page=1):
    scope_arguments(scope, postal_code, radius_km, page)
    fields = {"search-fromsearchform": "1", SCOPES[scope]: "1", "search-job": "",
              "search-plz": postal_code, "search-radius": str(radius_km)}
    # Initial search and the native resultSearch paging form are distinct
    # observed carriers. Continuation retains every actual hidden filter.
    query = {**fields, "send": "Suchen"} if page == 1 else {
        "search-switchtype": "", "page": str(page), **fields,
    }
    return LIST + "?" + urlencode(query)


def checked_url(url, method="GET"):
    if (method != "GET" or not isinstance(url, str) or not 0 < len(url) <= 4096
            or url != url.strip() or any(c.isspace() or ord(c) < 32 for c in url)):
        raise SourceError("Only bounded exact public Handwerk GET routes are supported")
    p = urlsplit(url)
    origin = p.scheme + "://" + p.netloc
    if origin not in {ORIGIN, *PRIMARY} or p.fragment or "%" in p.path or "\\" in p.path:
        raise SourceError("Unqualified Handwerk origin or route")
    if p.path == "/robots.txt" and not p.query:
        return url
    if origin in PRIMARY:
        q = parse_qs(p.query, keep_blank_values=True)
        if (p.path != "/" + PRIMARY[origin] + ",0,jobboardofferdetail.html" or set(q) != {"id"}
                or len(q["id"]) != 1 or not re.fullmatch(r"[1-9][0-9]{0,19}", q["id"][0])):
            raise SourceError("Only qualified standalone chamber primary IDs are supported")
        return url
    if origin != ORIGIN or p.path != "/5100,0,lsrlist.html":
        raise SourceError("No script, application, firm directory or unqualified Handwerk route")
    try:
        q = parse_qs(p.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise SourceError("Malformed native Handwerk scope") from None
    if any(len(v) != 1 for v in q.values()):
        raise SourceError("Duplicate native Handwerk scope fields")
    native = {k: v[0] for k, v in q.items()}
    scope = next((name for name, key in SCOPES.items() if native.get(key) == "1"), None)
    if scope is None:
        raise SourceError("Explicit native offer switch required; an empty query is not all supply")
    try:
        number = int(native.get("page", "1"))
        radius = int(native.get("search-radius", ""))
    except ValueError:
        raise SourceError("Native page/radius integers required") from None
    scope_arguments(scope, native.get("search-plz"), radius, number)
    expected = parse_qs(urlsplit(inventory_uri(scope, native["search-plz"], radius, number)).query, keep_blank_values=True)
    if q != expected:
        raise SourceError("Only exact empty-keyword native search/paging fields are supported")
    return url


def document(raw):
    if not isinstance(raw, bytes) or not re.search(rb"</html\s*>\s*$", raw, re.I):
        raise SourceError("Complete native Handwerk HTML response required; no clipped page")
    try:
        return html.fromstring(raw)
    except (ValueError, TypeError, ParserError) as error:
        raise SourceError("Malformed native Handwerk document") from error


def primary_identity(uri):
    checked_url(uri)
    p = urlsplit(uri)
    origin = p.scheme + "://" + p.netloc
    if origin not in PRIMARY:
        raise SourceError("A qualified standalone chamber primary URI is required")
    return PRIMARY[origin] + "_" + parse_qs(p.query)["id"][0]


def parse_inventory(raw, scope, postal_code, radius_km=25, page=1, *, first_native_pages=None):
    args = scope_arguments(scope, postal_code, radius_km, page)
    tree = document(raw)
    forms = tree.xpath('//form[@id="resultSearch"]')
    if len(forms) != 1 or forms[0].get("method", "").lower() != "get":
        raise SourceError("Exact native Radar resultSearch form required")
    form = forms[0]
    expected = {"search-switchtype": "", "page": str(page), "search-fromsearchform": "1",
                SCOPES[scope]: "1", "search-job": "", "search-plz": postal_code, "search-radius": str(radius_km)}
    inputs = form.xpath('.//input[@name]')
    fields = {e.get("name"): e.get("value", "") for e in inputs}
    # Actual continuation HTML repeats the identical switchtype input. Preserve
    # those occurrences; only this verified duplicate is acceptable and its
    # values must agree. Never silently choose one conflicting page/filter.
    if (fields != expected or any(e.get("name") not in expected
            or e.get("value", "") != expected[e.get("name")] for e in inputs)
            or any(sum(e.get("name") == key for e in inputs) > 1 for key in fields if key != "search-switchtype")):
        raise SourceError("Native Handwerk form filters/page differ; no scope inference")
    lists = tree.xpath('//*[@id="lsrresultlist"]')
    if len(lists) != 1:
        raise SourceError("One complete native Radar result list required")
    rows = lists[0].xpath('.//a[@data-resultid]')
    if not rows:
        message = "Leider ergab die Suche keine Treffer."
        visible = clean(" ".join(tree.xpath('//text()[not(ancestor::script or ancestor::style or ancestor::template or ancestor::noscript)]')))
        if (page != 1 or first_native_pages is not None or message not in visible
                or form.xpath('.//a[@data-page]') or tree.xpath('//div[starts-with(@id,"detail_")]')):
            raise SourceError("Unqualified empty Radar response; no empty-market fallback")
        result = base_result("handwerk", "handwerk_radar_inventory")
        result.update(
            source_url=LIST, requested_url=inventory_uri(**args), source_board_url=ENTRY,
            native_scope=args, native_page=page, native_pages=None, returned_count=0, metadata=[],
            native_form_field_occurrences=[{"name": e.get("name"), "value": e.get("value", "")} for e in inputs],
            source_result_count=None, source_count_unit="native_offer_records_with_cross_page_overlap",
            native_fixed_page_size_verified=False, exact_native_total_verified=False,
            native_empty_scoped_result=True, native_empty_result_text=message,
            native_previous_page=None, native_next_page=None, has_more=False, next_request=None,
            source_metadata_untruncated=True, native_inline_fields_untruncated=True,
            role_interest_query_filters=False, organisations_are_not_vacancy_rows=True,
            raw_html_sha256=hashlib.sha256(raw).hexdigest(), original_published_at=None,
            limits=LIMITS, source_terms_url=TERMS,
        )
        return result
    pager = re.findall(r"Seite\s+([0-9]+)\s+von\s+([0-9]+)", clean(form.text_content()))
    if len(pager) != 1 or int(pager[0][0]) != page or not 1 <= page <= int(pager[0][1]):
        raise SourceError("Native Handwerk page/ceiling missing or changed; no empty-market fallback")
    final = int(pager[0][1])
    if first_native_pages is not None and final != first_native_pages:
        raise SourceError("Native Handwerk page ceiling changed during continuation")
    controls = form.xpath('.//a[@data-page]/@data-page')
    expected_controls = ([str(page - 1)] if page > 1 else []) + ([str(page + 1)] if page < final else [])
    if controls != expected_controls or not rows:
        raise SourceError("Native previous/next controls or nonempty bounded page differ")
    bodies = tree.xpath('//div[starts-with(@id,"detail_")]')
    bodymap = {body.get("id").removeprefix("detail_"): body for body in bodies}
    if len(bodymap) != len(bodies) or len(bodies) != len(rows):
        raise SourceError("Every native offer requires its complete matching inline field block")
    records, seen = [], set()
    for row in rows:
        identifier = row.get("data-resultid")
        if (not re.fullmatch(r"[1-9][0-9]{0,6}_[1-9][0-9]{0,19}", identifier or "")
                or identifier in seen or identifier not in bodymap):
            raise SourceError("Native Radar identity is missing, duplicated or unmatched")
        seen.add(identifier)
        titles = row.xpath('.//p[contains(concat(" ",normalize-space(@class)," ")," list-group-item-heading ")]')
        if len(titles) != 1:
            raise SourceError("Native Handwerk offer title missing")
        title, metadata = clean(titles[0].text_content()), clean(row.text_content())
        model = r"\bPraktik(?:um|a)\b" if scope == "internships" else r"\bLehrstelle(?:n)?\b"
        if not title or not re.search(model, metadata):
            raise SourceError("Native offer model/title differs from requested switch")
        body = bodymap[identifier]
        links = [a.get("href") for a in body.xpath('.//a[@href]') if a.text_content().strip() == "Details"]
        if len(links) != 1 or not isinstance(links[0], str) or len(links[0]) > 4096:
            raise SourceError("One independently advertised standalone primary reference required")
        safe, media = safe_primary(body)
        text = clean(safe.text_content())
        if title not in text:
            raise SourceError("Native inline field title and metadata differ")
        try:
            supported = primary_identity(links[0]) == identifier
        except SourceError:
            supported = False
        records.append({
            "id": "handwerk::" + identifier, "native_radar_id": identifier, "title": title,
            "metadata_text": metadata, "native_inline_text": text,
            "native_inline_html": html.tostring(safe, encoding="unicode"),
            "native_primary_reference": links[0], "standalone_primary_route_qualified": supported,
            "native_nontext_media_count": media, "nontext_media_requirements_verified": False,
            "inline_fields_are_not_verified_complete_primary": True,
            "original_published_at": None, "full_posting_reviewed": False, "reviewed_by_model": False,
        })
    result = base_result("handwerk", "handwerk_radar_inventory")
    more = page < final
    result.update(
        source_url=LIST, requested_url=inventory_uri(**args), source_board_url=ENTRY,
        native_scope=args, native_page=page, native_pages=final, returned_count=len(records), metadata=records,
        native_empty_scoped_result=False,
        native_form_field_occurrences=[{"name": e.get("name"), "value": e.get("value", "")} for e in inputs],
        source_result_count=None, source_count_unit="native_offer_records_with_cross_page_overlap",
        native_fixed_page_size_verified=False, exact_native_total_verified=False,
        native_previous_page=page - 1 if page > 1 else None, native_next_page=page + 1 if more else None,
        has_more=more, next_request={"tool": "de_public_handwerk_inventory", "backend_native_tool": "handwerk_inventory",
            "arguments": {**args, "page": page + 1, "first_native_pages": final, "personal_noncommercial_use": True}} if more else None,
        source_metadata_untruncated=True, native_inline_fields_untruncated=True,
        role_interest_query_filters=False, organisations_are_not_vacancy_rows=True,
        raw_html_sha256=hashlib.sha256(raw).hexdigest(), original_published_at=None,
        limits=LIMITS, source_terms_url=TERMS,
    )
    return result


def inventory(scope, postal_code, radius_km=25, page=1, *, first_native_pages=None, personal_noncommercial_use=False, client=None):
    personal_use(personal_noncommercial_use)
    if (page == 1 and first_native_pages is not None or page != 1 and (
            type(first_native_pages) is not int or not page <= first_native_pages <= 10000)):
        raise SourceError("Continuation requires its original native page ceiling; initial page must start fresh")
    uri = inventory_uri(scope, postal_code, radius_km, page)
    response = (client or Client(url_check=checked_url)).get(uri)
    if response.status != 200 or "html" not in response.content_type.lower():
        raise SourceError("Unqualified Handwerk inventory HTTP/content response")
    return parse_inventory(response.body, scope, postal_code, radius_km, page, first_native_pages=first_native_pages)


def parse_detail(raw, url):
    identifier = primary_identity(url)
    tree = document(raw)
    mains, headings = tree.xpath('//main'), tree.xpath('//h1')
    canonicals = tree.xpath('//link[@rel="canonical"]/@href')
    graph_uris = tree.xpath('//meta[@property="og:url"]/@content')
    if canonicals != [url] or graph_uris != [url]:
        raise SourceError("Standalone chamber canonical/OpenGraph URI differs from the requested native offer")
    if len(mains) != 1 or len(headings) != 1 or headings[0] not in mains[0].iterdescendants():
        raise SourceError("Complete qualified chamber primary main/title required")
    header = clean(headings[0].text_content())
    if not header or not re.search(r"\b(?:Praktikum|Praktika|Lehrstelle|Lehrstellen)\b", header):
        raise SourceError("Standalone chamber primary offer model is missing")
    safe, media = safe_primary(mains[0])
    text = clean(safe.text_content())
    if header not in text or len(text) <= len(header):
        raise SourceError("Complete native chamber primary text missing")
    result = base_result("handwerk", "handwerk_primary_detail")
    result.update(
        id="handwerk::" + identifier, native_radar_id=identifier, url=url, source_url=url,
        native_canonical_url=canonicals[0], native_open_graph_url=graph_uris[0],
        title=header, native_header_text=header, source_primary_text=text, description=text,
        description_html=html.tostring(safe, encoding="unicode"),
        body_representation="native_handwerk_odav_complete_primary_main",
        source_body_untruncated=True, native_nontext_media_count=media,
        nontext_media_requirements_verified=False, related_job_and_firm_context_is_not_this_roles_requirements=True,
        actual_application_form_material_list_verified=False,
        scripts_controls_hydration_or_nonce_exported=False, original_published_at=None,
        returned_count=1, source_result_count=None, raw_html_sha256=hashlib.sha256(raw).hexdigest(),
        limits=LIMITS, source_terms_url=TERMS,
    )
    return result


def detail(url, *, personal_noncommercial_use=False, client=None):
    personal_use(personal_noncommercial_use)
    primary_identity(url)
    response = (client or Client(url_check=checked_url)).get(url)
    if response.status != 200 or "html" not in response.content_type.lower():
        raise SourceError("Unqualified standalone chamber primary HTTP/content response")
    return parse_detail(response.body, url)
