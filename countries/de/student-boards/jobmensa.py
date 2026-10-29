"""Original read-only public Jobmensa list/detail adapter. No account actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from lxml import html

ORIGIN = "https://www.jobmensa.de"
AGENT = "job-market-mcp/0.4.3"
MAX_BYTES = 5 * 1024 * 1024
QUERY_KEYS = {"categories", "location", "longitude", "latitude", "radius", "page"}
MODEL_CODES = {
    "apprenticeship",
    "dual_study",
    "holiday_job",
    "fsj",
    "mini_job",
    "internship",
    "scholar_job",
    "student_job",
    "studies",
    "part_time",
    "trainee_program",
    "full_time",
    "werkstudent",
}
LIMITS = [
    "A current source page or native terminal is not a frozen historical or nationwide census.",
    "Native categories may contain mixed or promoted contracts; inspect each actual model.",
    "Listing dates may be absent. Preserve detail datePosted, expiry and observation separately.",
    "Remote, hours and employmentType can conflict; no applicant fit is inferred.",
    "External apply links are returned only; no application, account, subscription or contact is started.",
]


def clean(value):
    return " ".join(value.split())


def checked_url(value, operation=None):
    u = urlsplit(value)
    if (
        u.scheme != "https"
        or u.netloc != "www.jobmensa.de"
        or u.username
        or u.password
        or u.fragment
    ):
        raise SourceError("Only the exact public HTTPS Jobmensa origin is supported")
    listing = u.path == "/jobs-suchen"
    detail = bool(re.fullmatch(r"/jobs/(?:ex|in)/[A-Za-z0-9][A-Za-z0-9-]*", u.path))
    if not listing and not detail:
        raise SourceError("Unsupported public list/detail path")
    if operation and ((operation == "page") != listing):
        raise SourceError("Path does not match the requested operation")
    query = parse_qs(u.query, keep_blank_values=True)
    if (
        not set(query) <= QUERY_KEYS
        or any(len(v) != 1 for v in query.values())
        or (detail and query)
    ):
        raise SourceError("Unknown, duplicate or career-keyword query fields are not inventory")
    if "page" in query and not re.fullmatch(r"[1-9][0-9]{0,5}", query["page"][0]):
        raise SourceError("Page must be a bounded positive source page")
    if "categories" in query and query["categories"][0] not in MODEL_CODES:
        raise SourceError("Only observed native contract-model categories are supported")
    return value


class SourceError(ValueError):
    pass


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if req is None:
            raise SourceError("Redirect lacks the original request context")
        previous, target = urlsplit(req.full_url), urlsplit(newurl)
        if previous.path == "/robots.txt":
            if newurl != ORIGIN + "/robots.txt":
                raise SourceError("Robots redirect requires separate policy verification")
        else:
            checked_url(newurl)
            if previous.path != target.path or parse_qs(previous.query) != parse_qs(target.query):
                raise SourceError("Redirect changes source identity or requested partition/page")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, *, with_url=False):
    request = Request(url, headers={"User-Agent": AGENT, "Accept": "text/html,text/plain"})
    with build_opener(SafeRedirect()).open(request, timeout=25) as response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise SourceError("Complete source exceeds the body bound; no truncated result")
        return (body, response.geturl()) if with_url else body


def capabilities():
    return {
        "source": "jobmensa",
        "status": "ok",
        "operations": ["page", "detail"],
        "origin": ORIGIN,
        "robots": ORIGIN + "/robots.txt",
        "auth": "anonymous_public_only",
        "allowed_query_fields": sorted(QUERY_KEYS),
        "role_keyword_inventory": False,
        "native_model_codes_observed_2026_10_29": sorted(MODEL_CODES),
        "private_capture_environment": "JOB_MARKET_CAPTURE_DIR",
        "limits": LIMITS,
        "coverage_complete": False,
        "reviewed_by_model": False,
    }


def _envelope(body, url, kind):
    return {
        "source": "jobmensa",
        "status": "ok",
        "kind": kind,
        "source_url": url,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_html_sha256": hashlib.sha256(body).hexdigest(),
        "coverage_complete": False,
        "reviewed_by_model": False,
        "limits": LIMITS,
    }


def parse_page(body, url):
    checked_url(url, "page")
    tree = html.fromstring(body)
    cards = tree.xpath(
        '//a[starts-with(@href,"/jobs/") or starts-with(@href,"https://www.jobmensa.de/jobs/")]'
    )
    counts = {
        int(match.group(1))
        for span in tree.xpath("//span")
        if (match := re.fullmatch(r"([0-9]+)\s+Jobs", clean(span.text_content())))
    }
    if len(counts) > 1:
        raise SourceError("Ambiguous native result counter")
    reported = next(iter(counts), None)
    if not cards and reported != 0:
        raise SourceError("Native cards/verified zero state absent; not successful empty supply")
    rows, seen = [], set()
    for card in cards:
        link = checked_url(urljoin(url, card.get("href", "")), "detail")
        if link in seen:
            raise SourceError("Duplicate native card identity requires source review")
        seen.add(link)
        headings = card.xpath(".//h2")
        if len(headings) != 1 or not clean(headings[0].text_content()):
            raise SourceError("Native card title absent")
        row = {
            "id": urlsplit(link).path,
            "url": link,
            "title": clean(headings[0].text_content()),
            "native_text": clean(" ".join(card.itertext())),
            "native_attributes": {
                k: v
                for k, v in card.attrib.items()
                if k in {"data-testid", "data-jobvalley-job", "data-promoted", "data-recommended"}
            },
            "original_published_at": None,
            "contract_model_verified": False,
            "body_complete": False,
            "location_text": None,
            "employer_text": None,
        }
        for icon, key in [("location-dot", "location_text"), ("building", "employer_text")]:
            paragraphs = card.xpath(f'.//p[.//*[@data-icon="{icon}"]]')
            if len(paragraphs) == 1:
                row[key] = clean(paragraphs[0].text_content())
        row["promoted_label_present"] = bool(re.search(r"\bEmpfohlen\b", row["native_text"]))
        rows.append(row)
    query = parse_qs(urlsplit(url).query)
    current = int(query.get("page", ["1"])[0])
    partition = {k: v for k, v in query.items() if k != "page"}
    pages = {}
    navigations = tree.xpath('//nav[@aria-label="Seitennummerierung"]')
    if len(navigations) > 1 or (reported is not None and reported > len(rows) and not navigations):
        raise SourceError("Native pagination control missing or ambiguous")
    for anchor in tree.xpath('//nav[@aria-label="Seitennummerierung"]//a[@href]'):
        candidate = urljoin(url, anchor.get("href"))
        u = urlsplit(candidate)
        # Client-only anchors do not change the requested server resource.
        candidate = urlunsplit((u.scheme, u.netloc, u.path, u.query, ""))
        if u.netloc != "www.jobmensa.de" or u.path != "/jobs-suchen":
            continue
        q = parse_qs(u.query)
        checked_url(candidate, "page")
        if {k: v for k, v in q.items() if k != "page"} != partition:
            raise SourceError("Native continuation changed the selected partition")
        pages[int(q.get("page", ["1"])[0])] = candidate
    later = sorted(p for p in pages if p > current)
    if later and later[0] != current + 1:
        raise SourceError("Native continuation has a page gap")
    next_url = pages[later[0]] if later else None
    result = _envelope(body, url, "jobmensa_listing_page")
    result.update(
        requested_query=query,
        returned_count=len(rows),
        listings=rows,
        reported_total=reported,
        pagination={
            "page": current,
            "native_page_links": pages,
            "next_url": next_url,
            "continuation_discovered": next_url is not None,
            "native_display_terminal_candidate": next_url is None,
            "historical_coverage_verified": False,
        },
    )
    return result


def _postings(value):
    if isinstance(value, list):
        return [item for v in value for item in _postings(v)]
    if not isinstance(value, dict):
        return []
    types = value.get("@type", [])
    if types == "JobPosting" or isinstance(types, list) and "JobPosting" in types:
        return [value]
    return _postings(value.get("@graph", []))


def parse_detail(body, url):
    checked_url(url, "detail")
    tree = html.fromstring(body)
    postings = []
    for script in tree.xpath('//script[@type="application/ld+json"]'):
        try:
            postings.extend(_postings(json.loads(script.text or "")))
        except json.JSONDecodeError:
            continue
    if (
        len(postings) != 1
        or not isinstance(postings[0].get("description"), str)
        or not postings[0]["description"]
    ):
        raise SourceError("One complete native JobPosting is required; no snippet fallback")
    job = postings[0]
    if not job.get("title"):
        raise SourceError("Native JobPosting title absent")
    description = html.fromstring("<div>" + job["description"] + "</div>").text_content()
    apply_links = []
    for a in tree.xpath("//a[@href]"):
        if "jetzt bewerben" in clean(a.text_content()).casefold():
            target = urljoin(url, a.get("href"))
            if urlsplit(target).scheme in {"https", "mailto"}:
                apply_links.append(target)
    result = _envelope(body, url, "jobmensa_job_detail")
    result.update(
        id=urlsplit(url).path,
        title=job["title"],
        description=description,
        description_html=job["description"],
        native_job_posting=job,
        original_source_date=job.get("datePosted"),
        valid_through=job.get("validThrough"),
        employment_type=job.get("employmentType"),
        work_hours=job.get("workHours"),
        worker_location_requirements=job.get("applicantLocationRequirements"),
        job_location_type=job.get("jobLocationType"),
        apply_urls=list(dict.fromkeys(apply_links)),
        source_body_untruncated=True,
        full_posting_reviewed=False,
        requirements_reconciled=False,
    )
    return result


def read(operation, url):
    checked_url(url, operation)
    robots_body = fetch(ORIGIN + "/robots.txt")
    policy = RobotFileParser()
    policy.parse(robots_body.decode("utf-8").splitlines())
    if not policy.can_fetch(AGENT, url):
        raise SourceError("Current robots policy denies this route; no page request made")
    body, actual_url = fetch(url, with_url=True)
    capture = os.environ.get("JOB_MARKET_CAPTURE_DIR")
    raw_path = None
    if capture:
        folder = Path(capture)
        folder.mkdir(parents=True, exist_ok=True)
        raw_path = folder / (hashlib.sha256(body).hexdigest() + ".html")
        if not raw_path.exists():
            try:
                with raw_path.open("xb") as handle:
                    handle.write(body)
            except FileExistsError:
                pass  # Another reader stored the same content-addressed response.
    result = (parse_page if operation == "page" else parse_detail)(body, actual_url)
    result.update(
        requested_url=url,
        robots_sha256=hashlib.sha256(robots_body).hexdigest(),
        private_raw_checkpoint=str(raw_path) if raw_path else None,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", choices=["page", "detail"])
    parser.add_argument("--url")
    parser.add_argument("--capabilities", action="store_true")
    args = parser.parse_args()
    try:
        result = capabilities() if args.capabilities else read(args.operation, args.url)
    except Exception as error:
        result = {
            "source": "jobmensa",
            "status": "source_limited",
            "coverage_complete": False,
            "reviewed_by_model": False,
            "returned_count": None,
            "error_type": type(error).__name__,
            "http_status": getattr(error, "code", None),
            "message": str(error)
            if isinstance(error, SourceError)
            else "Native policy, request or page validation failed; not zero supply.",
        }
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 2 if result["status"] != "ok" else 0


if __name__ == "__main__":
    raise SystemExit(main())
