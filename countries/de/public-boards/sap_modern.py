"""Original anonymous reader for the separately qualified modern SAP careers front."""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from lxml import html
from native_flight import resolve

import sap_flight

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from shared.public_http import SourceError as PublicError  # noqa: E402
from shared.public_http import request, robot_policy  # noqa: E402

SOURCE = "sap_modern"
ORIGIN = "https://jobs.sap.com"
LIST_PATH = "/en/jobs/"
BOARD = ORIGIN + LIST_PATH
LIMITS = [
    "This is the modern SAP front, separate from legacy careers.sap.com RMK. Counts are neither combined nor a national/employer census.",
    "Only the whole native front and its advertised Germany country facet are qualified. No title, team, experience, contract, keyword, candidate or custom-sort acquisition.",
    "Every page retains its native count, size, page and source default newest order. Freeze the first total and reconcile every continuation; current metadata is not atomic historical supply.",
    "Inline and cached Flight record namespaces are parsed as data, without script/module execution. Complete resolved source models must agree across all frames.",
    "Primary rendered-source HTML, separate page context, schema, requisition reference, URL ID and native clocks remain distinct. Schema summaries are not substituted for full primary content.",
    "Native part/full-time, country, work-pattern and posting/display dates do not establish an exact student contract, Germany remote eligibility, original publication or individual fit.",
    "Only anonymous first-party HTML and robots are requested. Scripts, images, account, application, personalization and contact routes are excluded; links remain data.",
]


class SapModernError(ValueError):
    def __init__(self, code, *, http_status=None, retry_after=None):
        super().__init__(code)
        self.http_status, self.retry_after = http_status, retry_after


def inventory_uri(country=None, page=1):
    if country not in (None, "DE") or type(page) is not int or not 1 <= page <= 100000:
        raise SapModernError("invalid_native_sap_partition")
    values = (["country=Germany"] if country else []) + (["page=" + str(page)] if page > 1 else [])
    return BOARD + ("?" + "&".join(values) if values else "")


def checked_url(url, operation):
    if (not isinstance(url, str) or url != url.strip() or len(url) > 2048
            or any(ord(c) < 32 for c in url)):
        raise SapModernError("invalid_native_sap_uri")
    parsed = urlsplit(url)
    if parsed.scheme + "://" + parsed.netloc != ORIGIN or parsed.fragment:
        raise SapModernError("unqualified_native_sap_origin")
    if operation == "inventory":
        query = parse_qs(parsed.query, keep_blank_values=True)
        if (parsed.path != LIST_PATH or set(query) - {"country", "page"}
                or any(len(v) != 1 for v in query.values())
                or query.get("country") not in (None, ["Germany"])
                or query.get("page") is not None and not re.fullmatch(r"[1-9][0-9]{0,5}", query["page"][0])):
            raise SapModernError("unqualified_native_sap_inventory")
        country, page = ("DE" if "country" in query else None), int(query.get("page", ["1"])[0])
        if url != inventory_uri(country, page):
            raise SapModernError("noncanonical_native_sap_partition")
    elif operation == "detail":
        if parsed.query or not re.fullmatch(r"/en/jobs/[1-9][0-9]{5,19}/[a-z0-9]+(?:-[a-z0-9]+)*/", parsed.path):
            raise SapModernError("unqualified_native_sap_posting")
    else:
        raise SapModernError("unsupported_native_sap_operation")
    return url


def partition(url):
    checked_url(url, "inventory")
    query = parse_qs(urlsplit(url).query)
    return ("DE" if "country" in query else None), int(query.get("page", ["1"])[0])


def native_id(url):
    checked_url(url, "detail")
    return "sap_modern::" + urlsplit(url).path.split("/")[3]


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def search_model(body):
    try:
        frames, candidates = sap_flight.data_frames(body), []
        for frame in frames:
            for record in frame["records"].values():
                for value in nodes(record):
                    if {"jobs", "totalPages", "totalJobs", "currentPage", "pageSize"} <= set(value):
                        candidates.append(resolve(value, frame["records"]))
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise SapModernError("incomplete_or_ambiguous_native_sap_frames") from None
    if not candidates or any(item != candidates[0] for item in candidates[1:]):
        raise SapModernError("conflicting_native_sap_job_models")
    return candidates[0], len(frames), len(candidates)


def inventory(body, url):
    country, number = partition(url)
    model, frame_count, model_count = search_model(body)
    total, pages, size, rows = (model.get(k) for k in ("totalJobs", "totalPages", "pageSize", "jobs"))
    criteria = {"page": number, "pagesize": 12, "orderby": 1, "includeFilters": True}
    if country:
        criteria["country"] = ["Germany"]
    if (type(total) is not int or not 0 <= total <= 1000000
            or type(pages) is not int or pages != max(1, (total + 11) // 12)
            or type(size) is not int or size != 12
            or type(model.get("currentPage")) is not int or model["currentPage"] != number or number > pages
            or not isinstance(rows, list) or len(rows) != min(12, max(0, total - (number - 1) * 12))
            or model.get("locale") != "en" or model.get("matcherSearchCriteria") != criteria
            or model.get("jobMatcherEnabled") is not False or model.get("profileEditingEnabled") is not False
            or not isinstance(model.get("filterMetadata"), dict) or not isinstance(model.get("displayMetadata"), dict)):
        raise SapModernError("native_sap_count_page_scope_or_guest_echo_differs")
    sorts = model["filterMetadata"].get("sortOptions")
    if not isinstance(sorts, list) or any(not isinstance(v, dict) for v in sorts):
        raise SapModernError("invalid_native_sap_sort_options")
    default_sort = [v for v in sorts if v.get("isDefault") is True]
    if len(default_sort) != 1 or default_sort[0].get("value") != 1 or default_sort[0].get("kind") != "DisplayDate":
        raise SapModernError("native_sap_default_sort_changed")
    listings, seen = [], set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or not re.fullmatch(r"[1-9][0-9]{5,19}", row["id"])
                or not isinstance(row.get("url"), str) or not row["url"].startswith(LIST_PATH)
                or any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("title", "locations"))):
            raise SapModernError("incomplete_native_sap_metadata_row")
        uri = ORIGIN + row["url"]
        identity = native_id(uri)
        if identity != "sap_modern::" + row["id"] or identity in seen:
            raise SapModernError("conflicting_or_duplicate_native_sap_job_id")
        seen.add(identity)
        listings.append({"id": identity, "native_job_id": row["id"], "url": uri, "title": row["title"],
                         "native_row": row, "native_country_partition": country,
                         "native_model_label": None, "original_source_date": None,
                         "source_body_complete": False, "applicant_fit_assessed": False})
    more = number < pages
    return {"source": SOURCE, "status": "ok", "kind": "german_public_board_page",
            "source_url": url, "requested_url": url, "board_url": BOARD,
            "native_country_partition": country, "listings": listings, "returned_count": len(rows),
            "source_result_count": total, "native_frame_count": frame_count, "native_job_model_count": model_count,
            "native_frames_agree": True, "native_search_criteria": model["matcherSearchCriteria"],
            "native_filter_metadata": model["filterMetadata"], "native_display_metadata": model["displayMetadata"],
            "pagination": {"page": number, "page_size": size, "native_total": total, "native_pages": pages,
                           "first_page_total": total, "has_more": more, "next_page": number + 1 if more else None,
                           "next_url": inventory_uri(country, number + 1) if more else None},
            "hydration_credentials_exported_or_used": False, "source_scripts_images_or_application_requested": False,
            "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS}


def public_section(value):
    node = html.fragment_fromstring(value or " ", create_parent="section")
    for child in node.xpath(".//script|.//style|.//iframe|.//object|.//embed|.//form|.//input"):
        child.drop_tree()
    for child in node.iter():
        for name in list(child.attrib):
            if name.lower().startswith(("on", "data-")) or name.lower() in {"href", "src"} and re.match(r"\s*(?:javascript|vbscript|data):", child.attrib[name], re.I):
                del child.attrib[name]
        if child.tag in {"p", "li", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "section", "ul", "ol", "tr", "td"}:
            child.text, child.tail = " " + (child.text or ""), " " + (child.tail or "")
    return {"text": " ".join(node.text_content().split()), "html": html.tostring(node, encoding="unicode", method="html")}


def detail(body, url):
    identity = native_id(url)
    tree = html.fromstring(body)
    schemas = []
    for text in tree.xpath('//script[@type="application/ld+json"]/text()'):
        value = sap_flight.strict_json(text)
        schemas.extend(node for node in nodes(value) if node.get("@type") == "JobPosting")
    headings = [" ".join(n.text_content().split()) for n in tree.xpath("//h1")]
    primary = tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," max-w-3xl ") and ./h2[normalize-space(.)="The Role"]]')
    if len(schemas) != 1 or len(primary) != 1 or len(headings) != 1:
        raise SapModernError("incomplete_native_sap_primary_structure")
    schema = schemas[0]
    reference = schema.get("identifier")
    organization = schema.get("hiringOrganization")
    if (schema.get("url") != url or schema.get("mainEntityOfPage") != url
            or schema.get("title") != headings[0] or not isinstance(schema.get("description"), str)
            or not isinstance(reference, dict) or not isinstance(reference.get("value"), str) or not reference["value"].strip()
            or not isinstance(organization, dict) or organization.get("name") != "SAP Careers"
            or organization.get("url") != ORIGIN):
        raise SapModernError("conflicting_native_sap_schema_identity")
    raw = html.tostring(primary[0], encoding="unicode", method="html")
    section, schema_section = public_section(raw), public_section(schema["description"])
    if len(section["text"]) < 100:
        raise SapModernError("missing_complete_native_sap_primary_body")
    context = [public_section(html.tostring(node, encoding="unicode", method="html"))
               for node in tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," prose ")]')
               if primary[0] not in node.iterancestors()]
    facts = [{"label": " ".join(term.text_content().split()),
              "value": " ".join(term.getnext().text_content().split())}
             for term in tree.xpath("//dl/dt") if term.getnext() is not None and term.getnext().tag == "dd"]
    return {"source": SOURCE, "status": "ok", "kind": "german_public_board_detail", "id": identity,
            "native_job_id": identity.split("::", 1)[1], "native_requisition_reference": reference["value"],
            "url": url, "source_url": url, "title": schema["title"],
            "description": section["text"], "description_html": section["html"],
            "native_primary_raw_html": raw, "native_page_context_sections": context, "native_display_facts": facts,
            "native_job_posting": schema, "native_schema_description_section": schema_section,
            "native_description_characters": len(section["text"]),
            "body_representation": "native_sap_modern_complete_primary_html", "source_body_untruncated": True,
            "schema_description_used_as_full_body": False, "full_posting_reviewed": False, "original_published_at": None,
            "hydration_credentials_exported_or_used": False, "source_scripts_images_or_application_requested": False,
            "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS}


def read(operation, url, *, transport=request):
    checked_url(url, operation)
    try:
        rules, policy = robot_policy(ORIGIN, transport=transport)
        if rules is not None and not rules.can_fetch("job-market-mcp", url):
            raise SapModernError("robots_denied")
        response = transport(url, accept="text/html", timeout=20)
        raw = response.get("body")
        if (response.get("http_status", 200) != 200 or not isinstance(raw, bytes)
                or len(raw) > sap_flight.MAX_BYTES
                or "html" not in (response.get("content_type") or "").lower()):
            raise SapModernError("unexpected_native_sap_content")
        result = inventory(raw, url) if operation == "inventory" else detail(raw, url)
        return {**result, "policy": policy, "provenance": {
            "requested_url": url, "http_status": 200, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            **{k: response.get(k) for k in ("requested_at", "observed_at", "content_type")}}}
    except PublicError as error:
        raise SapModernError(error.code, http_status=error.http_status, retry_after=error.retry_after) from None
