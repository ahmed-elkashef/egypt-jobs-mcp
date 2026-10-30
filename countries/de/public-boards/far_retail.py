"""Original anonymous FAR public inventory and complete textual job sections.

Only fixed first-party public read endpoints are used. The source's application
links remain data; no application, preview or hydration credential is used.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, build_opener

from lxml import etree, html

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from shared.public_http import MAX_BYTES, NoRedirect, load_json, request, robot_policy  # noqa: E402
from shared.public_http import SourceError as PublicError  # noqa: E402

SOURCE = "far_retail"
ORIGIN = "https://frankfurt-airport-retail.de"
LIST_PATH = "/far/de/karriere-start/jobs"
BOARD = ORIGIN + LIST_PATH
COMPANY = "Frankfurt Airport Retail GmbH & Co. KG"
LOCALE = "de-DE"
READ_PATHS = {"/api/jobsearch", "/api/jobdetails", "/api/contentful"}
LIMITS = [
    "Only the qualified Frankfurt Airport Retail employer board is supported; this is not a national market or a census of Heinemann employers.",
    "The whole native metadata array must reconcile @odata.count and unique scoped IDs. No role, keyword, hours or department selector is exposed; the fixed native wildcard means the entire company.",
    "The native client uses POST for these public reads. Only jobsearch, non-preview jobdetails and contentful benefits/texts are permitted. No account, candidate, key, cookie, application, image or source-script request is made.",
    "Primary introduction/tasks/profile, benefits, company and recruiter sections remain distinct, with raw and safe variants. Employer context is not automatically a mandatory job requirement.",
    "Monthly hours, source employment labels, dates, country and city remain raw. No precise student contract, weekly hours, original publication, fit, worker-country eligibility or historical-week completion is inferred.",
    "A current complete native array is not atomic historical supply. Missing, capped, changed, denied or malformed responses have unknown counts; no fake empty market or partial body is emitted.",
    "Textual source completeness is not a visual verification of decorative images or of the external application portal.",
]


class FarError(ValueError):
    def __init__(self, code, *, http_status=None, retry_after=None):
        super().__init__(code)
        self.http_status, self.retry_after = http_status, retry_after


def checked_url(url, operation):
    if (not isinstance(url, str) or len(url) > 2048 or url != url.strip()
            or any(ord(c) < 32 for c in url)):
        raise FarError("invalid_far_public_uri")
    parsed = urlsplit(url)
    if (parsed.scheme + "://" + parsed.netloc != ORIGIN or parsed.query or parsed.fragment
            or unquote(parsed.path) != parsed.path):
        raise FarError("unverified_far_public_scope")
    if operation == "inventory":
        if url != BOARD:
            raise FarError("unverified_far_inventory")
    elif operation == "detail":
        if not re.fullmatch(r"/far/de/job/[1-9][0-9]{0,9}-de_DE", parsed.path):
            raise FarError("unverified_far_public_posting")
    else:
        raise FarError("unsupported_far_operation")
    return url


def job_uri(native):
    if not isinstance(native, str) or not re.fullmatch(r"[1-9][0-9]{0,9}-de_DE", native):
        raise FarError("invalid_far_native_job_id")
    return ORIGIN + "/far/de/job/" + native


def native_id(url):
    checked_url(url, "detail")
    return SOURCE + "::" + url.rsplit("/", 1)[1]


def native_transport(url, *, payload=None, accept="application/json", bound=MAX_BYTES, timeout=15):
    if payload is None:
        return request(url, accept=accept, bound=bound, timeout=timeout)
    if url not in {ORIGIN + path for path in READ_PATHS}:
        raise FarError("unverified_far_read_endpoint")
    started = datetime.now(timezone.utc).isoformat()
    req = Request(url, data=json.dumps(payload).encode(), method="POST",
                  headers={"User-Agent": "job-market-mcp/0.4.16", "Accept": "application/json",
                           "Content-Type": "application/json"})
    try:
        with build_opener(NoRedirect()).open(req, timeout=timeout) as response:
            raw = response.read(bound + 1)
            if response.status != 200 or len(raw) > bound:
                raise FarError("incomplete_far_response", http_status=response.status)
            return {"body": raw, "content_type": response.headers.get("Content-Type"),
                    "requested_at": started, "observed_at": datetime.now(timezone.utc).isoformat()}
    except HTTPError as error:
        raise FarError("far_native_http_error", http_status=error.code,
                       retry_after=error.headers.get("Retry-After")) from None
    except FarError:
        raise
    except Exception:
        raise FarError("far_native_transport_failed") from None


def reject_credentials(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in {"bearertoken", "access_token", "refresh_token", "password", "private_key", "apikey", "api_key"} and item:
                raise FarError("unexpected_source_credential_in_public_response")
            reject_credentials(item)
    elif isinstance(value, list):
        for item in value:
            reject_credentials(item)


def api(path, payload, rules, transport):
    if path not in READ_PATHS:
        raise FarError("unverified_far_read_endpoint")
    url = ORIGIN + path
    if rules is not None and not rules.can_fetch("job-market-mcp", url):
        raise FarError("robots_denied")
    response = transport(url, payload=payload, accept="application/json", timeout=15)
    if (response.get("http_status", 200) != 200
            or "json" not in (response.get("content_type") or "").lower()):
        raise FarError("unexpected_far_native_content")
    raw = response["body"]
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise FarError("incomplete_far_native_response")
    data = load_json(raw)
    reject_credentials(data)
    return data, {"requested_url": url, "method": "POST", "read_asset": payload.get("asset"),
                  "http_status": 200, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                  "requested_at": response.get("requested_at"), "observed_at": response.get("observed_at")}


def public_section(value):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise FarError("invalid_far_public_text")
    try:
        node = html.fragment_fromstring(value or " ", create_parent="section")
    except (TypeError, ValueError, etree.ParserError):
        raise FarError("invalid_far_public_html") from None
    for child in node.xpath(".//script|.//style|.//iframe|.//object|.//embed|.//form|.//input"):
        child.drop_tree()
    for child in node.iter():
        for name in list(child.attrib):
            if (name.lower().startswith(("on", "data-"))
                    or name.lower() in {"href", "src"} and re.match(r"\s*(?:javascript|vbscript|data):", child.attrib[name], re.I)):
                del child.attrib[name]
        if child.tag in {"p", "li", "div", "br", "h1", "h2", "h3", "section", "ul", "ol", "tr", "td"}:
            child.text, child.tail = " " + (child.text or ""), " " + (child.tail or "")
    return {"text": " ".join(node.text_content().split()),
            "html": html.tostring(node, encoding="unicode", method="html")}


def inventory(data, url):
    checked_url(url, "inventory")
    rows = data.get("value") if isinstance(data, dict) else None
    total = data.get("@odata.count") if isinstance(data, dict) else None
    if type(total) is not int or not 0 <= total <= 1000000 or not isinstance(rows, list) or len(rows) != total:
        raise FarError("far_native_whole_array_count_does_not_reconcile")
    listings, seen = [], set()
    for row in rows:
        if (not isinstance(row, dict) or row.get("company") != COMPANY
                or any(not isinstance(row.get(key), str) or not row[key].strip()
                       for key in ["title", "city", "country"])):
            raise FarError("missing_or_unscoped_far_metadata")
        uri = job_uri(row.get("jobId"))
        identity = native_id(uri)
        if identity in seen:
            raise FarError("duplicate_far_native_job")
        seen.add(identity)
        listings.append({
            "id": identity, "native_job_id": row["jobId"], "url": uri, "title": row["title"],
            "native_job_fields": row, "native_model_label": None, "original_source_date": None,
            "source_body_complete": False, "applicant_fit_assessed": False,
        })
    return {
        "source": SOURCE, "status": "ok", "kind": "german_public_board_page", "source_url": url,
        "listings": listings, "returned_count": len(rows), "source_result_count": total,
        "native_array_untruncated": True, "native_company": COMPANY,
        "native_inventory_request": {"locale": LOCALE, "searchTerm": "*", "facets": [{"company": [COMPANY]}], "operation": "search"},
        "native_facets": data.get("@search.facets"), "native_api_metadata": {k: v for k, v in data.items() if k != "value"},
        "pagination": {"next_url": None, "native_total": total, "native_array_count": len(rows)},
        "hydration_credentials_exported_or_used": False, "source_scripts_images_or_application_requested": False,
        "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS,
    }


def cms_arguments(job):
    if (not isinstance(job, dict) or job.get("company") != COMPANY
            or not isinstance(job.get("location"), str) or not job["location"]):
        raise FarError("missing_far_company_or_location")
    ids = []
    for number in range(1, 6):
        value = job.get("custRecBenefits" + str(number))
        if value is None:
            continue
        if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", value):
            raise FarError("invalid_far_benefit_identifier")
        ids.append("JOB-AD-BENEFIT-" + value)
    raw = job.get("recruiter")
    if raw is not None and not isinstance(raw, dict):
        raise FarError("invalid_far_recruiter_object")
    raw = raw or {}
    recruiter = {"name": raw.get("name") or "", "phone": raw.get("phone") or "",
                 "email": job.get("custRecDetails6") or raw.get("email") or ""}
    if any(not isinstance(value, str) for value in recruiter.values()):
        raise FarError("invalid_far_public_recruiter_field")
    return (
        {"ids": ",".join(ids), "locale": LOCALE, "asset": "benefits"},
        {"company": COMPANY, "location": job["location"], "recruiter": recruiter, "locale": LOCALE, "asset": "texts"},
    )


def detail(job, benefits, texts, url):
    identity = native_id(url)
    native = url.rsplit("/", 1)[1]
    if (not isinstance(job, dict) or job.get("jobId") != native or job.get("company") != COMPANY
            or not isinstance(job.get("title"), str) or not job["title"].strip()
            or any(key not in job or not isinstance(job[key], str) for key in ["introduction", "tasks", "profile"])):
        raise FarError("missing_or_conflicting_far_primary_body")
    cms_arguments(job)
    if (not isinstance(benefits, list) or any(
            not isinstance(row, dict) or not isinstance(row.get("headline"), str) or not row["headline"].strip()
            or row.get("imageURL") is not None and (not isinstance(row["imageURL"], str)
                                                   or not row["imageURL"].startswith("https://"))
            for row in benefits)):
        raise FarError("invalid_far_full_benefit_sections")
    if (not isinstance(texts, dict) or set(texts) != {"recruiter", "companyText"}
            or any(not isinstance(v, str) for v in texts.values())):
        raise FarError("missing_far_company_or_recruiter_text")
    sections = {key: public_section(job[key]) for key in ["introduction", "tasks", "profile"]}
    primary = "\n\n".join(sections[key]["text"] for key in ["introduction", "tasks", "profile"])
    primary_html = "".join(sections[key]["html"] for key in ["introduction", "tasks", "profile"])
    if len(primary.strip()) < 100:
        raise FarError("missing_complete_far_primary_description")
    context = {key: public_section(value) for key, value in texts.items()}
    full = "\n\n".join([primary, *[row["headline"] for row in benefits],
                        context["companyText"]["text"], context["recruiter"]["text"]])
    return {
        "source": SOURCE, "status": "ok", "kind": "german_public_board_detail",
        "id": identity, "native_job_id": native, "url": url, "source_url": url, "title": job["title"],
        "description": primary, "description_html": primary_html,
        "native_primary_sections": sections, "native_job_fields": job,
        "native_benefits": benefits, "native_context_sections": context, "native_context_raw": texts,
        "native_full_public_text": full, "native_description_characters": len(primary),
        "body_representation": "native_far_complete_public_api_sections",
        "source_body_untruncated": True, "full_posting_reviewed": False, "original_published_at": None,
        "hydration_credentials_exported_or_used": False, "source_scripts_images_or_application_requested": False,
        "native_public_cms_sections_requested": True,
        "application_links_data_only": {key: job.get(key) for key in ["link", "quickApplyLink"]},
        "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS,
    }


def read(operation, url, *, transport=native_transport):
    checked_url(url, operation)
    try:
        rules, policy = robot_policy(ORIGIN, transport=transport)
        if rules is not None and not rules.can_fetch("job-market-mcp", url):
            raise FarError("robots_denied")
        if operation == "inventory":
            payload = {"locale": LOCALE, "searchTerm": "*", "facets": [{"company": [COMPANY]}], "operation": "search"}
            data, provenance = api("/api/jobsearch", payload, rules, transport)
            result = inventory(data, url)
            provenance = [provenance]
        else:
            job, core = api("/api/jobdetails", {"jobId": url.rsplit("/", 1)[1], "preview": False}, rules, transport)
            if not isinstance(job, dict) or job.get("jobId") != url.rsplit("/", 1)[1]:
                raise FarError("far_detail_identity_changed")
            benefit_args, text_args = cms_arguments(job)
            benefits, benefits_provenance = api("/api/contentful", benefit_args, rules, transport)
            texts, texts_provenance = api("/api/contentful", text_args, rules, transport)
            result = detail(job, benefits, texts, url)
            provenance = [core, benefits_provenance, texts_provenance]
        return {**result, "policy": policy, "native_response_provenance": provenance,
                "observed_at": datetime.now(timezone.utc).isoformat()}
    except PublicError as error:
        raise FarError(error.code, http_status=error.http_status, retry_after=error.retry_after) from None
