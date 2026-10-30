"""Original anonymous reader for independently qualified GULP job read routes.

Native schema/HTTP facts were observed from public interface references; no
website implementation, reference program, account or applicant data is used.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from public_http import MAX_BYTES, NoRedirect, SourceError, load_json, request, robot_policy

ORIGIN = "https://www.gulp.de"
SEARCH = ORIGIN + "/gulp2/rest/internal/projects/jobs/search"
DETAIL = ORIGIN + "/gulp2/rest/internal/projects/job/"
FRONT = ORIGIN + "/gulp2/g/jobs/"
AGENT = "JobMarketMCP/0.4.27 (+https://github.com/ahmed-elkashef/job-market-mcp)"
PAGE_SIZE = 20
MAX_TOTAL = 10_000_000
KINDS = {"TEMP_JOB", "PERM_JOB"}
ACCOUNT_FIELDS = {"applicationDate", "favorite", "hidden", "memoText"}


def advert_id(url):
    if not isinstance(url, str):
        raise SourceError("exact_acquired_native_job_URI_required")
    match = re.fullmatch(re.escape(FRONT) + r"(C[0-9]{8})", url)
    if not match:
        raise SourceError("exact_acquired_native_job_URI_required")
    return match[1]


def checked_read_route(url, method):
    if method == "POST" and url == SEARCH:
        return url
    if method == "GET" and (url == ORIGIN + "/robots.txt" or isinstance(url, str)
                            and re.fullmatch(re.escape(DETAIL) + r"C[0-9]{8}\?language=DE", url)):
        return url
    raise SourceError("unqualified_read_route_or_method")


def check_page(page, first_page_total):
    if type(page) is not int or not 0 <= page < MAX_TOTAL // PAGE_SIZE:
        raise SourceError("bounded_zero_based_native_page_required")
    if page == 0:
        if first_page_total is not None:
            raise SourceError("initial_page_cannot_carry_counter_state")
    elif (type(first_page_total) is not int or not 0 < first_page_total <= MAX_TOTAL
          or page * PAGE_SIZE >= first_page_total):
        raise SourceError("continuation_requires_acquired_counter_and_in_range_native_page")


def base(kind):
    return {"status": "ok", "source": "gulp", "kind": kind,
            "source_country": "DE", "source_country_is_job_worksite_proof": False,
            "coverage_complete": False, "full_posting_reviewed": False, "reviewed_by_model": False,
            "original_publication_clock_verified": False, "worker_country_permission_verified": False,
            "native_contract_type_is_student_model_proof": False,
            "source_result_count_unit": "native_job_search_records"}


def native_identity(row):
    if not isinstance(row, dict):
        raise SourceError("native_job_record_required")
    identifier = advert_id(row.get("url"))
    if row.get("id") != identifier or row.get("idInIndex") != identifier:
        raise SourceError("native_job_identity_disagrees")
    if not isinstance(row.get("type"), str) or row["type"] not in KINDS:
        raise SourceError("unqualified_native_contract_type")
    if any(row.get(field) is not None for field in ACCOUNT_FIELDS):
        raise SourceError("unexpected_personalized_native_account_state")
    for field in ("title", "location"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise SourceError("native_job_header_missing")
    return identifier


def parse_inventory(data, *, page=0, first_page_total=None):
    check_page(page, first_page_total)
    if not isinstance(data, dict) or type(data.get("totalCount")) is not int:
        raise SourceError("native_search_counter_missing")
    total, rows = data["totalCount"], data.get("projects")
    if not 0 <= total <= MAX_TOTAL or not isinstance(rows, list):
        raise SourceError("native_search_counter_or_collection_invalid")
    if page and total != first_page_total:
        raise SourceError("native_search_counter_changed_resume_requires_reconciliation")
    offset = page * PAGE_SIZE
    if (offset >= total and not (page == total == 0)
            or len(rows) != min(PAGE_SIZE, total - offset)):
        raise SourceError("native_page_length_and_counter_disagree")
    output, seen = [], set()
    for row in rows:
        identifier = native_identity(row)
        if identifier in seen:
            raise SourceError("duplicate_native_identity_within_page")
        seen.add(identifier)
        if (not isinstance(row.get("description"), str)
                or not isinstance(row.get("skills"), list)
                or any(not isinstance(item, str) for item in row["skills"])
                or type(row.get("isRemoteWorkPossible")) is not bool):
            raise SourceError("native_metadata_fields_invalid")
        output.append({"id": "gulp::" + identifier, "native_job_id": identifier,
                       "url": row["url"], "title": row["title"], "location_raw": row["location"],
                       "native_contract_type": row["type"], "company_name_raw": row.get("companyName"),
                       "remote_possible_raw": row["isRemoteWorkPossible"],
                       "original_publication_date_raw": row.get("originalPublicationDate"),
                       "start_date_raw": row.get("startDate"), "native_metadata": row,
                       "description_is_full_primary": False})
    more = offset + len(rows) < total
    return {**base("german_staffing_inventory"), "page": page, "native_page_size": PAGE_SIZE,
            "native_search_payload": {"query": None, "page": page, "limit": PAGE_SIZE, "language": "DE"},
            "role_country_model_or_remote_filters_applied": False,
            "source_result_count": total, "returned_count": len(rows), "records": output,
            "has_more": more, "native_terminal_page": not more,
            "pagination_contract": "qualified_zero_based_native_page_fixed_twenty_records",
            "next_request": {"tool": "de_public_gulp_inventory", "backend_native_tool": "gulp_inventory",
                             "arguments": {"page": page + 1, "first_page_total": total}} if more else None,
            "limits": ["Anonymous live search is not an immutable snapshot; reconcile changed counts and cross-page identities.",
                       "Metadata descriptions are previews. Full native detail and individual student-model review remain required.",
                       "TEMP_JOB/PERM_JOB describe placement contracts, not mandatory/voluntary internship or working-student eligibility.",
                       "Remote-possible, source locale, source country and raw dates do not prove Germany remote permission, worksites or original weekly clocks."]}


class BodyText(HTMLParser):
    """Text-only projection; scripts, controls and media are never executed."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.blocked = [], []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template", "iframe", "form", "object"}:
            self.blocked.append(tag)
        if not self.blocked and tag in {"p", "li", "div", "br", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.blocked and self.blocked[-1] == tag:
            self.blocked.pop()
        elif not self.blocked and tag in {"p", "li", "div", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(data)


def text_only(value):
    parser = BodyText()
    parser.feed(value)
    parser.close()
    return "\n".join(line for line in (re.sub(r"\s+", " ", part).strip()
                                      for part in "".join(parser.parts).splitlines()) if line)


def parse_detail(data, *, url):
    requested_id = advert_id(url)
    identifier = native_identity(data)
    if identifier != requested_id:
        raise SourceError("requested_and_returned_job_identity_disagree")
    fields = ("description", "responsibilities", "skills", "benefits", "salary", "schedule")
    if any(not isinstance(data.get(field), str) for field in fields):
        raise SourceError("complete_native_job_fields_missing")
    sections = {field: text_only(data[field]) for field in fields}
    if not sections["description"] or not sections["responsibilities"] or not sections["skills"]:
        raise SourceError("complete_native_role_body_missing")
    published = None
    schema_error = None
    if isinstance(data.get("metaJobPosting"), str):
        try:
            published = load_json(data["metaJobPosting"])
        except SourceError as error:
            schema_error = error.code
    body = "\n\n".join(field + "\n" + value for field, value in sections.items() if value)
    return {**base("german_staffing_detail"), "id": "gulp::" + identifier, "native_job_id": identifier,
            "url": url, "title": data["title"], "location_raw": data["location"],
            "native_contract_type": data["type"], "native_schedule": data["schedule"],
            "company_name_raw": data.get("companyName"), "native_detail": data,
            "body_representation": "complete_native_public_GULP_job_detail_API_role_fields",
            "body_sections": sections, "full_description": body, "full_description_acquired": True,
            "source_result_count": None, "returned_count": 1,
            "original_publication_date_raw": data.get("originalPublicationDate"),
            "start_date_raw": data.get("startDate"), "published_job_posting": published,
            "published_job_posting_parse_error": schema_error,
            "limits": ["Complete public job API fields are retained; employer originals and application forms were not opened.",
                       "Schedule and descriptive part-time/remote claims can conflict; retain every field and review manually.",
                       "Public recruiter contact metadata is source evidence, never authorization to contact.",
                       "Body acquisition is not human review, personal fit, current eligibility or original-clock qualification."]}


class Client:
    def __init__(self, *, transport=request, opener=None):
        self.transport = transport
        self.opener = opener or build_opener(NoRedirect())
        self.rules, self.policy = None, None
        self.request_attempts = {"policy_GET": 0, "search_read_POST": 0, "detail_GET": 0}

    def guard(self, url, method):
        checked_read_route(url, method)
        if self.policy is None:
            def policy_read(target, **kwargs):
                checked_read_route(target, "GET")
                self.request_attempts["policy_GET"] += 1
                return self.transport(target, agent=AGENT, **kwargs)
            self.rules, self.policy = robot_policy(ORIGIN, transport=policy_read)
        if self.rules is not None:
            if not self.rules.can_fetch(AGENT, url):
                raise SourceError("robots_denies_native_read")
            # stdlib does not implement RFC wildcard matching. Conservatively
            # deny matching wildcard Disallow rules in applicable groups too;
            # never let this limitation become an access-policy bypass.
            entries = [entry for entry in self.rules.entries if entry.applies_to(AGENT)]
            if not entries and self.rules.default_entry:
                entries = [self.rules.default_entry]
            target = urlsplit(url).path + ("?" + urlsplit(url).query if urlsplit(url).query else "")
            for entry in entries:
                for rule in entry.rulelines:
                    path = unquote(rule.path)
                    if not rule.allowance and ("*" in path or path.endswith("$")):
                        pattern = path[:-1] if path.endswith("$") else path
                        pattern = "^" + re.escape(pattern).replace(r"\*", ".*") + ("$" if path.endswith("$") else "")
                        if re.search(pattern, target):
                            raise SourceError("robots_wildcard_denies_native_read_conservatively")
            if self.rules.crawl_delay(AGENT) or self.rules.request_rate(AGENT):
                raise SourceError("source_pacing_requires_operator_coordination")

    def post(self, payload):
        if (not isinstance(payload, dict) or set(payload) != {"query", "page", "limit", "language"}
                or payload["query"] is not None or payload["limit"] != PAGE_SIZE
                or type(payload["limit"]) is not int or payload["language"] != "DE"
                or type(payload["page"]) is not int or not 0 <= payload["page"] < MAX_TOTAL // PAGE_SIZE):
            raise SourceError("only_fixed_unfiltered_native_search_payload")
        self.guard(SEARCH, "POST")
        self.request_attempts["search_read_POST"] += 1
        try:
            with self.opener.open(Request(SEARCH, method="POST", data=json.dumps(payload, separators=(",", ":")).encode(),
                                         headers={"User-Agent": AGENT, "Accept": "application/json",
                                                  "Content-Type": "application/json"}), timeout=20) as response:
                raw = response.read(MAX_BYTES + 1)
                if response.status != 200:
                    raise SourceError("unexpected_native_read_status", http_status=response.status)
                if len(raw) > MAX_BYTES:
                    raise SourceError("complete_response_exceeds_bound")
                return {"body": raw, "content_type": response.headers.get("Content-Type"),
                        "observed_at": datetime.now(timezone.utc).isoformat()}
        except HTTPError as error:
            status, retry_after = error.code, error.headers.get("Retry-After")
            error.close()
            raise SourceError("native_read_search_HTTP_error", http_status=status, retry_after=retry_after) from None
        except SourceError:
            raise
        except Exception:
            raise SourceError("native_read_transport_failed") from None

    def get(self, url):
        self.guard(url, "GET")
        self.request_attempts["detail_GET"] += 1
        return self.transport(url, accept="application/json", agent=AGENT, bound=MAX_BYTES)


def read(operation, *, page=0, first_page_total=None, url=None, client=None):
    if operation == "inventory":
        check_page(page, first_page_total)
        if url is not None:
            raise SourceError("inventory_does_not_accept_an_arbitrary_URI")
    elif operation == "detail":
        advert_id(url)
        if type(page) is not int or page != 0 or first_page_total is not None:
            raise SourceError("detail_does_not_accept_inventory_state")
    else:
        raise SourceError("only_native_inventory_and_detail_reads")
    client = client or Client()
    if operation == "inventory":
        response = client.post({"query": None, "page": page, "limit": PAGE_SIZE, "language": "DE"})
    else:
        response = client.get(DETAIL + advert_id(url) + "?language=DE")
    if (response.get("content_type") or "").split(";", 1)[0].strip().lower() != "application/json":
        raise SourceError("native_job_response_not_JSON")
    try:
        data = load_json(response["body"].decode("utf-8", errors="strict"))
    except UnicodeDecodeError:
        raise SourceError("native_job_JSON_not_strict_UTF8") from None
    output = (parse_inventory(data, page=page, first_page_total=first_page_total) if operation == "inventory"
              else parse_detail(data, url=url))
    output.update(native_response_sha256=hashlib.sha256(response["body"]).hexdigest(),
                  observed_at=response.get("observed_at"), source_policy=getattr(client, "policy", None),
                  native_HTTP_request_attempts=getattr(client, "request_attempts", None))
    return output
