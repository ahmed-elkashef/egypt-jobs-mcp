"""Original read-only d.vinci public job-publication JSON reader.

The documented singular /jobPublication routes are anonymous publishing
interfaces. Account REST, application forms and application APIs are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import html as escape_html
import json
import math
import re
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from lxml import etree, html

AGENT = "job-market-mcp/0.4.11"
MAX_BYTES = 8 * 1024 * 1024
MAX_SAFE_ID = 9007199254740991
DOCUMENTATION = "https://static.dvinci-easy.com/files/d.vinci%20job-publication-api.html"
CUSTOM_ORIGINS = {
    "https://dein-weg-zu.dvinci.de": "https://karriere.dvinci.de/jobs/",
    "https://dtsgroup-career.dvinci.de": "https://www.dts.de/de/karriere",
}
RAW_BODY_FIELDS = ("introduction", "tasks", "profile", "weOffer", "closingText")
OPENING_FIELDS = ("id", "name", "type", "categories", "reference", "location", "locations",
                  "department", "targetGroups", "workingTimes", "salaryRange", "contractPeriod",
                  "earliestEntryDate", "orgUnit", "createdDate", "company", "salary")
LIMITS = [
    "An independently identified employer portal is not an employer or country census.",
    "The documented unfiltered DEFAULT list supplies the current active regular-publication array, not historical weekly coverage or unsolicited applications.",
    "No independent server result count or revision token is supplied; returned array length is not a separately reported total.",
    "startDate/endDate are optional publication availability clocks; jobOpening.createdDate is requisition creation, not verified original publication.",
    "earliestEntryDate is a separate raw job-entry field. Target-group, working-time and contract labels are employer-configurable, not universal eligibility enums.",
    "Native location and remote wording require individual review; they do not establish compatible student hours or Germany-based remote permission.",
    "Rendered ad sections, raw sections and company description variants are preserved separately. Unused company text is not automatically an advertised requirement.",
    "No account REST, authentication, application form/API, contact or subscription operation is supported. Returned application links are data only.",
]


class SourceError(ValueError):
    def __init__(self, code, *, http_status=None, retry_after=None):
        super().__init__(code)
        self.code, self.http_status, self.retry_after = code, http_status, retry_after


def portal(value):
    if not isinstance(value, str) or len(value) > 2048 or value != value.strip() or any(ord(c) < 32 for c in value):
        raise SourceError("invalid_verified_publication_portal")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise SourceError("invalid_verified_publication_portal") from None
    vendor = re.fullmatch(r"([a-z0-9]+(?:-[a-z0-9]+)*)\.dvinci-hr\.com", parsed.netloc)
    base = "https://" + parsed.netloc
    path = parsed.path.rstrip("/")
    if (parsed.scheme != "https" or parsed.query or parsed.fragment
            or not (base in CUSTOM_ORIGINS or vendor and vendor[1] not in {"api", "www", "static", "support", "admin"})
            or path and not re.fullmatch(r"/portal/[A-Za-z0-9_-]+", path)
            or parsed.path not in {path, path + "/"}):
        raise SourceError("unverified_publication_portal")
    return base + path


def publication_id(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise SourceError("invalid_exact_publication_id")
    if not re.fullmatch(r"[1-9][0-9]{0,15}", str(value)) or int(value) > MAX_SAFE_ID:
        raise SourceError("invalid_exact_publication_id")
    return str(value)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, *, accept, bound=MAX_BYTES, opener=None):
    started = datetime.now(timezone.utc).isoformat()
    try:
        with (opener or build_opener(NoRedirect())).open(
                Request(url, headers={"User-Agent": AGENT, "Accept": accept}), timeout=15) as response:
            raw = response.read(bound + 1)
            if response.status != 200:
                raise SourceError("unexpected_http_status", http_status=response.status)
            if len(raw) > bound:
                raise SourceError("complete_response_exceeds_bound")
            return {"body": raw, "content_type": response.headers.get("Content-Type"),
                    "requested_at": started, "observed_at": datetime.now(timezone.utc).isoformat()}
    except HTTPError as error:
        raise SourceError("source_http_error", http_status=error.code,
                          retry_after=error.headers.get("Retry-After")) from None
    except SourceError:
        raise
    except Exception:
        raise SourceError("source_transport_failed") from None


def robot_policy(base, *, transport=request):
    parsed = urlsplit(base)
    origin = parsed.scheme + "://" + parsed.netloc
    try:
        response = transport(origin + "/robots.txt", accept="text/plain", bound=256 * 1024)
    except SourceError as error:
        if error.http_status in {404, 410}:
            return None, {"robots_status": error.http_status, "basis": "RFC9309 robots resource unavailable."}
        raise SourceError("robots_unavailable_or_denied", http_status=error.http_status,
                          retry_after=error.retry_after) from None
    try:
        text = response["body"].decode("utf-8-sig")
    except UnicodeDecodeError:
        raise SourceError("invalid_robots_response") from None
    if "<html" in text.lower() or "<!doctype" in text.lower():
        raise SourceError("invalid_robots_response")
    rules = RobotFileParser()
    rules.parse(text.splitlines())
    return rules, {"robots_status": 200}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SourceError("duplicate_json_key")
        result[key] = value
    return result


def _finite(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite_json_number")
    return result


def load_json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_object, parse_float=_finite,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeDecodeError):
        raise SourceError("invalid_native_json") from None


def body_text(markup):
    if not isinstance(markup, str):
        raise SourceError("invalid_native_description_html")
    if not markup.strip():
        return ""
    try:
        document = html.fragment_fromstring(markup, create_parent="div")
    except (etree.ParserError, ValueError, TypeError):
        raise SourceError("invalid_native_description_html") from None
    for node in document.xpath(".//script|.//style|.//iframe|.//object|.//embed"):
        node.drop_tree()
    for node in document.iter():
        if node.tag in {"p", "li", "div", "br", "h1", "h2", "h3", "h4"}:
            node.tail = " " + (node.tail or "")
    return " ".join(document.text_content().split())


def description(row):
    rendered = row.get("renderedContent")
    if rendered is not None and not isinstance(rendered, dict):
        raise SourceError("invalid_native_rendered_content")
    chunks = []
    for name, section in (rendered or {}).items():
        if not isinstance(name, str) or not isinstance(section, dict):
            raise SourceError("invalid_native_rendered_section")
        for key in ("headline", "body"):
            value = section.get(key)
            if value is not None and not isinstance(value, str):
                raise SourceError("invalid_native_rendered_section")
        if section.get("headline"):
            chunks.append("<h2>" + escape_html.escape(section["headline"]) + "</h2>")
        if section.get("body"):
            chunks.append(section["body"])
    raw_sections = {name: row.get(name) for name in RAW_BODY_FIELDS}
    for value in raw_sections.values():
        if value is not None and not isinstance(value, str):
            raise SourceError("invalid_native_raw_section")
    rendered_text = body_text("\n".join(chunks))
    extras = [value for value in raw_sections.values()
              if value and body_text(value) and body_text(value) not in rendered_text]
    complete_html = "\n".join(chunks + extras)
    text = body_text(complete_html)
    if not text:
        raise SourceError("missing_complete_native_description")
    opening = row["jobOpening"]
    company = opening.get("company")
    if company is not None and not isinstance(company, dict):
        raise SourceError("invalid_native_company")
    company_sections = {name: company.get(name) for i in range(1, 11)
                        if company is not None and (name := "description" + str(i)) in company}
    for value in company_sections.values():
        if value is not None and not isinstance(value, str):
            raise SourceError("invalid_native_company_description")
    return {"description": text, "description_html": complete_html,
            "body_representation": "native_dvinci_publication_json_content",
            "source_body_untruncated": True, "visible_description": None,
            "native_body_fields": {"renderedContent": rendered, "raw_sections": raw_sections,
                                   "company_description_sections": company_sections},
            "raw_section_extras_preserved": len(extras),
            "body_variants_require_reconciliation": True, "full_posting_reviewed": False}


def normalize_row(row, base, *, include_body):
    if not isinstance(row, dict) or not isinstance(row.get("id"), int):
        raise SourceError("invalid_native_publication")
    identity = publication_id(row["id"])
    title, opening = row.get("position"), row.get("jobOpening")
    if not isinstance(title, str) or not title.strip() or not isinstance(opening, dict):
        raise SourceError("missing_native_publication_identity")
    opening_id = publication_id(opening.get("id"))
    url = row.get("jobPublicationURL")
    if url is not None:
        if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 32 for c in url):
            raise SourceError("invalid_published_job_url")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise SourceError("invalid_published_job_url")
    result = {"id": base + "::" + identity, "native_publication_id": identity,
              "native_job_opening_id": opening_id, "url": url, "title": title,
              "source_language": row.get("language"), "source_subtitle": row.get("subtitle"),
              "source_page_description": row.get("pageDescription"),
              "application_url": row.get("applicationFormURL"),
              "native_job_opening": {k: v for k, v in opening.items() if k in OPENING_FIELDS},
              "native_benefits": row.get("benefits"),
              "source_publication_available_since": row.get("startDate"),
              "source_publication_available_until": row.get("endDate"),
              "native_job_opening_created_at": opening.get("createdDate"),
              "native_earliest_entry_date": opening.get("earliestEntryDate"),
              "original_published_at": None, "full_posting_reviewed": False}
    if include_body:
        result.update(description(row))
    else:
        result.update(description=None, description_html=None, source_body_untruncated=False,
                      body_representation=None, visible_description=None)
    return result


def parse_inventory(raw, base, *, include_body=False):
    rows = load_json(raw)
    if not isinstance(rows, list):
        raise SourceError("invalid_native_publication_array")
    jobs, identities = [], set()
    for row in rows:
        job = normalize_row(row, base, include_body=include_body)
        if job["id"] in identities:
            raise SourceError("duplicate_native_publication_id")
        identities.add(job["id"])
        jobs.append(job)
    return {"status": "ok", "source": "dvinci", "kind": "dvinci_native_inventory",
            "portal_url": base, "returned_count": len(jobs), "source_result_count": None,
            "native_array_count": len(jobs), "native_array_untruncated": True,
            "native_scope": "Current active DEFAULT regular publications for one portal; no role/geography/language filter.",
            "body_included": include_body, "listings": jobs,
            "pagination": {"next_url": None, "contract": "Documented complete array without pagination."},
            "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS}


def read(portal_url, *, job_id=None, include_body=False, transport=request):
    base = portal(portal_url)
    if not isinstance(include_body, bool) or job_id is not None and include_body:
        raise SourceError("invalid_read_arguments")
    exact_id = publication_id(job_id) if job_id is not None else None
    rules, policy = robot_policy(base, transport=transport)
    path = "/jobPublication/show/" + exact_id + ".json" if exact_id else "/jobPublication/list.json" + ("" if include_body else "?fields=small")
    url = base + path
    if rules is not None and not rules.can_fetch(AGENT, url):
        raise SourceError("robots_denied")
    response = transport(url, accept="application/json")
    if "application/json" not in (response.get("content_type") or "").lower():
        raise SourceError("unexpected_native_response_content_type")
    raw = response["body"]
    if exact_id is None:
        result = parse_inventory(raw, base, include_body=include_body)
    else:
        row = load_json(raw)
        job = normalize_row(row, base, include_body=True)
        if job["native_publication_id"] != exact_id:
            raise SourceError("native_detail_publication_identity_mismatch")
        result = {"status": "ok", "source": "dvinci", "kind": "dvinci_native_detail", "portal_url": base,
                  **job, "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS}
    result.update(policy=policy, provenance=[{"url": url, "method": "GET", "bytes": len(raw),
                  "sha256": hashlib.sha256(raw).hexdigest(), "requested_at": response.get("requested_at"),
                  "observed_at": response.get("observed_at")}])
    return result


def capabilities():
    return {"status": "ok", "source": "dvinci", "operations": ["inventory", "detail"],
            "seed_required": True, "documentation": DOCUMENTATION,
            "vendor_portal": "Exact identified HTTPS <tenant>.dvinci-hr.com origin, optionally /portal/<name>.",
            "verified_custom_origins": CUSTOM_ORIGINS, "max_complete_response_bytes": MAX_BYTES,
            "inventory_default": "Documented fields=small preserves every regular-publication metadata row. Optional include_body reads full list without fields parameter.",
            "detail": "Documented singular GET /jobPublication/show/{publicationId}.json, full native rendered/raw/company sections.",
            "acquisition_filters": [], "coverage_complete": False, "limits": LIMITS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--portal-url")
    parser.add_argument("--job-id")
    parser.add_argument("--include-body", action="store_true")
    args = parser.parse_args()
    try:
        result = capabilities() if args.capabilities else read(args.portal_url, job_id=args.job_id, include_body=args.include_body)
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        result = {"status": "source_limited", "source": "dvinci", "returned_count": None,
                  "source_result_count": None, "error": error.code if isinstance(error, SourceError) else "invalid_native_source_response",
                  "http_status": getattr(error, "http_status", None), "retry_after": getattr(error, "retry_after", None),
                  "coverage_complete": False, "reviewed_by_model": False}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
