"""Original read-only German public board contracts; no account or application actions."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import berlin
import englishjobs
import getinengineering
import jobware
import source_capture
import xing
import zenjob
from lxml import html
from native_flight import public_search_state

AGENT = "job-market-mcp/0.4.7"
MAX_BYTES = 8 * 1024 * 1024
ORIGINS = {
    name: "https://www." + host
    for name, host in {
        "absolventa": "absolventa.de",
        "academics": "academics.de",
        "stellenanzeigen": "stellenanzeigen.de",
        "yourfirm": "yourfirm.de",
        "bund_de": "service.bund.de",
    }.items()
}
ORIGINS["germantechjobs"] = "https://germantechjobs.de"
ORIGINS["jobs_de"] = "https://www.jobs.de"
ORIGINS["jobware"] = "https://www.jobware.de"
ORIGINS["englishjobs"] = englishjobs.ORIGIN
ORIGINS["berlinstartupjobs"] = berlin.ORIGIN
ORIGINS["xing"] = xing.ORIGIN
ORIGINS["getinengineering"] = getinengineering.ORIGIN
ORIGINS["zenjob"] = zenjob.ORIGIN
LIST_PATHS = {
    "getinengineering": "/jobsuche",
    "zenjob": "/de/jobboerse",
    "xing": "/jobs/k-student",
    "englishjobs": "/in/hessen",
    "berlinstartupjobs": "/",
    "jobware": "/jobsearch/sitemap/sitemap-advertisements.xml",
    "jobs_de": "/jobs",
    "absolventa": "/jobs",
    "academics": "/stellenanzeigen",
    "stellenanzeigen": "/jobs/",
    "yourfirm": "/stellenangebote/",
    "germantechjobs": "/api/jobsLight",
    "bund_de": "/Content/Globals/Functions/RSSFeed/RSSGenerator_Stellen.xml",
}
DETAILS = {
    "jobware": r"/job/[^/]+-([0-9]{9})",
    "jobs_de": r"/job/[^/]+-([1-9][0-9]*)",
    "absolventa": r"/stellenangebote/([1-9][0-9]*)-[^/]+",
    "academics": r"/jobs/[^/]+-([1-9][0-9]*)",
    "stellenanzeigen": r"/job/[^/]+?-((?:sde-)?[1-9][0-9]*)/",
    "yourfirm": r"/job/[^/]+/[^/]+/(yf-[1-9][0-9]*)/",
    "germantechjobs": r"/api/jobWithUrl/([^/]+)",
    "bund_de": r"/IMPORTE/Stellenangebote/(?:[^/?#;]+/)+([A-Za-z0-9][A-Za-z0-9_.-]*)\.html",
}
LIMITS = [
    "Code/source transport is not complete national or frozen-interval coverage.",
    "Site country, source role categories and remote labels do not establish worker eligibility or applicant fit.",
    "Moving pages, original campaign clocks, renewal clocks and observation clocks remain distinct.",
    "Full source bodies can still require comparison with the original employer and actual required documents.",
    "No login, apply, account, save, favourite, subscription, email or contact action is supported.",
]


class SourceError(ValueError):
    pass


def clean(value):
    return " ".join(value.split())


def without_session(value):
    return re.sub(r';jsessionid=[^/?#;\s"<>]+', "", value, flags=re.I)


def checked_url(source, url, operation):
    if source not in ORIGINS:
        raise SourceError("Unsupported public source")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != urlsplit(ORIGINS[source]).netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
        or ";" in parsed.path
    ):
        raise SourceError("Exact public HTTPS origin without account/session markers required")
    path = unquote(parsed.path)
    if "%" in path or any(ord(c) < 32 for c in path):
        raise SourceError("Ambiguous encoded route")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if any(len(v) != 1 for v in query.values()):
        raise SourceError("Ambiguous duplicate source query")
    if source == "englishjobs":
        return englishjobs.checked_url(url, operation)
    if source == "berlinstartupjobs":
        return berlin.checked_url(url, operation)
    if source == "xing":
        return xing.checked_url(url, operation)
    if source in {"getinengineering", "zenjob"}:
        return (getinengineering if source == "getinengineering" else zenjob).checked_url(
            url, operation
        )
    if operation == "inventory":
        if path != LIST_PATHS[source]:
            raise SourceError("Only the observed unfiltered inventory path is supported")
        allowed = (
            {"nn"}
            if source == "bund_de"
            else set()
            if source in {"germantechjobs", "jobware"}
            else {"page"}
        )
        if not set(query) <= allowed:
            raise SourceError("Unknown or career-keyword inventory fields refused")
        if "page" in query and not re.fullmatch(r"[1-9][0-9]{0,5}", query["page"][0]):
            raise SourceError("Invalid native page")
        if "nn" in query and query["nn"] != ["4641956"]:
            raise SourceError("Unverified feed navigation parameter")
    elif operation == "detail":
        if query or not re.fullmatch(DETAILS[source], path, re.I):
            raise SourceError("Only an exact native public detail route is supported")
    else:
        raise SourceError("Unsupported read operation")
    return url


def identity(source, url):
    if source == "xing":
        return xing.native_id(url)
    if source in {"getinengineering", "zenjob"}:
        return (getinengineering if source == "getinengineering" else zenjob).native_id(url)
    match = re.fullmatch(DETAILS[source], unquote(urlsplit(url).path), re.I)
    if not match:
        raise SourceError("Native detail identity absent")
    if source == "bund_de":
        return unquote(
            urlsplit(url).path
        )  # Provider/path namespace prevents numeric ID collisions.
    return match[1].upper() if source in {"stellenanzeigen", "yourfirm"} else match[1]


class SafeRedirect(HTTPRedirectHandler):
    def __init__(self, source, operation, initial, policy=None):
        super().__init__()
        self.source, self.operation, self.initial, self.policy = source, operation, initial, policy

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if self.operation == "robots":
            if newurl != ORIGINS[self.source] + "/robots.txt":
                raise SourceError("Robots canonical origin requires separate verification")
        else:
            checked_url(self.source, newurl, self.operation)
            if self.operation == "detail":
                if identity(self.source, newurl) != identity(self.source, self.initial):
                    raise SourceError("Redirect changes vacancy identity")
            elif urlsplit(newurl).path != urlsplit(self.initial).path or parse_qs(
                urlsplit(newurl).query
            ) != parse_qs(urlsplit(self.initial).query):
                raise SourceError("Redirect changes inventory partition/page")
            if self.policy is None or not self.policy.can_fetch(AGENT, newurl):
                raise SourceError("Redirect target is denied or has no checked policy")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(source, url, operation, policy=None):
    headers = {
        "User-Agent": AGENT,
        "Accept": "text/html,application/json,application/rss+xml,text/plain",
    }
    if source == "getinengineering" and urlsplit(url).path == getinengineering.API_PATH:
        # Required by this published anonymous openV2 client. No credentials,
        # browser impersonation or inherited insecure TLS configuration.
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = Request(
        url,
        headers=headers,
    )
    with build_opener(SafeRedirect(source, operation, url, policy)).open(
        request, timeout=25
    ) as response:
        if response.status != 200:
            raise SourceError("A complete200 response is required, never a partial/empty transport")
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise SourceError("Full source exceeds bound; no truncated response")
        if source == "xing" and urlsplit(url).path.endswith(".xml.gz") and body[:2] == b"\x1f\x8b":
            body = gzip.GzipFile(fileobj=BytesIO(body)).read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise SourceError("Full decompressed native resource exceeds bound; no clipping")
        return body, response.geturl()


def envelope(source, body, url, kind):
    return {
        "source": source,
        "status": "ok",
        "kind": kind,
        "source_url": url,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "coverage_complete": False,
        "reviewed_by_model": False,
        "limits": LIMITS,
    }


def card(source, url, title, **extra):
    checked_url(source, url, "detail")
    return {
        "id": identity(source, url),
        "url": url,
        "title": title,
        "original_source_date": None,
        "source_body_complete": False,
        "applicant_fit_assessed": False,
        **extra,
    }


def static_page(source, body, url):
    tree = html.fromstring(body)
    page = int(parse_qs(urlsplit(url).query).get("page", ["1"])[0])
    if source == "absolventa":
        anchors = tree.xpath('//a[@data-job-offer-target="jobOfferTeaser"]')
        navigations = tree.xpath('//nav[@aria-label="Mobile Pagination"]')
        active = {
            clean(e.text_content())
            for nav in navigations
            for e in nav.xpath("./span")
            if clean(e.text_content()).isdecimal()
        }
    else:
        anchors = tree.xpath('//a[@data-stm-job-id and starts-with(@id,"job-")]')
        navigations = tree.xpath('//a[starts-with(@id,"job-teasers-select-page-")]/..')
        active = {
            clean(e.text_content())
            for e in tree.xpath(
                '//a[starts-with(@id,"job-teasers-select-page-") and contains(@class,"underline")]'
            )
        }
    if active != {str(page)}:
        raise SourceError("Native active page missing or different from request")
    rows = []
    for anchor in anchors:
        target = urljoin(url, anchor.get("href", ""))
        headings = list(dict.fromkeys(clean(e.text_content()) for e in anchor.xpath(".//h2|.//h3")))
        title = anchor.get("title") or (headings[0] if len(headings) == 1 else None)
        if not title:
            raise SourceError("Native card title missing or ambiguous")
        row = card(
            source,
            target,
            clean(title),
            native_card_text=clean(anchor.text_content()),
            native_card_id=anchor.get("id"),
        )
        rows.append(row)
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise SourceError("No verified primary cards or duplicate native identity")
    links = {}
    for nav in navigations:
        for anchor in nav.xpath(".//a[@href]"):
            target = urljoin(url, anchor.get("href"))
            checked_url(source, target, "inventory")
            number = int(parse_qs(urlsplit(target).query).get("page", ["1"])[0])
            if number in links and links[number] != target:
                raise SourceError("Conflicting native continuation URLs")
            links[number] = target
    later = sorted(n for n in links if n > page)
    if later and later[0] != page + 1:
        raise SourceError("Native page gap")
    result = envelope(source, body, url, "german_public_board_page")
    result.update(
        listings=rows,
        returned_count=len(rows),
        reported_total=None,
        pagination={
            "page": page,
            "native_page_links": links,
            "next_url": links[later[0]] if later else None,
            "continuation_basis": "actual native pagination links",
            "historical_coverage_verified": False,
        },
    )
    return result


def flight_page(source, body, url):
    state = public_search_state(body)
    query = state["searchQuery"]["query"]
    params = state["currentPageParams"]["pageParams"]["searchParams"]
    requested_page = int(parse_qs(urlsplit(url).query).get("page", ["1"])[0])
    actual = int(query.get("page", 1))
    limit = params.get("limit")
    offset = params.get("offset")
    if (
        actual != requested_page
        or not isinstance(limit, int)
        or limit <= 0
        or offset != (actual - 1) * limit
    ):
        raise SourceError("Native page/limit/offset differs from requested inventory")
    if query.get("fulltext") or query.get("locationIds") or query.get("onlyTopJobs"):
        raise SourceError("Native source unexpectedly narrowed the unfiltered inventory")
    if query.get("portal") != {"stellenanzeigen": "stanz", "yourfirm": "yourfirm"}[source]:
        raise SourceError("Native source portal differs from the requested source")
    models = []
    for response in state["api"]["queries"].values():
        data = response.get("data", {}).get("requests", {}).get("jobSearchResult", {})
        if isinstance(data, dict) and isinstance(data.get("jobAdSearchResultModel"), dict):
            models.append(data["jobAdSearchResultModel"])
    if len(models) != 1:
        raise SourceError("One complete native search result required")
    model = models[0]
    jobs = model.get("jobAds")
    total = model.get("count")
    if (
        not isinstance(jobs, list)
        or not jobs
        or not isinstance(total, int)
        or total < offset + len(jobs)
    ):
        raise SourceError("Native result/cardinality/total is unresolved")
    tree = html.fromstring(body)
    cards = tree.xpath("//*[@data-jobid]")
    by_id = {e.get("data-jobid").upper(): e for e in cards}
    if len(cards) != len(by_id) or len(cards) != len(jobs):
        raise SourceError("Native metadata and visible primary-card counts disagree")
    if offset + len(jobs) < total and len(jobs) != limit:
        raise SourceError("Short native page contradicts its continuation count")
    rows = []
    for entry in jobs:
        job = entry.get("jobAd")
        if not isinstance(job, dict) or not job.get("id") or str(job["id"]).upper() not in by_id:
            raise SourceError("Native card/reference identity missing")
        node = by_id[str(job["id"]).upper()]
        anchors = node.xpath('.//a[@data-testid="qa-hitzone"]')
        if len(anchors) != 1:
            raise SourceError("One native primary-card link required")
        anchor = anchors[0]
        target = urljoin(url, anchor.get("href", ""))
        row = card(
            source,
            target,
            anchor.get("title"),
            native_card_id=job["id"],
            native_source_record=job,
            native_search_record=entry,
            native_card_text=clean(node.text_content()),
            native_clock_fields={
                k: job.get(k) for k in ["originalStartDate", "startDate", "expirationDate"]
            },
        )
        if row["id"] != str(job["id"]).upper() or not row["title"]:
            raise SourceError("Canonical native URL/card identity differs")
        rows.append(row)
    result = envelope(source, body, url, "german_public_board_page")
    result.update(
        listings=rows,
        returned_count=len(rows),
        reported_total=total,
        reported_relevant_total=model.get("countRelevant"),
        native_default_filters={
            key: query.get(key)
            for key in [
                "portal",
                "backfillTypes",
                "contractType",
                "employmentType",
                "homeOfficeType",
                "onlyTopJobs",
                "locationIds",
                "sort",
                "limit",
                "page",
            ]
        },
        pagination={
            "page": actual,
            "offset": offset,
            "limit": limit,
            "native_page_links": {},
            "next_url": ORIGINS[source] + LIST_PATHS[source] + "?" + urlencode({"page": actual + 1})
            if offset + len(rows) < total
            else None,
            "continuation_unresolved": False,
            "next_url_is_provider_emitted_href": False,
            "continuation_basis": "Verified native numeric page/limit/offset/count contract; next URL derived from that contract. Actual pages1,2,3 verified separately; not a provider-emitted next href.",
            "historical_coverage_verified": False,
        },
    )
    return result


def next_page_props(body):
    tree = html.fromstring(body)
    scripts = tree.xpath('//script[@id="__NEXT_DATA__"]')
    if len(scripts) != 1:
        raise SourceError("One complete native Next data record is required")
    props = json.loads(scripts[0].text or "").get("props", {}).get("pageProps", {})
    if not isinstance(props, dict) or props.get("error") or props.get("loading"):
        raise SourceError("Native page data is absent, failed or still loading")
    return props


def jobs_de_inventory(body, url):
    props = next_page_props(body)
    jobs = props.get("data", {}).get("jobs")
    root_query = props.get("__APOLLO_STATE__", {}).get("ROOT_QUERY", {})
    keys = [key for key in root_query if key.startswith("jobs(") and key.endswith(")")]
    if len(keys) != 1 or not isinstance(jobs, dict):
        raise SourceError("One complete native jobs/range response is required")
    request = json.loads(keys[0][5:-1])
    groups = request.get("condition_group", {})
    if (
        groups.get("conjunction") != "AND"
        or groups.get("groups") != []
        or request.get("fulltext", {}).get("keys")
    ):
        raise SourceError("Native inventory was narrowed by conditions or a keyword")
    page = int(parse_qs(urlsplit(url).query).get("page", ["1"])[0])
    ranges = request.get("ranges", {})
    first, size = ranges.get("first"), ranges.get("last")
    if not isinstance(size, int) or size <= 0 or first != (page - 1) * size:
        raise SourceError("Native range differs from requested numeric page")
    records, total = jobs.get("pages"), jobs.get("result_count")
    if (
        not isinstance(records, list)
        or not records
        or not isinstance(total, int)
        or total < first + len(records)
    ):
        raise SourceError("Native result count/range is unverified, never empty success")
    if first + len(records) < total and len(records) != size:
        raise SourceError("Native short page contradicts its continuation count")
    rows = []
    for job in records:
        if (
            not isinstance(job, dict)
            or not job.get("id")
            or not job.get("urlNoPrefix")
            or not job.get("title")
        ):
            raise SourceError("Native metadata identity/title/link is missing")
        target = urljoin(url, job["urlNoPrefix"])
        row = card(
            "jobs_de",
            target,
            job["title"],
            native_source_record=job,
            native_clock_fields={
                key: job.get(key) for key in ["published", "formattedPublished", "expiration"]
            },
        )
        if row["id"] != str(job["id"]):
            raise SourceError("Native metadata identity differs from public URL")
        rows.append(row)
    if len({row["id"] for row in rows}) != len(rows):
        raise SourceError("Duplicate native metadata identity")
    result = envelope("jobs_de", body, url, "german_public_board_page")
    result.update(
        listings=rows,
        returned_count=len(rows),
        reported_total=total,
        native_default_filters={
            "condition_group": groups,
            "fulltext": request.get("fulltext"),
            "language": request.get("language"),
        },
        pagination={
            "page": page,
            "offset": first,
            "limit": size,
            "next_url": ORIGINS["jobs_de"] + "/jobs?" + urlencode({"page": page + 1})
            if first + len(rows) < total
            else None,
            "next_url_is_provider_emitted_href": False,
            "continuation_basis": "Native frontend numeric page formula plus independently checked native first/last ranges; last is count, not end offset.",
            "historical_coverage_verified": False,
        },
    )
    return result


def jobs_de_detail(body, url):
    props = next_page_props(body)
    job = props.get("data", {}).get("jobByPath", {}).get("content")
    if (
        not isinstance(job, dict)
        or str(job.get("id")) != identity("jobs_de", url)
        or not job.get("description")
    ):
        raise SourceError("Complete native detail identity/body is missing")
    raw = job["description"]
    if not isinstance(raw, str) or not raw.strip():
        raise SourceError("No complete native body; no snippet fallback")
    text = clean(html.fromstring(raw).text_content())
    structured = []
    for script in html.fromstring(body).xpath('//script[@type="application/ld+json"]'):
        try:
            structured.extend(postings(json.loads(script.text or "")))
        except ValueError:
            continue
    if len(structured) > 1:
        raise SourceError("Ambiguous native structured job records")
    result = envelope("jobs_de", body, url, "german_public_board_detail")
    result.update(
        id=str(job["id"]),
        title=job.get("title"),
        native_job=job,
        native_job_posting=structured[0] if structured else None,
        native_structured_job_present=bool(structured),
        description=text,
        description_html=raw,
        native_body_fields={
            key: job.get(key)
            for key in [
                "applicationRequireCv",
                "applicationRequireCoverLetter",
                "applicationRequireQualifyingQuestions",
                "applicationQualifyingQuestions",
                "formattedOriginalPublished",
                "published",
            ]
        },
        original_source_date=None,
        source_body_untruncated=True,
        full_posting_reviewed=False,
        requirements_completeness_verified=False,
    )
    return result


def tech_inventory(body, url):
    jobs = json.loads(body)
    if not isinstance(jobs, list) or not jobs:
        raise SourceError("A nonempty complete native metadata array is required")
    rows = []
    seen = set()
    for job in jobs:
        if (
            not isinstance(job, dict)
            or not job.get("_id")
            or not job.get("jobUrl")
            or job["_id"] in seen
        ):
            raise SourceError("Native API identity missing or duplicated")
        seen.add(job["_id"])
        target = ORIGINS["germantechjobs"] + "/api/jobWithUrl/" + job["jobUrl"]
        rows.append(
            {
                "id": str(job["_id"]),
                "url": target,
                "public_job_url": ORIGINS["germantechjobs"] + "/jobs/" + job["jobUrl"],
                "title": job.get("name"),
                "native_source_record": job,
                "source_body_complete": False,
                "original_source_date": None,
                "activation_clock": job.get("activeFrom"),
                "applicant_fit_assessed": False,
            }
        )
        checked_url("germantechjobs", target, "detail")
    result = envelope("germantechjobs", body, url, "german_public_board_page")
    result.update(
        listings=rows,
        returned_count=len(rows),
        reported_total=None,
        pagination={
            "native_whole_array_response": True,
            "next_url": None,
            "historical_coverage_verified": False,
        },
    )
    return result


def bund_feed(body, url):
    root = ElementTree.fromstring(body)
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise SourceError("One official native RSS channel required")
    rows = []
    for item in channel.findall("item"):
        native_target = without_session(item.findtext("link") or "")
        target_parts = urlsplit(native_target)
        target = urlunsplit(
            (target_parts.scheme, target_parts.netloc, target_parts.path, target_parts.query, "")
        )
        title = item.findtext("title")
        guid = without_session(item.findtext("guid") or "")
        row = {
            "id": guid or target,
            "url": target,
            "title": title,
            "metadata_verification_required": not bool(title),
            "native_client_fragment_removed": bool(target_parts.fragment),
            "description_snippet": without_session(item.findtext("description") or ""),
            "source_feed_publication_raw": item.findtext("pubDate"),
            "native_guid": guid,
            "source_body_complete": False,
            "applicant_fit_assessed": False,
            "original_source_date": None,
            "native_detail_url": None,
            "body_route_status": "original_source_resolution_required",
        }
        try:
            checked_url("bund_de", target, "detail")
            row.update(
                id=identity("bund_de", target),
                native_detail_url=target,
                body_route_status="native_detail_route",
            )
        except SourceError:
            pass  # Retain actual metadata when a native body route needs separate verification.
        try:
            row["source_feed_publication"] = parsedate_to_datetime(
                item.findtext("pubDate")
            ).isoformat()
        except (TypeError, ValueError):
            row["source_feed_publication"] = None
        rows.append(row)
    if not rows:
        raise SourceError("Native feed empty state has not been verified")
    result = envelope("bund_de", body, url, "german_public_board_page")
    result.update(
        listings=rows,
        returned_count=len(rows),
        reported_total=None,
        pagination={
            "next_url": None,
            "feed_snapshot_count": len(rows),
            "retention_or_history_cap_unresolved": True,
            "historical_coverage_verified": False,
        },
    )
    return result


def postings(value):
    if isinstance(value, list):
        for item in value:
            yield from postings(item)
    elif isinstance(value, dict):
        if value.get("@type") == "JobPosting":
            yield value
        if "@graph" in value:
            yield from postings(value["@graph"])


def parse_detail(source, body, url):
    checked_url(source, url, "detail")
    if source in {"getinengineering", "zenjob"}:
        result = envelope(source, body, url, "german_public_board_detail")
        result.update(
            (getinengineering if source == "getinengineering" else zenjob).detail(body, url)
        )
        return result
    if source == "xing":
        result = envelope(source, body, url, "german_public_board_detail")
        result.update(xing.detail(body, url))
        return result
    if source == "berlinstartupjobs":
        result = envelope(source, body, url, "german_public_board_detail")
        result.update(berlin.detail(body, url))
        return result
    if source == "jobware":
        raise SourceError(
            "The full native iframe and its independently checked policy are required"
        )
    if source == "jobs_de":
        return jobs_de_detail(body, url)
    if source == "germantechjobs":
        job = json.loads(body)
        if (
            not isinstance(job, dict)
            or not job.get("_id")
            or job.get("jobUrl") != identity(source, url)
        ):
            raise SourceError("Native API detail identity differs from requested jobUrl")
        fields = {
            key: job.get(key)
            for key in [
                "description",
                "requirementsMustTextArea",
                "requirementsNiceTextArea",
                "responsibilitiesTextArea",
            ]
        }
        if not any(isinstance(value, str) and value.strip() for value in fields.values()):
            raise SourceError("Native full detail fields missing; no snippet fallback")
        result = envelope(source, body, url, "german_public_board_detail")
        result.update(
            id=str(job["_id"]),
            title=job.get("name"),
            native_job=job,
            native_body_fields=fields,
            description="\n\n".join(
                key + "\n" + value
                for key, value in fields.items()
                if isinstance(value, str) and value.strip()
            ),
            source_body_untruncated=True,
            full_posting_reviewed=False,
            requirements_completeness_verified=False,
        )
        return result
    tree = html.fromstring(body)
    selectors = {
        "absolventa": '//*[@id="internal-job-offer"]',
        "academics": '//*[@id="job-ad-content"]',
        "stellenanzeigen": '//*[@id="job-ad-details-widget"]',
        "yourfirm": '//*[@id="job-ad-details-widget"]',
        "bund_de": '//*[@id="main"]',
    }
    containers = tree.xpath(selectors[source])
    if len(containers) != 1 or not clean(containers[0].text_content()):
        raise SourceError("One complete native body container required")
    native = []
    for script in tree.xpath('//script[@type="application/ld+json"]'):
        try:
            native.extend(postings(json.loads(script.text or "")))
        except ValueError:
            continue
    if source != "bund_de" and len(native) != 1:
        raise SourceError("One native JobPosting required alongside complete visible body")
    container = containers[0]
    body_text = without_session(clean(container.text_content()))
    result = envelope(source, body, url, "german_public_board_detail")
    result.update(
        id=identity(source, url),
        title=native[0].get("title") if native else None,
        native_job_posting=native[0] if native else None,
        native_heading_texts=list(
            dict.fromkeys(clean(e.text_content()) for e in tree.xpath("//h1"))
        ),
        description=body_text,
        description_html=without_session(html.tostring(container, encoding="unicode")),
        source_body_untruncated=True,
        full_posting_reviewed=False,
        requirements_completeness_verified=False,
    )
    return result


def parse_inventory(source, body, url):
    checked_url(source, url, "inventory")
    if source in {"getinengineering", "zenjob"}:
        result = envelope(source, body, url, "german_public_board_page")
        result.update(
            (getinengineering if source == "getinengineering" else zenjob).inventory(body, url)
        )
        return result
    if source == "xing":
        result = envelope(source, body, url, "german_public_board_page")
        result.update(xing.inventory(body, url))
        return result
    if source in {"englishjobs", "berlinstartupjobs"}:
        result = envelope(source, body, url, "german_public_board_page")
        result.update((englishjobs if source == "englishjobs" else berlin).inventory(body, url))
        return result
    if source == "jobware":
        result = envelope(source, body, url, "german_public_board_page")
        result.update(jobware.inventory(body))
        return result
    if source == "jobs_de":
        return jobs_de_inventory(body, url)
    if source in {"absolventa", "academics"}:
        return static_page(source, body, url)
    if source in {"stellenanzeigen", "yourfirm"}:
        return flight_page(source, body, url)
    if source == "germantechjobs":
        return tech_inventory(body, url)
    return bund_feed(body, url)


def read(source, operation, url):
    checked_url(source, url, operation)
    robots, _ = fetch(source, ORIGINS[source] + "/robots.txt", "robots")
    policy = RobotFileParser()
    policy.parse(robots.decode("utf-8").splitlines())
    if not policy.can_fetch(AGENT, url):
        raise SourceError("Current robots denies this route; no resource request performed")
    body, actual = fetch(source, url, operation, policy)
    capture = None
    if os.environ.get("JOB_MARKET_CAPTURE_DIR"):
        folder = Path(os.environ["JOB_MARKET_CAPTURE_DIR"])
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (hashlib.sha256(body).hexdigest() + ".native")
        try:
            with path.open("xb") as handle:
                handle.write(body)
        except FileExistsError:
            pass
        capture = str(path)
    if source == "englishjobs":
        result = envelope(source, body, actual, "german_public_board_page")
        result.update(englishjobs.inventory(body, actual, policy, AGENT))
    elif source == "jobware" and operation == "detail":
        embedded_url = jobware.embedded_url(body, actual)
        embedded_robots, _ = fetch(source, ORIGINS[source] + "/robots.txt", "robots")
        embedded_policy = RobotFileParser()
        embedded_policy.parse(embedded_robots.decode("utf-8").splitlines())
        if not embedded_policy.can_fetch(AGENT, embedded_url):
            raise SourceError(
                "Current robots denies the native iframe; no embedded request performed"
            )
        embedded_body, embedded_actual = fetch(source, embedded_url, "embedded", embedded_policy)
        result = envelope(source, body, actual, "german_public_board_detail")
        result.update(jobware.detail(body, actual, embedded_body, embedded_actual))
        result["embedded_robots_sha256"] = hashlib.sha256(embedded_robots).hexdigest()
    else:
        result = (parse_inventory if operation == "inventory" else parse_detail)(
            source, body, actual
        )
    result.update(
        requested_url=url,
        robots_sha256=hashlib.sha256(robots).hexdigest(),
        private_raw_checkpoint=capture,
    )
    if (
        result.get("kind") == "source_uri_discovery"
        and len(json.dumps(result, ensure_ascii=False).encode()) > 2 * 1024 * 1024
    ):
        manifest = source_capture.record_capture(result)
        manifest.update(
            observed_at=result["observed_at"],
            requested_url=url,
            robots_sha256=result["robots_sha256"],
            native_sitemap_kind=result["native_sitemap_kind"],
        )
        return manifest
    return result


def capabilities():
    return {
        "status": "ok",
        "sources": list(ORIGINS),
        "origins": ORIGINS,
        "inventory_paths": LIST_PATHS,
        "operations": ["inventory", "detail"],
        "limits": LIMITS,
        "coverage_complete": False,
        "numeric_page_contract": ["stellenanzeigen", "yourfirm", "jobs_de", "getinengineering"],
        "operations_by_source": {
            source: ["inventory"] if source == "englishjobs" else ["inventory", "detail"]
            for source in ORIGINS
        },
        "native_partition_discovery": {
            "getinengineering": "Whole SSR first39 records; native published openV2 GET search client provides start=0/39/78 with limit39 and required X-Requested-With protocol header. SSR start query resets and is not continuation. No role/degree filters or restricted API calls.",
            "zenjob": "Whole public shift lists and actual page links. Native shift starts, structured publication dates and contract type differ; student shift supply is not automatically a working-student contract. Full visible notes beyond structured description retained. Filter POST/signup/app actions unsupported.",
            "berlinstartupjobs": "Read the root category catalogue, then every category and native continuation; homepage featured cards are incomplete.",
            "englishjobs": {
                "states": [englishjobs.ORIGIN + "/in/" + state for state in englishjobs.STATES],
                "native_themes": ["/jobs/student", "/jobs/remote"],
                "body_access": "No implemented full-body route. Signed redirects are not emitted or bypassed; independent original-employer resolution remains necessary.",
            },
        },
        "feed_history_cap": ["bund_de"],
        "source_uri_consumer_segments": {
            "private_directory_env": "JOB_MARKET_CAPTURE_DIR",
            "segment_size": 1000,
            "native_pagination": False,
            "uri_counts_are_current_jobs": False,
        },
        "reviewed_by_model": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=list(ORIGINS))
    parser.add_argument("--operation", choices=["inventory", "detail"])
    parser.add_argument("--url")
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--capture-id")
    parser.add_argument("--segment-index", type=int, default=0)
    args = parser.parse_args()
    try:
        result = (
            source_capture.read_segment(args.capture_id, args.segment_index)
            if args.capture_id
            else capabilities()
            if args.capabilities
            else read(args.source, args.operation, args.url)
        )
    except Exception as error:
        result = {
            "source": args.source,
            "status": "source_limited",
            "returned_count": None,
            "coverage_complete": False,
            "reviewed_by_model": False,
            "error_type": type(error).__name__,
            "http_status": error.code if isinstance(error, HTTPError) else None,
            "exact_native_detail_gone": isinstance(error, HTTPError)
            and error.code == 410
            and args.operation == "detail",
            "retry_after": error.headers.get("Retry-After")
            if isinstance(error, HTTPError) and error.headers
            else None,
            "message": str(error)
            if isinstance(
                error,
                (
                    SourceError,
                    xing.XingError,
                    getinengineering.EngineeringError,
                    zenjob.ZenjobError,
                    source_capture.CaptureError,
                ),
            )
            else "Native source unavailable, changed or incomplete; no partial/empty success.",
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
