"""Original anonymous Workday public CXS jobs reads; no account/application API.

Protocol verified against the published candidate-experience-jobs app. Board
URLs must be supplied from an identified employer's official careers authority.
This is a seeded employer reader, never an employer or country census.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from lxml import html

AGENT = "job-market-mcp/0.4.9"
MAX_BYTES = 8 * 1024 * 1024
MAX_ROBOTS_BYTES = 256 * 1024
HOST = re.compile(r"([a-z0-9]+(?:-[a-z0-9]+)*)\.(wd[1-9][0-9]{0,2})\.myworkdayjobs\.com\Z")
SITE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
LOCALE = re.compile(r"[a-z]{2}(?:-[A-Z]{2})?\Z")
LIMITS = [
    "An explicitly identified employer board is not an employer, Germany or Egypt census.",
    "Moving current pages do not establish complete historical or frozen weekly coverage.",
    "Offsets are requested native offsets, not an independent server echo; compare IDs and totals across pages.",
    "Native later pages can return total=0 with jobs; carry the exact first-page total as continuation state. Out-of-range offsets can reset to page one, so never probe past the observed total or infer an empty terminal.",
    "Relative postedOn and native startDate are preserved without inventing an original publication instant or employment start.",
    "A remote label, primary country or full-time label alone does not prove worker eligibility, hours or student contract.",
    "Full source descriptions require individual fit and required-document review; no application, account, contact or subscription action exists.",
]
CARD_FIELDS = {"title", "externalPath", "locationsText", "postedOn", "remoteType", "bulletFields"}
JOB_FIELDS = {
    "id", "title", "jobDescription", "location", "additionalLocations", "postedOn", "startDate",
    "endDate", "timeType", "jobReqId", "jobPostingId", "jobPostingSiteId", "country", "posted",
    "jobRequisitionLocation", "remoteType", "externalUrl", "jobPostingEndDate", "timeLeftToApply",
    "jobPostingEndDateAsText",
}


class SourceError(ValueError):
    def __init__(self, code, *, http_status=None, retry_after=None):
        super().__init__(code)
        self.code, self.http_status, self.retry_after = code, http_status, retry_after


def integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise SourceError("invalid_native_pagination")
    return value


def board(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise SourceError("invalid_explicit_board_url")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise SourceError("invalid_explicit_board_url") from None
    if (parsed.scheme != "https" or not HOST.fullmatch(parsed.netloc) or parsed.query
            or parsed.fragment or not parsed.path.startswith("/")):
        raise SourceError("invalid_explicit_board_url")
    parts = parsed.path.removesuffix("/").split("/")[1:]
    if len(parts) == 2 and LOCALE.fullmatch(parts[0]):
        locale, site = parts
    elif len(parts) == 1:
        locale, site = None, parts[0]
    else:
        raise SourceError("invalid_explicit_board_url")
    if not SITE.fullmatch(site):
        raise SourceError("invalid_explicit_board_url")
    origin = "https://" + parsed.netloc
    return {"origin": origin, "tenant": HOST.fullmatch(parsed.netloc)[1], "site": site,
            "locale": locale, "board_url": origin + "/" + "/".join(parts)}


def external_path(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 1800:
        raise SourceError("invalid_native_job_path")
    decoded = unquote(value)
    parts = decoded.split("/")
    if (not decoded.startswith("/job/") or len(parts) not in {3, 4}
            or any(not p or p in {".", "..", "apply", "account"} for p in parts[1:])
            or any(ord(c) < 32 or c in "\\?#" for c in decoded)
            or re.search(r"%[0-9a-fA-F]{2}", decoded)
            or re.search(r"%(?:2f|5c)", value, re.I)):
        raise SourceError("invalid_native_job_path")
    return quote(decoded, safe="/-_.~")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, *, payload=None, bound=MAX_BYTES, opener=None, accept="application/json"):
    opener = opener or build_opener(NoRedirect())
    headers = {"User-Agent": AGENT, "Accept": accept}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    try:
        with opener.open(Request(url, data=payload, headers=headers,
                                 method="POST" if payload is not None else "GET"), timeout=35) as response:
            data = response.read(bound + 1)
            if response.status != 200:
                raise SourceError("unexpected_http_status", http_status=response.status)
            if len(data) > bound:
                raise SourceError("complete_response_exceeds_bound")
            return data
    except HTTPError as error:
        raise SourceError("source_http_error", http_status=error.code,
                          retry_after=error.headers.get("Retry-After")) from None
    except SourceError:
        raise
    except Exception:
        raise SourceError("source_transport_failed") from None


def policy(origin, target, *, transport=request):
    try:
        raw = transport(origin + "/robots.txt", bound=MAX_ROBOTS_BYTES, accept="text/plain")
    except SourceError as error:
        if error.http_status in {404, 410}:
            return {"robots_status": error.http_status, "robots_allowed": True,
                    "basis": "RFC9309 robots resource unavailable, not an access denial."}
        raise SourceError("robots_unavailable_or_denied", http_status=error.http_status,
                          retry_after=error.retry_after) from None
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise SourceError("invalid_robots_response") from None
    if "<html" in text.lower() or "<!doctype" in text.lower():
        raise SourceError("invalid_robots_response")
    rules = RobotFileParser()
    rules.parse(text.splitlines())
    if not rules.can_fetch(AGENT, target):
        raise SourceError("robots_denied")
    return {"robots_status": 200, "robots_allowed": True}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SourceError("duplicate_json_key")
        result[key] = value
    return result


def payload(raw):
    try:
        data = json.loads(raw, object_pairs_hook=_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(SourceError("invalid_json_number")))
    except (ValueError, UnicodeDecodeError):
        raise SourceError("invalid_native_json") from None
    if not isinstance(data, dict) or data.get("userAuthenticated") is not False:
        raise SourceError("unexpected_public_context")
    return data


def inventory(raw, board_url, *, offset=0, limit=20, first_page_total=None):
    context = board(board_url)
    integer(offset, 0, 1_000_000)
    integer(limit, 1, 20)
    if first_page_total is not None:
        integer(first_page_total, 0, 100_000_000)
    if offset > 0 and (first_page_total is None or offset >= first_page_total):
        raise SourceError("valid_initial_native_total_required_for_offset")
    data = payload(raw)
    total = integer(data.get("total"), 0, 100_000_000)
    count_known = offset == 0 or total > 0
    if count_known and first_page_total is not None and total != first_page_total:
        raise SourceError("native_snapshot_total_changed")
    expected_total = total if offset == 0 else first_page_total
    rows = data.get("jobPostings")
    if (not isinstance(rows, list) or len(rows) > limit
            or (rows and offset + len(rows) > expected_total)
            or (not rows and offset < expected_total)):
        raise SourceError("inconsistent_native_inventory")
    jobs, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("title"), str) or not row["title"].strip():
            raise SourceError("incomplete_native_job_card")
        path = external_path(row.get("externalPath"))
        if path in seen:
            raise SourceError("duplicate_native_job_path")
        seen.add(path)
        identity = context["origin"] + "/" + context["site"] + path
        jobs.append({"source_id": identity, "external_path": path, "url": context["board_url"] + path, "title": row["title"],
                     "location_raw": row.get("locationsText"), "country": None,
                     "posted_on_raw": row.get("postedOn"), "original_published_at": None,
                     "remote_type_raw": row.get("remoteType"),
                     "native_fields": {k: v for k, v in row.items() if k in CARD_FIELDS},
                     "requires_full_description": True})
    next_offset = offset + len(rows) if offset + len(rows) < expected_total else None
    if next_offset is not None and next_offset > 1_000_000:
        raise SourceError("native_continuation_exceeds_operator_bound")
    return {"status": "ok", "source": "workday", "kind": "workday_inventory", "board_url": context["board_url"],
            "count": len(jobs), "source_result_count": total if count_known else None, "jobs": jobs,
            "native_pagination": {"offset": offset, "limit": limit, "server_offset_echo": None,
                                  "next_offset": next_offset, "reported_total_raw": total,
                                  "global_count_known_on_this_response": count_known,
                                  "first_page_total": expected_total,
                                  "initial_total_bound_reached": next_offset is None},
            "continuation": ({"board_url": context["board_url"], "offset": next_offset, "limit": limit,
                              "first_page_total": expected_total}
                             if next_offset is not None else None),
            "response_sha256": hashlib.sha256(raw).hexdigest(), "coverage_complete": False,
            "reviewed_by_model": False, "limits": LIMITS}


def detail(raw, board_url, path):
    context, path, data = board(board_url), external_path(path), payload(raw)
    info = data.get("jobPostingInfo")
    if (not isinstance(info, dict) or not isinstance(info.get("title"), str) or not info["title"].strip()
            or not isinstance(info.get("jobDescription"), str) or not info["jobDescription"].strip()
            or not isinstance(info.get("id"), str) or not info["id"]):
        raise SourceError("incomplete_native_job_description")
    if not isinstance(info.get("externalUrl"), str):
        raise SourceError("native_job_identity_mismatch")
    try:
        native_url = urlsplit(info["externalUrl"])
    except ValueError:
        raise SourceError("native_job_identity_mismatch") from None
    native_parts = native_url.path.split("/job/", 1)
    if len(native_parts) != 2:
        raise SourceError("native_job_identity_mismatch")
    returned_board = board(native_url.scheme + "://" + native_url.netloc + native_parts[0])
    if (returned_board["origin"] != context["origin"] or returned_board["site"] != context["site"]
            or native_url.query or native_url.fragment or external_path("/job/" + native_parts[1]) != path):
        raise SourceError("native_job_identity_mismatch")
    try:
        document = html.fragment_fromstring(info["jobDescription"], create_parent="div")
        for element in document.xpath(".//script|.//style|.//iframe|.//object|.//embed"):
            element.drop_tree()
        for element in document.iter():
            if element.tag in {"br", "p", "li", "div", "h1", "h2", "h3", "h4"}:
                element.tail = " " + (element.tail or "")
        text = " ".join(document.text_content().split())
    except (ValueError, TypeError):
        raise SourceError("invalid_native_description_html") from None
    if not text:
        raise SourceError("empty_native_description")
    return {"status": "ok", "source": "workday", "kind": "workday_detail", "board_url": context["board_url"],
            "source_id": context["origin"] + "/" + context["site"] + path,
            "external_path": path, "url": context["board_url"] + path, "title": info["title"],
            "source_description": text, "source_description_html": info["jobDescription"],
            "body_representation": "native_cxs_job_description", "visible_description": None,
            "native_job_posting_id": info["id"], "source_requisition_id": info.get("jobReqId"),
            "original_published_at": None, "source_start_date_raw": info.get("startDate"),
            "native_fields": {k: v for k, v in info.items() if k in JOB_FIELDS},
            "response_sha256": hashlib.sha256(raw).hexdigest(), "coverage_complete": False,
            "reviewed_by_model": False, "limits": LIMITS}


def read(board_url, *, offset=0, limit=20, first_page_total=None, path=None, transport=request):
    context = board(board_url)
    base = context["origin"] + "/wday/cxs/" + context["tenant"] + "/" + context["site"]
    if path is None:
        integer(offset, 0, 1_000_000)
        integer(limit, 1, 20)
        if first_page_total is not None:
            integer(first_page_total, 0, 100_000_000)
        if offset > 0 and (first_page_total is None or offset >= first_page_total):
            raise SourceError("valid_initial_native_total_required_for_offset")
        target = base + "/jobs"
        body = json.dumps({"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}).encode()
    else:
        if offset != 0 or limit != 20 or first_page_total is not None:
            raise SourceError("details_do_not_accept_pagination")
        path = external_path(path)
        target, body = base + path, None
    checked_policy = policy(context["origin"], target, transport=transport)
    requested_at = datetime.now(timezone.utc).isoformat()
    raw = transport(target, payload=body)
    result = inventory(raw, board_url, offset=offset, limit=limit, first_page_total=first_page_total) if path is None else detail(raw, board_url, path)
    result.update({"requested_at": requested_at, "observed_at": datetime.now(timezone.utc).isoformat(),
                   "request_url": target, "request_method": "POST" if body is not None else "GET",
                   "policy": checked_policy})
    return result


def capabilities():
    return {"status": "ok", "source": "workday", "operations": ["inventory", "detail"],
            "seed_required": True, "inventory": "Unfiltered native POST: appliedFacets={}, searchText='', limit 1..20, offset 0..1000000. Nonzero offset requires exact first_page_total from the same board's initial response; never request offset >= that bound.",
            "detail": "Anonymous GET of the exact returned /job/... path on the same tenant and site.",
            "acquisition_filters": [], "max_complete_response_bytes": MAX_BYTES,
            "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--board-url")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--first-page-total", type=int)
    parser.add_argument("--external-path")
    args = parser.parse_args()
    try:
        result = capabilities() if args.capabilities else read(args.board_url, offset=args.offset,
                                                              limit=args.limit, first_page_total=args.first_page_total,
                                                              path=args.external_path)
    except SourceError as error:
        result = {"status": "source_limited", "source": "workday", "count": None,
                  "source_result_count": None, "error": error.code, "http_status": error.http_status,
                  "retry_after": error.retry_after, "coverage_complete": False, "reviewed_by_model": False}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
