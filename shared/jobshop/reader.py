"""Original anonymous Jobshop SSR inventory and full CMS advert reader."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from lxml import etree, html

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from public_http import MAX_BYTES, SourceError, load_json, request, robot_policy  # noqa: E402

ORIGIN = "https://www.jobs-fraport.com"
VENDOR = "https://fraport.job-shop.com"
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
SAFE_FIELDS = {
    "about", "additional", "benefits", "career_level", "cluster", "company", "company_url",
    "contact_data", "contact_persons", "contact_text", "contract_time", "contract_type", "coordinate",
    "country", "create_date", "create_date_timestamp", "department", "description", "expectation",
    "external_id", "external_reference_id", "full_address", "id", "introduction", "last_modified",
    "last_modified_timestamp", "location", "location_count", "location_objects", "offer_uuid", "offering",
    "salary", "schedule", "schema_values", "start_date", "start_date_timestamp", "start_year", "status",
    "status_change_date", "status_change_date_timestamp", "sub_title", "title", "title_slug", "url",
    "work_mode", "working_hours",
}
LIMITS = [
    "One independently identified employer board is not a Germany/employer census or a complete historical week.",
    "Only the independently qualified Fraport custom origin/current Nuxt SSR and CMS contracts are supported; a SuccessFactors profile link does not make this front a verified SAP RMK API.",
    "Inventory reconciles every SSR URI/title with native anchors and an independently advertised whole-board count, not client-filter placeholders or search-provider credentials.",
    "JobPosting and native jobData descriptions may be absent. Complete primary job-data CMS HTML, sanitized full main and secondary CMS/context sections remain separate.",
    "Schema educationRequirements may hold a work-model label; native create/update/start/validThrough clocks do not establish original publication, meaningful expiry, student eligibility or a Germany-based remote contract.",
    "No hydration credential, search API key, source script/CDN, account, application, contact or subscription request is supported. Native application form labels are data only.",
]


def origin(value):
    if value != ORIGIN:
        raise SourceError("unverified_independent_jobshop_career_origin")
    return value


def job_uri(value):
    if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 32 for c in value):
        raise SourceError("invalid_native_jobshop_uri")
    parsed = urlsplit(value)
    if parsed.scheme + "://" + parsed.netloc != ORIGIN or parsed.fragment:
        raise SourceError("unverified_native_jobshop_uri")
    query = parse_qs(parsed.query, keep_blank_values=True)
    opaque = query.get("offerApiId")
    if opaque is not None and (len(opaque) != 1 or not re.fullmatch(r"[A-Za-z0-9_+/=-]{1,128}", opaque[0])):
        raise SourceError("invalid_native_offer_reference")
    canonical = re.fullmatch(r"/jobs/[^/?#\\\s]+/(" + UUID + ")", parsed.path)
    if canonical and set(query) <= {"offerApiId"}:
        return value, ORIGIN + "::offer_uuid:" + canonical[1], canonical[1], opaque[0] if opaque else None
    if (parsed.path == "/offer-redirect/" and set(query) == {"offerApiId", "showApplicationForm"}
            and opaque and query["showApplicationForm"] == ["false"]):
        return value, ORIGIN + "::offer_reference:" + opaque[0], None, opaque[0]
    raise SourceError("account_application_or_non_native_job_route_refused")


def document(raw):
    if not isinstance(raw, bytes) or raw.startswith(b"%PDF"):
        raise SourceError("expected_native_html")
    try:
        return html.fromstring(raw.decode("utf-8-sig"))
    except (UnicodeError, ValueError, TypeError, etree.ParserError):
        raise SourceError("invalid_native_html") from None


def markup(node):
    return html.tostring(node, encoding="unicode", with_tail=False)


def sanitize(node):
    copy = html.fromstring(markup(node))
    for child in copy.xpath('.//script|.//style|.//form|.//input|.//select|.//textarea|.//button|.//iframe|.//object|.//embed'):
        child.drop_tree()
    for comment in copy.xpath(".//comment()"):
        comment.getparent().remove(comment)
    return copy


def text(node):
    copy = sanitize(node)
    for item in copy.iter():
        if item.tag in {"p", "li", "div", "br", "h1", "h2", "h3", "h4", "main", "section"}:
            item.tail = " " + (item.tail or "")
    return " ".join(copy.text_content().split())


class NativeTable:
    """Follow only selected inert reference fields, never execute hydration."""
    def __init__(self, doc):
        nodes = doc.xpath('//script[@id="__NUXT_DATA__" and @type="application/json"]')
        if len(nodes) != 1:
            raise SourceError("missing_unique_native_reference_table")
        self.steps = 0
        self.table = load_json(nodes[0].text or "")
        if not isinstance(self.table, list) or not 4 <= len(self.table) <= 1000000:
            raise SourceError("invalid_native_reference_table")
        envelope = self.unwrap(0)
        if not isinstance(envelope, dict) or "data" not in envelope:
            raise SourceError("missing_native_data_root")
        self.data = self.unwrap(envelope["data"])
        if not isinstance(self.data, dict):
            raise SourceError("invalid_native_data_root")

    def at(self, index):
        if type(index) is not int or not 0 <= index < len(self.table):
            raise SourceError("unsupported_native_reference")
        return self.table[index]

    def unwrap(self, index):
        for _ in range(8):
            node = self.at(index)
            if isinstance(node, list) and len(node) == 2 and node[0] in ("ShallowReactive", "Reactive"):
                index = node[1]
            else:
                return node
        raise SourceError("native_wrapper_cycle_or_depth")

    def selected(self, prefix):
        names = [key for key in self.data if key.startswith(prefix)]
        if len(names) != 1:
            raise SourceError("missing_unique_native_selected_field")
        return self.at(self.data[names[0]])

    def resolve(self, index, active=()):
        self.steps += 1
        if self.steps > 200000:
            raise SourceError("complete_native_projection_exceeds_budget")
        if len(active) > 64 or index in active:
            raise SourceError("native_reference_cycle_or_depth")
        if type(index) is int and index < 0:
            return {"native_unresolved_reference": index}
        node = self.at(index)
        if isinstance(node, dict):
            return {key: self.resolve(value, (*active, index)) for key, value in node.items()}
        if isinstance(node, list):
            if node and isinstance(node[0], str):
                raise SourceError("unsupported_native_tagged_value")
            return [self.resolve(value, (*active, index)) for value in node]
        if node is None or isinstance(node, (str, bool, int, float)):
            return node
        raise SourceError("unsupported_native_value")


def parse_inventory(home_raw, search_raw, career_origin=ORIGIN):
    base = origin(career_origin)
    home, doc = document(home_raw), document(search_raw)
    counts = NativeTable(home).selected("typesenseJobCounts")
    if not isinstance(counts, dict) or "count" not in counts:
        raise SourceError("missing_independent_native_total")
    total = NativeTable(home).at(counts["count"])
    table = NativeTable(doc)
    refs = table.selected("ssrJobLinks-")
    if type(total) is not int or total < 0 or not isinstance(refs, list):
        raise SourceError("invalid_native_total_or_ssr_links")
    rows, seen = [], set()
    for reference in refs:
        row = table.resolve(reference)
        if not isinstance(row, dict) or set(row) != {"url", "title"} or not isinstance(row["title"], str) or not row["title"].strip():
            raise SourceError("malformed_complete_native_ssr_row")
        url, identity, uuid, opaque = job_uri(row["url"])
        if identity in seen:
            raise SourceError("duplicate_native_jobshop_identity")
        seen.add(identity)
        rows.append({"id": identity, "url": url, "title": row["title"], "native_offer_uuid": uuid,
                     "native_offer_reference": opaque, "original_published_at": None})
    anchors = {}
    for link in doc.xpath('//a[@href]'):
        href = link.get("href")
        if href.startswith(base + "/jobs/") or href.startswith(base + "/offer-redirect/"):
            _, identity, _, _ = job_uri(href)
            if identity in anchors:
                raise SourceError("duplicate_native_job_anchor")
            anchors[identity] = text(link)
    if len(rows) != total or len(anchors) != total or any(anchors.get(row["id"]) != " ".join(row["title"].split()) for row in rows):
        raise SourceError("native_ssr_dom_and_independent_total_differ")
    return {"status": "ok", "source": "jobshop", "kind": "jobshop_native_inventory", "career_origin": base,
            "requested_url": base + "/search", "listings": rows, "returned_count": len(rows),
            "source_result_count": total, "native_array_untruncated": True,
            "pagination": {"next_url": None, "native_ssr_count": len(refs), "native_anchor_count": len(anchors), "independent_board_total": total},
            "coverage_complete": False, "full_posting_reviewed": False, "limits": LIMITS}


def parse_detail(raw, requested_url, final_url):
    _, identity, requested_uuid, opaque = job_uri(requested_url)
    _, _, final_uuid, final_opaque = job_uri(final_url)
    if not final_uuid or requested_uuid and requested_uuid != final_uuid or opaque and final_opaque != opaque:
        raise SourceError("native_redirect_posting_identity_changed")
    doc = document(raw)
    table = NativeTable(doc)
    fields = table.selected("jobData-")
    if not isinstance(fields, dict):
        raise SourceError("missing_native_job_fields")
    native = {key: table.resolve(value) for key, value in fields.items() if key in SAFE_FIELDS}
    if native.get("offer_uuid") != final_uuid:
        raise SourceError("native_cms_uuid_mismatch")
    schemas = []
    for node in doc.xpath('//script[@type="application/ld+json"]'):
        value = load_json(node.text or "")
        schemas += [entry for entry in value.get("@graph", []) if isinstance(entry, dict) and entry.get("@type") == "JobPosting"] if isinstance(value, dict) else []
    if len(schemas) != 1:
        raise SourceError("missing_unique_native_job_schema")
    schema = schemas[0]
    headings = doc.xpath('//main//h1')
    primary = doc.xpath('//main//section[contains(concat(" ",normalize-space(@class)," ")," job-data-section ")]')
    mains = doc.xpath('//main[contains(concat(" ",normalize-space(@class)," ")," main-container ")]')
    if (len(headings) != 1 or len(primary) != 1 or len(mains) != 1 or not text(primary[0])
            or not isinstance(native.get("title"), str)
            or text(headings[0]) != " ".join(native["title"].split())
            or " ".join(str(schema.get("title") or "").split()) != " ".join(native["title"].split())
            or (schema.get("identifier") or {}).get("value") != final_uuid):
        raise SourceError("missing_complete_primary_cms_or_title_identity")
    sections = []
    for section in mains[0].xpath('.//section[not(ancestor::section)]'):
        sections.append({"source_class": section.get("class"), "html": markup(sanitize(section)), "text": text(section),
                         "visible_or_requirement_verified": False})
    main = sanitize(mains[0])
    form_text = [" ".join(form.text_content().split()) for form in mains[0].xpath('.//form')]
    return {"status": "ok", "source": "jobshop", "kind": "jobshop_native_detail", "career_origin": ORIGIN,
            "id": identity, "url": requested_url, "native_final_url": final_url, "title": native["title"],
            "native_offer_uuid": final_uuid, "native_offer_reference": opaque,
            "description": text(primary[0]), "description_html": markup(sanitize(primary[0])),
            "body_representation": "native_jobshop_full_primary_cms_html", "source_body_untruncated": True,
            "native_full_main_html_without_forms_scripts_controls": markup(main), "native_full_main_text": text(main),
            "native_cms_sections": sections, "native_application_form_text_data_only": form_text,
            "native_job_fields": native, "native_job_posting": schema,
            "source_schema_date_posted": schema.get("datePosted"), "native_schema_start_date": schema.get("jobStartDate"),
            "native_schema_valid_through": schema.get("validThrough"), "original_published_at": None,
            "hydration_credentials_exported_or_used": False, "source_scripts_assets_or_application_requested": False,
            "visible_description": None, "full_posting_reviewed": False, "coverage_complete": False, "limits": LIMITS}


def public_request(url, **kwargs):
    return request(url, **kwargs, timeout=10, redirect_metadata=True, agent="job-market-mcp/0.4.13")


def read(*, career_origin=None, job_url=None, transport=public_request):
    if (career_origin is None) == (job_url is None):
        raise SourceError("one_explicit_inventory_or_job_scope_required")
    if career_origin is not None:
        origin(career_origin)
    else:
        job_uri(job_url)
    policies, provenance = {}, []
    def step(url):
        parsed = urlsplit(url)
        base = parsed.scheme + "://" + parsed.netloc
        if base not in {ORIGIN, VENDOR}:
            raise SourceError("unverified_advertised_origin")
        if base not in policies:
            policies[base] = robot_policy(base, transport=transport)
        rules, _ = policies[base]
        if rules is not None and not rules.can_fetch("job-market-mcp", url):
            raise SourceError("robots_denied")
        response = transport(url, accept="text/html")
        provenance.append({"url": url, "method": "GET", "http_status": response.get("http_status", 200),
                           "bytes": len(response["body"]), "sha256": hashlib.sha256(response["body"]).hexdigest(),
                           "requested_at": response.get("requested_at"), "observed_at": response.get("observed_at")})
        return response
    if career_origin is not None:
        home, page = step(ORIGIN + "/"), step(ORIGIN + "/search")
        if home.get("http_status", 200) != 200 or page.get("http_status", 200) != 200:
            raise SourceError("native_inventory_redirect_requires_requalification")
        if any("text/html" not in (r.get("content_type") or "").lower() for r in [home, page]):
            raise SourceError("unexpected_native_html_content_type")
        result = parse_inventory(home["body"], page["body"], career_origin)
    else:
        current, seen, external_reference = job_url, set(), None
        _, _, _, opaque = job_uri(job_url)
        for _ in range(3):
            if current in seen:
                raise SourceError("native_redirect_cycle")
            seen.add(current)
            response = step(current)
            if response.get("http_status", 200) == 200:
                if "text/html" not in (response.get("content_type") or "").lower():
                    raise SourceError("unexpected_native_html_content_type")
                result = parse_detail(response["body"], job_url, current)
                if external_reference is not None and str(result["native_job_fields"].get("external_id")) != external_reference:
                    raise SourceError("native_vendor_external_reference_changed")
                break
            location = response.get("location")
            if not isinstance(location, str) or len(location) > 4096:
                raise SourceError("missing_native_redirect_location")
            parsed = urlsplit(location)
            query = parse_qs(parsed.query, keep_blank_values=True)
            if parsed.scheme + "://" + parsed.netloc == VENDOR:
                if (urlsplit(current).path != "/offer-redirect/" or parsed.path != "/api/offer/v1/offer/offer-redirect"
                        or parsed.fragment or set(query) != {"externalId", "jobshopVanity", "offerApiId", "showApplicationForm"}
                        or query["jobshopVanity"] != ["fraport-professionals"] or query["offerApiId"] != [opaque]
                        or query["showApplicationForm"] != ["false"] or len(query["externalId"]) != 1
                        or not re.fullmatch(r"[1-9][0-9]*", query["externalId"][0])):
                    raise SourceError("unverified_native_vendor_redirect")
                external_reference = query["externalId"][0]
            else:
                job_uri(location)
            current = location
        else:
            raise SourceError("native_redirect_ceiling")
    return {**result, "provenance": provenance, "policies": {base: policy for base, (_, policy) in policies.items()}}


def capabilities():
    return {"status": "ok", "source": "jobshop", "operations": ["inventory", "detail"],
            "independently_verified_origins": [ORIGIN], "inventory": "Whole SSR link table plus native anchor/title and independent board-count reconciliation; no search API/key.",
            "body": "Complete primary CMS job-data section, separate sanitized full main/context sections/schema and form labels; no schema-only description assumption.",
            "max_complete_response_bytes": MAX_BYTES, "native_redirect_ceiling": 2,
            "acquisition_filters": [], "coverage_complete": False, "limits": LIMITS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--career-origin")
    parser.add_argument("--job-url")
    args = parser.parse_args()
    try:
        result = capabilities() if args.capabilities else read(career_origin=args.career_origin, job_url=args.job_url)
        print(json.dumps(result, ensure_ascii=False))
    except (SourceError, ValueError, TypeError) as error:
        print(json.dumps({"status": "source_limited", "source": "jobshop", "error": getattr(error, "code", "invalid_native_jobshop_data"),
                          "http_status": getattr(error, "http_status", None), "retry_after": getattr(error, "retry_after", None),
                          "returned_count": None, "source_result_count": None, "coverage_complete": False, "limits": LIMITS}))


if __name__ == "__main__":
    main()
