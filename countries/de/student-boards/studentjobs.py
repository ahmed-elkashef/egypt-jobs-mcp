"""Original public StudentJob/YoungCapital Germany reader; no account actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from jobmensa import SourceError, _postings, clean
from lxml import html

ORIGINS = {"studentjob": "https://www.studentjob.de", "youngcapital": "https://www.youngcapital.de"}
AGENT = "job-market-mcp/0.4.3"
MAX_BYTES = 5 * 1024 * 1024
MODEL_KEY = "search[job_types][id][]"
MODEL_IDS = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "14"}
LIMITS = [
    "Public Germany-market pages include foreign jobs; site country is not worksite or worker eligibility.",
    "Native work-model facets include mixed and survey adverts; full-description review remains required.",
    "JSON-LD contract and identifier fields can contradict native page facts. Numeric listing URL ID is the source identity.",
    "Moving pages and native last-page links do not establish frozen historical coverage.",
    "No apply, login, save, favourite, account, email, subscription or candidate-profile action is performed.",
]


def checked_url(source, value, operation=None):
    if source not in ORIGINS:
        raise SourceError("Unsupported source")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc != urlsplit(ORIGINS[source]).netloc
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise SourceError("Exact public source origin required")
    path = unquote(parsed.path)
    if "%" in path or any(ord(c) < 32 for c in path):
        raise SourceError("Encoded route ambiguity is unsupported")
    listing = path == "/stellenangebote"
    detail = re.fullmatch(r"/stellenangebote/([1-9][0-9]*)-[^/]+", path)
    if not listing and not detail:
        raise SourceError("Only native public vacancy list/detail paths are supported")
    if operation and ((operation == "page") != listing):
        raise SourceError("URL does not match the requested operation")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if not set(query) <= {"page", "sort_by", MODEL_KEY} or (detail and query):
        raise SourceError("Unknown or career-keyword query fields are not inventory")
    if any(len(v) != 1 for k, v in query.items() if k != MODEL_KEY):
        raise SourceError("Ambiguous duplicate scalar query fields")
    if "page" in query and not re.fullmatch(r"[1-9][0-9]{0,5}", query["page"][0]):
        raise SourceError("Invalid native page")
    if "sort_by" in query and query["sort_by"][0] not in {"relevancy", "published_date"}:
        raise SourceError("Unsupported native sort")
    if MODEL_KEY in query and (
        len(query[MODEL_KEY]) != len(set(query[MODEL_KEY]))
        or not set(query[MODEL_KEY]) <= MODEL_IDS
    ):
        raise SourceError("Unknown or duplicate native model IDs")
    return value


def partition(url):
    query = parse_qs(urlsplit(url).query, keep_blank_values=True)
    return {k: sorted(v) for k, v in query.items() if k != "page"}


def native_id(url):
    return re.fullmatch(r"/stellenangebote/([1-9][0-9]*)-[^/]+", unquote(urlsplit(url).path))[1]


class SafeRedirect(HTTPRedirectHandler):
    def __init__(self, source, initial, operation):
        super().__init__()
        self.source, self.initial, self.operation = source, initial, operation

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if self.operation == "robots":
            if newurl != ORIGINS[self.source] + "/robots.txt":
                raise SourceError("Robots redirect requires separate policy verification")
        else:
            checked_url(self.source, newurl, self.operation)
            if self.operation == "detail":
                if native_id(newurl) != native_id(self.initial):
                    raise SourceError("Redirect changes native vacancy identity")
            elif partition(newurl) != partition(self.initial) or parse_qs(
                urlsplit(newurl).query
            ).get("page", ["1"]) != parse_qs(urlsplit(self.initial).query).get("page", ["1"]):
                raise SourceError("Redirect changes requested inventory partition/page")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(source, url, operation):
    request = Request(url, headers={"User-Agent": AGENT, "Accept": "text/html,text/plain"})
    with build_opener(SafeRedirect(source, url, operation)).open(request, timeout=25) as response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise SourceError("Native body exceeds bound; no truncated response")
        return body, response.geturl()


def envelope(source, body, url, kind):
    return {
        "source": source,
        "status": "ok",
        "kind": kind,
        "source_url": url,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_html_sha256": hashlib.sha256(body).hexdigest(),
        "coverage_complete": False,
        "reviewed_by_model": False,
        "limits": LIMITS,
    }


def parse_page(source, body, url):
    checked_url(source, url, "page")
    tree = html.fromstring(body)
    query = parse_qs(urlsplit(url).query)
    requested_page = int(query.get("page", ["1"])[0])
    controls = tree.xpath('//ul[contains(concat(" ",normalize-space(@class)," ")," pagination ")]')
    active = {
        clean(e.text_content())
        for nav in controls
        for e in nav.xpath('.//li[contains(concat(" ",normalize-space(@class)," ")," -active ")]')
    }
    if active != {str(requested_page)}:
        raise SourceError("Native active page missing or differs from request")
    taxonomy = {}
    checked = set()
    for node in tree.xpath('//form[@action="/stellenangebote"]//input[@type="checkbox"]'):
        if node.get("name") != MODEL_KEY:
            continue
        label = clean(
            " ".join(tree.xpath("//label[@for=$target]//text()", target=node.get("id", "")))
        )
        value = node.get("value")
        if not value or not label:
            raise SourceError("Native model control lacks ID or label")
        if value in taxonomy and taxonomy[value] != label:
            raise SourceError("Conflicting native model labels")
        taxonomy[value] = label
        if node.get("checked") is not None:
            checked.add(value)
    if checked != set(query.get(MODEL_KEY, [])):
        raise SourceError("Native selected model controls differ from requested partition")
    sorts = {o.get("value") for o in tree.xpath('//select[@name="sort_by"]//option[@selected]')}
    requested_sort = query.get("sort_by", ["relevancy"])[0]
    if (sorts or "sort_by" in query) and sorts != {requested_sort}:
        raise SourceError("Native sort differs from requested sort")
    cards = tree.xpath(
        '//a[@data-job-opening-id][contains(concat(" ",normalize-space(@class)," ")," job-opening__item ")]'
    )
    if not cards:
        raise SourceError("No primary native cards; empty-market state is not verified")
    rows, seen = [], set()
    for card in cards:
        target = urljoin(url, card.get("href", ""))
        parsed = urlsplit(target)
        if (
            parsed.scheme != "https"
            or parsed.netloc != urlsplit(ORIGINS[source]).netloc
            or parsed.query
            or parsed.fragment
        ):
            raise SourceError("Native card link has an unsupported origin or query")
        external = re.fullmatch(
            r"/vacatures/([1-9][0-9]*)-[^/]+/redirect_to_external", unquote(parsed.path)
        )
        if external:
            identity = external[1]
        else:
            checked_url(source, target, "detail")
            identity = native_id(target)
        if identity != card.get("data-job-opening-id") or identity in seen:
            raise SourceError("Native card identity mismatch or duplicate primary card")
        seen.add(identity)
        headings = card.xpath(".//h3")
        if len(headings) != 1 or not clean(headings[0].text_content()):
            raise SourceError("Native card requires its full visible title")
        fields = {}
        for name, icon in [
            ("location", "nyc-icon-location"),
            ("pay", "nyc-icon-euro-circle"),
            ("model", "nyc-icon-time"),
        ]:
            values = [
                clean(e.getparent().text_content())
                for e in card.xpath(
                    './/span[contains(concat(" ",normalize-space(@class)," "),$icon)]',
                    icon=" " + icon + " ",
                )
            ]
            fields[name] = list(dict.fromkeys(values))
        rows.append(
            {
                "id": identity,
                "url": target,
                "native_detail_url": None if external else target,
                "external_redirect_url": target if external else None,
                "body_route_status": "external_source_resolution_required"
                if external
                else "native_detail_route",
                "title": clean(headings[0].text_content()),
                "company_label": card.get("data-job-opening-item-brand"),
                "native_model_label": card.get("data-job-opening-employment"),
                "native_fields": fields,
                "native_card_text": clean(card.text_content()),
                "promoted": card.get("data-job-opening-topjob"),
                "source_variant": card.get("data-job-opening-item-variant"),
                "source_role_category": card.get("data-job-opening-item-category"),
                "original_source_date": None,
                "source_body_complete": False,
                "applicant_fit_assessed": False,
            }
        )
    pages = {}
    for nav in controls:
        for anchor in nav.xpath(".//a[@href]"):
            raw = anchor.get("href")
            if raw.startswith("#"):
                continue
            target = urljoin(url, raw)
            checked_url(source, target, "page")
            if partition(target) != partition(url):
                raise SourceError("Native continuation changes source partition")
            number = int(parse_qs(urlsplit(target).query).get("page", ["1"])[0])
            if number in pages and pages[number] != target:
                raise SourceError("Conflicting native page URLs")
            pages[number] = target
    later = sorted(p for p in pages if p > requested_page)
    if later and later[0] != requested_page + 1:
        raise SourceError("Native continuation has a page gap")
    counters = []
    for element in tree.xpath("//p"):
        value = clean(element.text_content())
        match = re.fullmatch(r"There Are ([0-9.,]+) Jobs wurden gefunden", value)
        if match:
            counters.append((value, int(match[1].replace(".", "").replace(",", ""))))
    if len({n for _, n in counters}) > 1:
        raise SourceError("Conflicting native totals")
    total = counters[0][1] if counters else None
    if total is not None and total > len(rows) and not pages:
        raise SourceError("Native total requires missing pagination")
    result = envelope(source, body, url, "student_board_page")
    result.update(
        requested_query=query,
        native_selected_model_ids=sorted(checked),
        native_model_taxonomy=taxonomy,
        native_selected_sort=sorted(sorts),
        listings=rows,
        returned_count=len(rows),
        reported_total=total,
        native_total_labels=[v for v, _ in counters],
        pagination={
            "page": requested_page,
            "native_page_links": pages,
            "next_url": pages[later[0]] if later else None,
            "native_display_terminal_candidate": not later,
            "historical_coverage_verified": False,
        },
    )
    return result


def parse_detail(source, body, url):
    checked_url(source, url, "detail")
    tree = html.fromstring(body)
    titles = tree.xpath(
        '//div[contains(concat(" ",normalize-space(@class)," ")," job-opening__title ")]//h1'
    )
    descriptions = tree.xpath(
        '//*[@itemprop="description"][contains(concat(" ",normalize-space(@class)," ")," job-opening__description ")]'
    )
    if len(titles) != 1 or len(descriptions) != 1:
        raise SourceError("Complete native job title and description container required")
    postings = []
    for script in tree.xpath('//script[@type="application/ld+json"]'):
        try:
            postings.extend(_postings(json.loads(script.text or "")))
        except json.JSONDecodeError:
            continue
    if len(postings) != 1:
        raise SourceError("One native JobPosting required alongside visible job body")
    job, description = postings[0], descriptions[0]
    if not clean(description.text_content()) or not isinstance(job.get("description"), str):
        raise SourceError("Native job body missing; no snippet fallback")
    facts = []
    for term in description.xpath(".//dt"):
        values = term.xpath("following-sibling::dd[1]")
        if values:
            facts.append(
                {
                    "label": clean(term.text_content()),
                    "value": clean(values[0].text_content()),
                    "itemprop": values[0].get("itemprop"),
                }
            )
    result = envelope(source, body, url, "student_board_job_detail")
    visible_models = [v["value"] for v in facts if v["itemprop"] == "employmentType"]
    result.update(
        id=native_id(url),
        title=clean(titles[0].text_content()),
        structured_title=job.get("title"),
        description=clean(description.text_content()),
        description_html=html.tostring(description, encoding="unicode"),
        native_facts=facts,
        native_job_posting=job,
        native_model_labels=visible_models,
        employment_type=job.get("employmentType"),
        original_source_date=job.get("datePosted"),
        valid_through=job.get("validThrough"),
        source_body_untruncated=True,
        full_posting_reviewed=False,
        requirements_reconciled=False,
        native_identity_basis="Numeric public listing URL ID; JSON-LD identifier is retained but not used as identity.",
        model_reconciliation_required=True,
        apply_urls=list(
            dict.fromkeys(
                urljoin(url, a.get("href"))
                for a in tree.xpath("//a[@href]")
                if re.search(r"^(jetzt )?bewerben$", clean(a.text_content()), re.I)
                and urlsplit(urljoin(url, a.get("href"))).scheme in {"https", "mailto"}
            )
        ),
    )
    return result


def read(source, operation, url):
    checked_url(source, url, operation)
    robots_body, _ = fetch(source, ORIGINS[source] + "/robots.txt", "robots")
    policy = RobotFileParser()
    policy.parse(robots_body.decode("utf-8").splitlines())
    if not policy.can_fetch(AGENT, url):
        raise SourceError("Current robots denies this route; no page request performed")
    body, actual = fetch(source, url, operation)
    raw_path = None
    if os.environ.get("JOB_MARKET_CAPTURE_DIR"):
        folder = Path(os.environ["JOB_MARKET_CAPTURE_DIR"])
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (hashlib.sha256(body).hexdigest() + ".html")
        try:
            with path.open("xb") as handle:
                handle.write(body)
        except FileExistsError:
            pass
        raw_path = str(path)
    result = (parse_page if operation == "page" else parse_detail)(source, body, actual)
    result.update(
        requested_url=url,
        robots_sha256=hashlib.sha256(robots_body).hexdigest(),
        private_raw_checkpoint=raw_path,
    )
    return result


class NoFollow(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def resolve_external(source, url):
    origin = ORIGINS.get(source)
    parsed = urlsplit(url)
    match = re.fullmatch(
        r"/vacatures/([1-9][0-9]*)-[^/]+/redirect_to_external", unquote(parsed.path)
    )
    if (
        not origin
        or parsed.scheme != "https"
        or parsed.netloc != urlsplit(origin).netloc
        or parsed.query
        or parsed.fragment
        or not match
    ):
        raise SourceError("An exact native external-vacancy redirect link is required")
    robots_body, _ = fetch(source, origin + "/robots.txt", "robots")
    policy = RobotFileParser()
    policy.parse(robots_body.decode("utf-8").splitlines())
    if not policy.can_fetch(AGENT, url):
        raise SourceError("Current robots denies the native redirect route")
    request = Request(url, method="HEAD", headers={"User-Agent": AGENT})
    try:
        with build_opener(NoFollow()).open(request, timeout=25) as response:
            location, status = response.headers.get("Location"), response.status
    except HTTPError as error:
        if error.code not in {301, 302, 303, 307, 308}:
            raise SourceError("Native external-link resolution unavailable") from error
        location, status = error.headers.get("Location"), error.code
        error.close()
    if not location:
        raise SourceError(
            "Native HEAD did not expose an external target; no GET/application fallback"
        )
    target = urljoin(url, location)
    value = urlsplit(target)
    if (
        value.scheme != "https"
        or not value.hostname
        or value.username
        or value.password
        or set(parse_qs(value.query))
        & {"access_token", "authenticity_token", "session", "token", "password"}
    ):
        raise SourceError("External target is not a safe public HTTPS evidence URL")
    return {
        "source": source,
        "status": "ok",
        "id": match[1],
        "native_redirect_url": url,
        "external_target_url": target,
        "native_http_status": status,
        "request_method": "HEAD",
        "external_request_performed": False,
        "external_body_fetched": False,
        "requires_target_identity_and_current_policy_review": True,
        "robots_sha256": hashlib.sha256(robots_body).hexdigest(),
        "coverage_complete": False,
        "reviewed_by_model": False,
        "limits": LIMITS,
    }


def capabilities():
    return {
        "status": "ok",
        "sources": list(ORIGINS),
        "origins": ORIGINS,
        "operations": ["page", "detail", "resolve_external"],
        "native_model_key": MODEL_KEY,
        "native_model_ids": sorted(MODEL_IDS),
        "limits": LIMITS,
        "coverage_complete": False,
        "reviewed_by_model": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=list(ORIGINS))
    parser.add_argument("--operation", choices=["page", "detail", "resolve_external"])
    parser.add_argument("--url")
    parser.add_argument("--capabilities", action="store_true")
    args = parser.parse_args()
    try:
        result = (
            capabilities()
            if args.capabilities
            else resolve_external(args.source, args.url)
            if args.operation == "resolve_external"
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
            "message": str(error)
            if isinstance(error, SourceError)
            else "Native source unavailable or changed; no partial/empty success.",
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
