"""Original anonymous JOIN employer-board reader; source UI contexts are not jobs."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

from lxml import html

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from shared.public_http import SourceError, load_json, request, robot_policy  # noqa: E402

SOURCE = "join"
ORIGIN = "https://join.com"
LIST_PATH = "/companies/{verified-employer-slug}"
AGENT = "job-market-mcp/0.4.18"
SLUG = r"[a-z0-9][a-z0-9-]{0,119}"
JOB_PARAM = r"[1-9][0-9]{0,19}-[a-z0-9]+(?:-[a-z0-9]+)*"
LIMITS = [
    "Requires an independently identified exact JOIN employer board; provider support is not employer discovery or country coverage.",
    "The source UI total includes an enabled spontaneous-application slot. It is context, never a vacancy. A final virtual page can repeat cached preceding jobs; those rows are retained separately and never recounted.",
    "Freeze the initial native total, follow every returned continuation and reconcile distinct native job IDs. URL/publication IDs and stable internal IDs differ and can redirect within the same company.",
    "Native creation/update/schema clocks are not verified original publication. Employee/full-time, country and hybrid labels do not prove a student contract or Germany worker eligibility.",
    "Complete native primary HTML, separately published schema and company context remain separate; source content still needs individual review and actual application terms.",
    "Only anonymous first-party robots/HTML GETs and scope-checked same-company numeric job redirects. No account, spontaneous-application page, application form action, cookie, key, script, image, contact or subscription request.",
]


def checked_url(url, operation):
    if (
        not isinstance(url, str)
        or url != url.strip()
        or len(url) > 2048
        or any(ord(c) < 33 for c in url)
    ):
        raise SourceError("invalid_join_uri")
    p = urlsplit(url)
    if p.scheme + "://" + p.netloc != ORIGIN or p.fragment:
        raise SourceError("unqualified_join_origin")
    if operation == "inventory":
        match = re.fullmatch(r"/companies/(" + SLUG + r")", p.path)
        q = parse_qs(p.query, keep_blank_values=True)
        if (
            not match
            or set(q) - {"page"}
            or any(len(v) != 1 for v in q.values())
            or q.get("page") is not None
            and not re.fullmatch(r"[2-9]|[1-9][0-9]{1,5}", q["page"][0])
        ):
            raise SourceError("unqualified_join_inventory")
        company, page = match[1], int(q.get("page", ["1"])[0])
        if url != inventory_uri(company, page):
            raise SourceError("noncanonical_join_inventory")
    elif operation == "detail":
        if p.query or not re.fullmatch(r"/companies/" + SLUG + "/" + JOB_PARAM, p.path):
            raise SourceError("unqualified_join_posting")
    else:
        raise SourceError("unsupported_join_operation")
    return url


def inventory_uri(company, page=1):
    if (
        not isinstance(company, str)
        or not re.fullmatch(SLUG, company)
        or type(page) is not int
        or not 1 <= page <= 999999
    ):
        raise SourceError("invalid_join_partition")
    return ORIGIN + "/companies/" + company + ("?page=" + str(page) if page > 1 else "")


def partition(url):
    checked_url(url, "inventory")
    p = urlsplit(url)
    return p.path.split("/")[2], int(parse_qs(p.query).get("page", ["1"])[0])


def job_uri(company, parameter):
    value = ORIGIN + "/companies/" + company + "/" + str(parameter)
    checked_url(value, "detail")
    return value


def identity(company, value):
    if type(value) is not int or value <= 0 or not re.fullmatch(SLUG, company):
        raise SourceError("invalid_join_native_job_id")
    return "join::" + company + "::" + str(value)


def checked_redirects(requested, final, hops):
    checked_url(requested, "detail")
    checked_url(final, "detail")
    company = urlsplit(final).path.split("/")[2]
    if not isinstance(hops, list) or len(hops) > 4:
        raise SourceError("invalid_join_redirect_chain")
    previous, seen = requested, {requested}
    if urlsplit(requested).path.split("/")[2] != company:
        raise SourceError("join_redirect_changed_employer")
    for hop in hops:
        if (
            not isinstance(hop, dict)
            or hop.get("from") != previous
            or hop.get("http_status") not in {301, 302, 303, 307, 308}
        ):
            raise SourceError("invalid_join_redirect_chain")
        target = checked_url(hop.get("to"), "detail")
        if target in seen or urlsplit(target).path.split("/")[2] != company:
            raise SourceError("join_redirect_cycle_or_changed_company")
        previous = target
        seen.add(target)
    if previous != final:
        raise SourceError("join_redirect_chain_does_not_reach_canonical_posting")


def squash(value):
    return "".join(value.split())


def public_html(value):
    if not isinstance(value, str) or not value.strip():
        raise SourceError("missing_join_public_html")
    try:
        node = html.fragment_fromstring(value, create_parent="div")
        for child in node.xpath(
            ".//script|.//style|.//iframe|.//form|.//input|.//button|.//select|.//textarea|.//object|.//embed|.//svg|.//img|.//video|.//audio"
        ):
            child.drop_tree()
        for child in node.iter():
            for name in list(child.attrib):
                if (
                    name not in {"href", "title"}
                    or name == "href"
                    and urlsplit(child.attrib[name]).scheme not in {"", "http", "https"}
                ):
                    del child.attrib[name]
        return html.tostring(node, encoding="unicode"), " ".join(" ".join(node.itertext()).split())
    except (ValueError, TypeError):
        raise SourceError("invalid_join_public_html") from None


def model(raw, url, operation):
    checked_url(url, operation)
    if not isinstance(raw, bytes) or len(raw) > 8 * 1024 * 1024:
        raise SourceError("invalid_join_complete_html")
    try:
        doc = html.document_fromstring(raw)
        scripts = doc.xpath('//script[@id="__NEXT_DATA__" and @type="application/json"]')
        if len(scripts) != 1:
            raise SourceError("missing_or_ambiguous_join_data")
        data = load_json(scripts[0].text or "")
        props = data["props"]["pageProps"]
        keys = [k for k in ("initialState", "pageData") if k in props]
        if len(keys) != 1 or props.get("isOnline") is not True:
            raise SourceError("unqualified_join_state_variant")
        state, company = props[keys[0]], urlsplit(url).path.split("/")[2]
        allowed_query = {"companySlug", "id"} if operation == "detail" else {"companySlug", "page"}
        if not isinstance(data.get("query"), dict) or set(data["query"]) - allowed_query:
            raise SourceError("unqualified_join_native_query")
        corp = state.get("company")
        if corp is None and operation == "detail" and isinstance(state.get("job"), dict):
            corp = state["job"].get("company")
        if (
            not isinstance(corp, dict)
            or corp.get("domain") != company
            or corp.get("isPublic") is not True
            or type(corp.get("id")) is not int
            or corp["id"] <= 0
            or not isinstance(corp.get("name"), str)
            or not corp["name"].strip()
            or data.get("query", {}).get("companySlug") != company
        ):
            raise SourceError("join_company_identity_mismatch")
        expected = (
            {"/companies/[companySlug]/[id]"}
            if operation == "detail"
            else {"/companies/[companySlug]", "/companies/[companySlug]/_dynamic"}
        )
        if data.get("page") not in expected:
            raise SourceError("join_route_is_not_the_requested_public_resource")
        return doc, data, state, keys[0], company, corp
    except (KeyError, TypeError, ValueError, IndexError) as error:
        if isinstance(error, SourceError):
            raise
        raise SourceError("incomplete_join_public_state") from None


def envelope(raw, url, kind):
    return {
        "source": SOURCE,
        "status": "ok",
        "kind": kind,
        "url": url,
        "requested_url": url,
        "raw_html_sha256": hashlib.sha256(raw).hexdigest(),
        "coverage_complete": False,
        "reviewed_by_model": False,
        "full_posting_reviewed": False,
        "source_scripts_images_or_application_requested": False,
        "limits": LIMITS,
    }


def inventory(raw, url):
    doc, data, state, variant, company, corp = model(raw, url, "inventory")
    _, page = partition(url)
    jobs = state.get("jobs")
    if (
        not isinstance(jobs, dict)
        or jobs.get("filters") != {}
        or not isinstance(jobs.get("items"), list)
    ):
        raise SourceError("join_unfiltered_complete_job_array_required")
    pagination, rows = jobs.get("pagination"), jobs["items"]
    enabled = corp.get("preference", {}).get("isSpontaneousApplicationEnabled")
    if type(enabled) is not bool or not isinstance(pagination, dict):
        raise SourceError("missing_join_native_pagination_or_context_flag")
    if any(
        type(pagination.get(k)) is not int
        for k in ["page", "pageCount", "pageSize", "perPage", "total"]
    ):
        raise SourceError("invalid_join_native_pagination_types")
    total, size, pages, native_page = (
        pagination[k] for k in ["total", "perPage", "pageCount", "page"]
    )
    if (
        total < int(enabled)
        or size != 5
        or pagination["pageSize"] != 5
        or pages != (total + size - 1) // size
        or not 1 <= page <= max(1, pages)
        or data["query"].get("page") != (str(page) if page > 1 else None)
    ):
        raise SourceError("join_native_pagination_does_not_reconcile")
    vacancy_total = total - int(enabled)
    real_pages = (vacancy_total + size - 1) // size
    virtual = enabled and page > real_pages and page == pages
    if native_page != (max(1, real_pages) if virtual else page):
        raise SourceError("join_source_page_reset_or_skip")
    expected_rows = min(size, vacancy_total - (native_page - 1) * size) if vacancy_total else 0
    if len(rows) != expected_rows:
        raise SourceError("join_native_row_count_does_not_reconcile")
    projected, seen = [], set()
    links = set(doc.xpath("//a/@href"))
    for row in rows:
        if not isinstance(row, dict):
            raise SourceError("invalid_join_native_job_row")
        stable = identity(company, row.get("id"))
        target = job_uri(company, row.get("idParam"))
        if (
            stable in seen
            or target not in links
            or not isinstance(row.get("title"), str)
            or not row["title"].strip()
        ):
            raise SourceError("join_native_ids_or_rendered_anchors_disagree")
        seen.add(stable)
        projected.append(
            {
                "id": stable,
                "url": target,
                "title": row["title"],
                "native_job_id": row["id"],
                "native_public_id_param": row["idParam"],
                "native_url_posting_id": int(row["idParam"].split("-", 1)[0]),
                "native_created_at": row.get("createdAt"),
                "native_country": row.get("country"),
                "native_city": row.get("city"),
                "native_employment_type": row.get("employmentType"),
                "native_workplace_type": row.get("workplaceType"),
                "native_remote_type": row.get("remoteType"),
                "original_published_at": None,
                "native_model_label": None,
                "source_row": row,
            }
        )
    contexts = (
        [
            {
                "kind": "spontaneous_application_context",
                "vacancy": False,
                "source_enabled": True,
                "source_native_total_slot": 1,
            }
        ]
        if enabled and page == max(1, pages)
        else []
    )
    result = envelope(raw, url, "german_public_board_page")
    result.update(
        company_slug=company,
        native_company_id=corp["id"],
        native_company_name=corp["name"],
        source_board_url=inventory_uri(company),
        native_SSR_state_key=variant,
        native_query=data["query"],
        native_filter_echo=jobs["filters"],
        native_pagination_raw=pagination,
        native_total_including_general_context=total,
        native_spontaneous_application_enabled=enabled,
        source_result_count=vacancy_total,
        source_count_basis="native_ui_total_minus_enabled_general_application_slot",
        returned_count=0 if virtual else len(projected),
        listings=[] if virtual else projected,
        native_cached_noncurrent_rows=projected if virtual else [],
        native_general_contexts=contexts,
        original_clock_basis="unverified_source_createdAt_not_original_publication",
        pagination={
            "page": page,
            "native_source_page": native_page,
            "native_pages": pages,
            "native_vacancy_pages": real_pages,
            "page_size": size,
            "source_result_count": vacancy_total,
            "native_total_with_context": total,
            "virtual_context_page": bool(virtual),
            "next_url": inventory_uri(company, page + 1) if page < pages else None,
        },
        source_metadata_untruncated=True,
        native_body_reviewed=False,
    )
    return result


def detail(raw, url, *, requested_url=None, redirects=None):
    checked_redirects(requested_url or url, url, redirects or [])
    doc, data, state, variant, company, corp = model(raw, url, "detail")
    job = state.get("job")
    if (
        not isinstance(job, dict)
        or job.get("companyId") != corp["id"]
        or job_uri(company, job.get("idParam")) != url
        or data["query"].get("id") != job["idParam"]
        or not isinstance(job.get("title"), str)
        or not job["title"].strip()
    ):
        raise SourceError("join_primary_job_identity_mismatch")
    stable = identity(company, job.get("id"))
    safe, text = public_html(job.get("description"))
    visible = html.document_fromstring(raw)
    for node in visible.xpath("//script|//style|//noscript|//template"):
        node.drop_tree()
    if not text or squash(text) not in squash(" ".join(visible.itertext())):
        raise SourceError("join_full_native_primary_not_rendered")
    canonical = doc.xpath('//link[@rel="canonical"]/@href')
    if canonical != [url]:
        raise SourceError("join_canonical_job_uri_mismatch")
    schemas = []
    for node in doc.xpath('//script[@type="application/ld+json"]'):
        value = load_json(node.text or "")
        candidates = value if isinstance(value, list) else [value]
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                schemas.append(item)
    matching = [s for s in schemas if s.get("url") == url and s.get("title") == job["title"]]
    if len(matching) != 1:
        raise SourceError("join_primary_schema_identity_ambiguous")
    contexts = []
    for name, value in [
        ("native_job_company_description", job.get("companyDesc")),
        ("native_board_company_description", corp.get("desc")),
    ]:
        if isinstance(value, str) and value.strip():
            clean, rendered = public_html(value)
            contexts.append({"kind": name, "raw_html": value, "safe_html": clean, "text": rendered})
    facts = {
        k: job.get(k)
        for k in [
            "status",
            "createdAt",
            "updatedAt",
            "closedAt",
            "lastId",
            "languageId",
            "language",
            "countryId",
            "country",
            "cityId",
            "city",
            "office",
            "contractTypeId",
            "contractType",
            "employmentType",
            "employmentTerms",
            "salaryFrequency",
            "salaryAmountFrom",
            "salaryAmountTo",
            "workplaceType",
            "remoteType",
            "hybrid",
            "remoteRegion",
            "categoryId",
            "category",
            "isDescriptionHtml",
            "isDescriptionSanitized",
        ]
        if k in job
    }
    result = envelope(raw, url, "german_public_board_detail")
    result.update(
        id=stable,
        title=job["title"],
        company_slug=company,
        native_company_id=corp["id"],
        native_company_name=corp["name"],
        native_job_id=job["id"],
        native_public_id_param=job["idParam"],
        native_url_posting_id=int(job["idParam"].split("-", 1)[0]),
        native_SSR_state_key=variant,
        requested_url=requested_url or url,
        canonical_url=url,
        native_redirects=redirects or [],
        description=safe,
        source_description=safe,
        raw_primary_description=job["description"],
        visible_description=text,
        body_representation="native_join_complete_primary_html",
        native_primary_visible_text_verified=True,
        source_body_untruncated=True,
        schema_description_used_as_full_body=False,
        schema_description=matching[0].get("description"),
        source_jobposting_schema=matching[0],
        native_job_facts=facts,
        native_context_sections=contexts,
        original_published_at=None,
        source_explicit_closed=job.get("status") in {"OFFLINE", "ARCHIVED"}
        or job.get("closedAt") is not None,
        native_status=job.get("status"),
        credentials_cookies_or_hydration_state_exported=False,
    )
    return result


def read(operation, url, *, transport=request):
    checked_url(url, operation)
    company = urlsplit(url).path.split("/")[2]
    policy, policy_meta = robot_policy(ORIGIN, transport=transport)
    current, hops, provenance, seen = url, [], [], set()
    for _ in range(5):
        checked_url(current, operation)
        if current in seen or urlsplit(current).path.split("/")[2] != company:
            raise SourceError("join_redirect_cycle_or_changed_company")
        seen.add(current)
        if policy is not None and not policy.can_fetch(AGENT, current):
            raise SourceError("join_current_robots_denies_resource")
        response = transport(
            current, accept="text/html", agent=AGENT, redirect_metadata=True, timeout=8
        )
        provenance.append(
            {
                k: response[k]
                for k in ["requested_at", "observed_at", "http_status"]
                if k in response
            }
        )
        if response.get("http_status", 200) != 200:
            if operation != "detail" or response.get("http_status") not in {
                301,
                302,
                303,
                307,
                308,
            }:
                raise SourceError("join_unqualified_resource_redirect")
            target = urljoin(current, response.get("location") or "")
            checked_url(target, "detail")
            if urlsplit(target).path.split("/")[2] != company:
                raise SourceError("join_redirect_changed_employer")
            hops.append({"from": current, "to": target, "http_status": response["http_status"]})
            current = target
            continue
        raw = response["body"]
        result = (
            inventory(raw, current)
            if operation == "inventory"
            else detail(raw, current, requested_url=url, redirects=hops)
        )
        result.update(
            provenance={
                "requested_at": provenance[0].get("requested_at"),
                "responses": provenance,
                "robots": policy_meta,
            },
            native_redirects=hops,
        )
        if os.environ.get("JOB_MARKET_CAPTURE_DIR"):
            folder = Path(os.environ["JOB_MARKET_CAPTURE_DIR"])
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / (hashlib.sha256(raw).hexdigest() + ".join-native")
            try:
                with path.open("xb") as f:
                    f.write(raw)
            except FileExistsError:
                pass
            result["private_raw_checkpoint"] = str(path)
        return result
    raise SourceError("join_redirect_limit")
