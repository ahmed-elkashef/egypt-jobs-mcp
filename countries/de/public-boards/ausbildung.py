"""Original read-only Ausbildung.de internship catalogue and public advert reader.

Only a separately qualified public search operation is issued by POST. Its
published function reference is protocol routing data, never a session token.
No website program is imported, executed, shipped or copied into this reader.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, build_opener

from lxml import html

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from native_flight import find_property, records_from_html, records_from_stream, resolve
from public_http import MAX_BYTES, NoRedirect, SourceError, load_json, request, robot_policy

ORIGIN = "https://www.ausbildung.de"
CATALOGUE = ORIGIN + "/schuelerpraktikum/stellen/"
AGENT = "JobMarketMCP/0.4.28 (+https://github.com/ahmed-elkashef/job-market-mcp)"
PAGE_SIZE = 20
MAX_TOTAL = 10_000_000
REFERENCE_ASSET = "/_next/static/chunks/006sfh0i8jsm5.js"
REFERENCE_SHA256 = "2a3916610a6dcb25d4ff77510fd21b01119f1685d8bf530a59035f430567d40c"
SEARCH_REFERENCE = "60240a04386578e515f6bb78e312867f48b505e901"
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
BINDING_FIELDS = {"source", "catalogue", "protocol_sha256", "resultsCount", "vacanciesCount", "countryEntryCode"}


def base(kind):
    return {"status": "ok", "source": "ausbildung_de", "kind": kind, "source_country": "DE",
            "source_country_is_job_worksite_proof": False, "coverage_complete": False,
            "full_posting_reviewed": False, "reviewed_by_model": False,
            "original_publication_clock_verified": False, "worker_country_permission_verified": False,
            "portal_school_section_is_school_only_model_proof": False}


def advert_id(url):
    if not isinstance(url, str):
        raise SourceError("exact_acquired_native_advert_URI_required")
    match = re.fullmatch(re.escape(CATALOGUE) + r"[a-z0-9]+(?:-[a-z0-9]+)*-(" + UUID + r")/", url)
    if not match:
        raise SourceError("exact_acquired_native_advert_URI_required")
    return match[1]


def check_request(offset, binding):
    if type(offset) is not int or not 0 <= offset < MAX_TOTAL or offset % PAGE_SIZE:
        raise SourceError("native_from_must_be_nonnegative_multiple_of_twenty")
    if offset == 0:
        if binding is not None:
            raise SourceError("initial_catalogue_cannot_carry_resume_binding")
    elif (not isinstance(binding, dict) or set(binding) != BINDING_FIELDS
          or binding.get("source") != "ausbildung_de" or binding.get("catalogue") != CATALOGUE
          or binding.get("protocol_sha256") != REFERENCE_SHA256 or binding.get("countryEntryCode") != "DE"
          or type(binding.get("resultsCount")) is not int or not 0 < binding["resultsCount"] <= MAX_TOTAL
          or offset >= binding["resultsCount"] or type(binding.get("vacanciesCount")) is not int
          or not 0 <= binding["vacanciesCount"] <= MAX_TOTAL):
        raise SourceError("continuation_requires_exact_acquired_native_binding_and_in_range_from")


def initial_data(body):
    tree = html.fromstring(body.decode("utf-8", errors="strict"))
    if REFERENCE_ASSET not in tree.xpath("//script[@src]/@src"):
        raise SourceError("published_search_protocol_deployment_changed_requalification_required")
    records = records_from_html(body)
    candidates = []
    for record in records.values():
        if not isinstance(record, (dict, list)):
            continue
        for results in find_property(record, "searchResults"):
            # Select the actual search component, never unrelated tracking/account state.
            if isinstance(record, list):
                def components(value):
                    if isinstance(value, list):
                        if len(value) == 4 and value[0] == "$" and isinstance(value[3], dict):
                            yield value[3]
                        for item in value:
                            yield from components(item)
                for props in components(record):
                    if props.get("searchResults") != results or props.get("searchType") != "student":
                        continue
                    if (resolve(props.get("searchParams"), records) != {}
                            or props.get("countryEntryCode") != "DE"):
                        raise SourceError("unfiltered_native_Germany_catalogue_required")
                    state = resolve(props.get("initialState"), records)
                    if not isinstance(state, dict) or any(v not in (None, [], "") for v in state.values()):
                        raise SourceError("unexpected_active_native_search_filter")
                    if (resolve(props.get("favoriteVacancyPublicIds"), records) not in (None, [])
                            or props.get("jobletterSubscribed") not in (None, False)):
                        raise SourceError("unexpected_personalized_native_account_state")
                    candidates.append(resolve(results, records))
    unique = {json.dumps(value, sort_keys=True, ensure_ascii=False): value for value in candidates}
    if len(unique) != 1:
        raise SourceError("one_unambiguous_native_search_component_required")
    return next(iter(unique.values()))


def continuation_data(body):
    records = records_from_stream(body)
    root = records.get("0")
    if not isinstance(root, dict) or root.get("a") != "$@1":
        raise SourceError("native_read_action_result_reference_unqualified")
    result = records.get("1")
    if not isinstance(result, dict) or set(result) != {"data", "meta", "statusCode"}:
        raise SourceError("native_read_action_result_shape_unqualified")
    if result["statusCode"] != "200":
        raise SourceError("native_read_action_reported_failure")
    return resolve(result["data"], records)


def parse_inventory(data, *, offset=0, binding=None):
    check_request(offset, binding)
    if not isinstance(data, dict) or not isinstance(data.get("meta"), dict) or not isinstance(data.get("hits"), dict):
        raise SourceError("native_internship_search_shape_missing")
    meta, hits = data["meta"], data["hits"]
    for field in ("resultsCount", "vacanciesCount"):
        if type(meta.get(field)) is not int or not 0 <= meta[field] <= MAX_TOTAL:
            raise SourceError("native_search_counters_invalid")
    if meta.get("countryEntryCode") != "DE" or meta.get("sessionLocation") is not False:
        raise SourceError("native_country_or_session_scope_unqualified")
    current = {"source": "ausbildung_de", "catalogue": CATALOGUE, "protocol_sha256": REFERENCE_SHA256,
               **{field: meta[field] for field in ("resultsCount", "vacanciesCount", "countryEntryCode")}}
    if offset and current != binding:
        raise SourceError("native_search_counter_or_scope_drift_requires_reconciliation")
    rows = hits.get("primary")
    if not isinstance(rows, list) or hits.get("extended") != []:
        raise SourceError("unfiltered_primary_and_extended_collections_unqualified")
    total = meta["resultsCount"]
    if (offset >= total and not (offset == total == 0)) or len(rows) != min(PAGE_SIZE, total - offset):
        raise SourceError("complete_native_page_length_and_result_count_disagree")
    output, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("slug"), str):
            raise SourceError("native_internship_record_or_slug_missing")
        url = CATALOGUE + row["slug"] + "/"
        identity = advert_id(url)
        if identity != row.get("vacancyPublicId") or not re.fullmatch(UUID, str(row.get("jobPostingPublicId", ""))):
            raise SourceError("native_advert_slug_and_vacancy_identity_disagree")
        if identity in seen:
            raise SourceError("duplicate_native_vacancy_identity_within_page")
        seen.add(identity)
        if not isinstance(row.get("title"), str) or not row["title"].strip() or not isinstance(row.get("cityName"), str):
            raise SourceError("native_advert_header_missing")
        if not isinstance(row.get("internshipKinds"), list) or any(not isinstance(v, str) for v in row["internshipKinds"]):
            raise SourceError("native_internship_kinds_invalid")
        output.append({"id": "ausbildung_de::" + identity, "native_vacancy_id": identity,
                       "native_job_posting_id": row["jobPostingPublicId"], "url": url, "title": row["title"],
                       "location_raw": row["cityName"], "internship_kinds_raw": row["internshipKinds"],
                       "native_metadata": row, "description_is_full_primary": False})
    more = offset + len(rows) < total
    return {**base("german_internship_catalogue"), "native_from": offset, "native_page_size": PAGE_SIZE,
            "native_search_parameters": {} if offset == 0 else {"from": offset}, "native_search_meta": meta,
            "source_result_count": total, "source_vacancy_place_count": meta["vacanciesCount"],
            "source_result_count_unit": "publisher_resultsCount_distinct_from_vacanciesCount",
            "returned_count": len(rows), "records": output, "native_binding": current,
            "has_more": more, "native_terminal_page": not more,
            "role_model_or_geography_filters_applied": False,
            "next_request": {"tool": "de_public_ausbildung_inventory", "backend_native_tool": "ausbildung_inventory",
                             "arguments": {"from": offset + PAGE_SIZE, "native_binding": current}} if more else None,
            "limits": ["This is the unfiltered native portal internship scope, not a census of German employment.",
                       "The school-section URL, school class and internship labels alone do not establish school-only or university eligibility.",
                       "Both native counters are retained; result cards can cover multiple places/branches.",
                       "Frankfurt metadata is the source's default search context, not a personal commute or actual worksite qualification.",
                       "Live counters and cross-page identities require reconciliation; a terminal page alone does not prove all pages acquired.",
                       "Employer originals can be expired while portal mirrors remain visible; current employer status needs separate evidence."]}


def parse_detail(body, *, url):
    identity = advert_id(url)
    tree = html.fromstring(body.decode("utf-8", errors="strict"))
    canonical = tree.xpath('//link[@rel="canonical"]/@href')
    mains, headings = tree.xpath("//main"), tree.xpath("//h1")
    if canonical != [url] or len(mains) != 1 or len(headings) != 1:
        raise SourceError("native_advert_canonical_main_or_heading_unqualified")
    sections = [" ".join(node.text_content().split()) for node in mains[0].xpath(".//h2")]
    if not {"Das Praktikum auf einen Blick", "Die Aufgaben im Praktikum", "So läuft die Bewerbung ab"} <= set(sections):
        raise SourceError("native_internship_role_and_application_sections_missing")
    title = " ".join(headings[0].text_content().split())
    links = [{"url": urljoin(url, node.get("href")), "label": " ".join(node.text_content().split())}
             for node in mains[0].xpath(".//a[@href]")]
    media = [{"tag": node.tag, "src": urljoin(url, node.get("src")), "alt": node.get("alt")}
             for node in mains[0].xpath(".//img[@src]|.//iframe[@src]|.//video[@src]")]
    schemas, schema_errors = [], []
    schema_raw = [node.text or "" for node in tree.xpath('//script[@type="application/ld+json"]')]
    for index, raw in enumerate(schema_raw):
        try:
            schemas.append(load_json(raw.encode("utf-8")))
        except SourceError as error:
            schema_errors.append({"index": index, "error": error.code})
    for node in mains[0].xpath(".//script|.//style|.//noscript|.//iframe|.//template"):
        node.drop_tree()
    native_nodes = list(mains[0].itertext())
    description = "\n".join(line for line in (re.sub(r"\s+", " ", part).strip()
                                               for part in "".join(native_nodes).splitlines()) if line)
    if not title or not description:
        raise SourceError("complete_native_public_advert_body_missing")
    return {**base("german_internship_advert"), "id": "ausbildung_de::" + identity,
            "native_vacancy_id": identity, "url": url, "title": title, "full_description": description,
            "full_description_acquired": True, "body_representation": "complete_public_portal_main_text",
            "native_main_text_nodes": native_nodes, "native_section_headings": sections,
            "portal_education_direction_pay_is_role_salary_proof": False,
            "portal_school_class_is_university_eligibility_proof": False,
            "native_links": links, "native_media": media, "published_structured_data": schemas,
            "published_structured_data_raw": schema_raw, "published_structured_data_parse_errors": schema_errors,
            "employer_original_status_verified": False, "source_result_count": None, "returned_count": 1,
            "limits": ["Complete portal text is not current employer-original status, individual fit or a verified weekly clock.",
                       "Generic education-direction descriptions/pay are career context, not this internship's compensation or degree requirements.",
                       "Advertised links and nontext media are evidence only; no application, account, contact or external target was opened."]}


class Client:
    def __init__(self, *, transport=request, opener=None):
        self.transport, self.opener = transport, opener or build_opener(NoRedirect())
        self.rules, self.policy = None, None
        self.request_attempts = {"policy_GET": 0, "catalogue_GET": 0, "search_read_POST": 0, "detail_GET": 0}

    def guard(self, url, method):
        if method not in {"GET", "POST"} or (method == "POST" and url != CATALOGUE):
            raise SourceError("unqualified_read_route_or_method")
        if method == "GET" and url != CATALOGUE:
            advert_id(url)
        if self.policy is None:
            def policy_read(target, **kwargs):
                if target != ORIGIN + "/robots.txt":
                    raise SourceError("unqualified_policy_route")
                self.request_attempts["policy_GET"] += 1
                return self.transport(target, agent=AGENT, **kwargs)
            self.rules, self.policy = robot_policy(ORIGIN, transport=policy_read)
        if self.rules is not None:
            if not self.rules.can_fetch(AGENT, url):
                raise SourceError("robots_denies_native_read")
            entries = [entry for entry in self.rules.entries if entry.applies_to(AGENT)]
            if not entries and self.rules.default_entry:
                entries = [self.rules.default_entry]
            target = urlsplit(url).path
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

    def get(self, url, kind):
        if url != CATALOGUE:
            advert_id(url)
        if kind != ("catalogue_GET" if url == CATALOGUE else "detail_GET"):
            raise SourceError("unqualified_read_request_kind")
        self.guard(url, "GET")
        self.request_attempts[kind] += 1
        return self.transport(url, accept="text/html", agent=AGENT, bound=MAX_BYTES)

    def search(self, offset):
        if type(offset) is not int or not 0 < offset < MAX_TOTAL or offset % PAGE_SIZE:
            raise SourceError("qualified_noninitial_native_from_required")
        self.guard(CATALOGUE, "POST")
        self.request_attempts["search_read_POST"] += 1
        payload = json.dumps([{"from": offset}], separators=(",", ":")).encode("utf-8")
        headers = {"User-Agent": AGENT, "Accept": "text/x-component", "Next-Action": SEARCH_REFERENCE,
                   "Content-Type": "text/plain;charset=UTF-8", "Origin": ORIGIN}
        started = datetime.now(timezone.utc).isoformat()
        try:
            with self.opener.open(Request(CATALOGUE, data=payload, headers=headers, method="POST"), timeout=15) as response:
                if response.status != 200:
                    raise SourceError("unexpected_http_status", http_status=response.status)
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise SourceError("complete_response_exceeds_bound")
                content_type = response.headers.get("Content-Type", "")
                if not content_type.startswith("text/x-component"):
                    raise SourceError("unexpected_native_read_content_type")
                return {"body": raw, "content_type": content_type, "requested_at": started,
                        "observed_at": datetime.now(timezone.utc).isoformat()}
        except HTTPError as error:
            status, retry_after = error.code, error.headers.get("Retry-After")
            error.close()
            raise SourceError("source_http_error", http_status=status, retry_after=retry_after) from None
        except SourceError:
            raise
        except Exception:
            raise SourceError("source_transport_failed") from None


def read(operation, *, offset=0, binding=None, url=None, client=None):
    client = client or Client()
    if operation == "inventory":
        check_request(offset, binding)
        response = client.get(CATALOGUE, "catalogue_GET") if offset == 0 else client.search(offset)
        data = initial_data(response["body"]) if offset == 0 else continuation_data(response["body"])
        value = parse_inventory(data, offset=offset, binding=binding)
    elif operation == "detail":
        advert_id(url)
        response = client.get(url, "detail_GET")
        value = parse_detail(response["body"], url=url)
    else:
        raise SourceError("unqualified_read_operation")
    return {**value, "source_policy": client.policy, "native_HTTP_request_attempts": client.request_attempts,
            "response_sha256": hashlib.sha256(response["body"]).hexdigest(),
            "requested_at": response.get("requested_at"), "observed_at": response.get("observed_at")}
