"""Original anonymous Teamtailor career-site JSON/RSS feed reader.

Uses the career site's advertised API catalogue, never the secret-key account
API. Exact employer career origins require independent employer identification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from lxml import etree, html

AGENT = "job-market-mcp/0.4.10"
MAX_BYTES = 8 * 1024 * 1024
CUSTOM_ORIGINS = {
    "https://jobs.highsnobiety.com": "https://www.highsnobiety.com/",
    "https://careers.voi.com": "https://www.voi.com/",
}
LOCATION_NS = "{https://teamtailor.com/locations}"
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
LIMITS = [
    "One explicitly verified employer career site is not an employer or country census.",
    "Current moving feeds and a reconciled native count do not establish a complete historical weekly interval.",
    "JSON date_published, schema datePosted and RSS pubDate remain source clocks, not a verified first-publication or reopening instant.",
    "Native remoteStatus, role and location facts do not prove worker-country eligibility, compatible hours or student contract.",
    "Source body representations and metadata require individual employer/person review; application requirements are not inferred from a feed.",
    "No account API, key, cookie, login, apply form, contact or subscription operation is supported.",
]


class SourceError(ValueError):
    def __init__(self, code, *, http_status=None, retry_after=None):
        super().__init__(code)
        self.code, self.http_status, self.retry_after = code, http_status, retry_after


def origin(value):
    if not isinstance(value, str) or len(value) > 2048 or value != value.strip() or any(ord(c) < 32 for c in value):
        raise SourceError("invalid_verified_career_origin")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise SourceError("invalid_verified_career_origin") from None
    vendor = re.fullmatch(r"([a-z0-9]+(?:-[a-z0-9]+)*)\.teamtailor\.com", parsed.netloc)
    canonical = "https://" + parsed.netloc
    if (parsed.scheme != "https" or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or not (canonical in CUSTOM_ORIGINS or vendor and vendor[1] not in {"api", "www", "docs", "support", "status"})):
        raise SourceError("unverified_career_origin")
    return canonical


def native_job_url(value, base):
    if not isinstance(value, str) or len(value) > 2048:
        raise SourceError("invalid_native_job_url")
    parsed = urlsplit(value)
    if (parsed.scheme + "://" + parsed.netloc != base or parsed.query or parsed.fragment
            or not re.fullmatch(r"/jobs/[1-9][0-9]*-[^/?#\\\s]+", unquote(parsed.path))
            or re.search(r"%[0-9a-fA-F]{2}", unquote(parsed.path))
            or any(ord(c) < 32 for c in unquote(parsed.path))):
        raise SourceError("invalid_native_job_url")
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, *, accept, bound=MAX_BYTES, opener=None):
    opener = opener or build_opener(NoRedirect())
    started = datetime.now(timezone.utc).isoformat()
    try:
        with opener.open(Request(url, headers={"User-Agent": AGENT, "Accept": accept}), timeout=10) as response:
            raw = response.read(bound + 1)
            if response.status != 200:
                raise SourceError("unexpected_http_status", http_status=response.status)
            if len(raw) > bound:
                raise SourceError("complete_response_exceeds_bound")
            return {"body": raw, "link": response.headers.get("Link", ""),
                    "content_type": response.headers.get("Content-Type"),
                    "requested_at": started, "observed_at": datetime.now(timezone.utc).isoformat()}
    except HTTPError as error:
        raise SourceError("source_http_error", http_status=error.code,
                          retry_after=error.headers.get("Retry-After")) from None
    except SourceError:
        raise
    except Exception:
        raise SourceError("source_transport_failed") from None


def robot_policy(base, *, transport=request):
    try:
        response = transport(base + "/robots.txt", accept="text/plain", bound=256 * 1024)
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


def load_json(raw):
    try:
        result = json.loads(raw, object_pairs_hook=_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeDecodeError):
        raise SourceError("invalid_native_json") from None
    if not isinstance(result, dict):
        raise SourceError("invalid_native_json_object")
    return result


def visible_text(markup):
    if not isinstance(markup, str) or not markup.strip():
        raise SourceError("missing_complete_native_description")
    try:
        document = html.fragment_fromstring(markup, create_parent="div")
    except (etree.ParserError, ValueError, TypeError):
        raise SourceError("invalid_native_description_html") from None
    for element in document.xpath(".//script|.//style|.//iframe|.//object|.//embed"):
        element.drop_tree()
    for element in document.iter():
        if element.tag in {"p", "li", "div", "br", "h1", "h2", "h3", "h4"}:
            element.tail = " " + (element.tail or "")
    text = " ".join(document.text_content().split())
    if not text:
        raise SourceError("empty_native_description")
    return text


def native_manifest(raw, base):
    try:
        doc = html.fromstring(raw)
    except (etree.ParserError, ValueError, TypeError):
        raise SourceError("invalid_native_jobs_html") from None
    rss = doc.xpath('//link[@type="application/rss+xml"]/@href')
    if rss != [base + "/jobs.rss"]:
        raise SourceError("native_rss_not_advertised_or_ambiguous")
    text = " ".join(" ".join(doc.xpath('//body//text()[not(ancestor::script) and not(ancestor::style)]')).split())
    counts = {int(x) for x in re.findall(r"\b([0-9]+)\s+(?:jobs|Stellenangebote|Stellen)\b", text, re.I)}
    count = next(iter(counts)) if len(counts) == 1 else None
    if count is None and re.search(r"\bNo matching jobs\b", text, re.I):
        count = 0
    return {"declared_count": count, "rss_url": rss[0]}


def rss_items(raw, base):
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise SourceError("xml_entity_declaration_refused")
    try:
        doc = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        raise SourceError("invalid_native_rss") from None
    if doc.tag != "rss" or doc.findtext("./channel/link") != base + "/jobs":
        raise SourceError("native_rss_identity_mismatch")
    rows = {}
    for item in doc.findall("./channel/item"):
        url = native_job_url(item.findtext("link"), base)
        if url in rows:
            raise SourceError("duplicate_rss_job_url")
        locations = []
        for place in item.findall(LOCATION_NS + "locations/" + LOCATION_NS + "location"):
            locations.append({k: place.findtext(LOCATION_NS + k) for k in ("name", "address", "zip", "city", "country")})
        rows[url] = {"guid": item.findtext("guid"), "title": item.findtext("title"),
                     "description_html": item.findtext("description"), "pub_date_raw": item.findtext("pubDate"),
                     "remote_status_raw": item.findtext("remoteStatus"), "locations": locations,
                     **{k: item.findtext(LOCATION_NS + k) for k in ("department", "role", "division")}}
    return rows


def parse_feed(raw, rss_raw, manifest_raw, base):
    base = origin(base)
    feed, rss, manifest = load_json(raw), rss_items(rss_raw, base), native_manifest(manifest_raw, base)
    if (feed.get("version") != "https://jsonfeed.org/version/1.1" or feed.get("feed_url") != base + "/jobs.json"
            or feed.get("home_page_url") != base + "/jobs" or not isinstance(feed.get("items"), list)):
        raise SourceError("native_feed_identity_or_version_mismatch")
    if feed.get("next_url"):
        raise SourceError("native_feed_continuation_requires_verified_contract")
    items = feed["items"]
    if len(items) != len(rss) or (manifest["declared_count"] is not None and len(items) != manifest["declared_count"]):
        raise SourceError("native_html_json_rss_count_mismatch")
    jobs, ids, urls = [], set(), set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not UUID.fullmatch(item["id"]):
            raise SourceError("invalid_native_feed_job_identity")
        url = native_job_url(item.get("url"), base)
        if item["id"] in ids or url in urls:
            raise SourceError("duplicate_native_feed_job")
        ids.add(item["id"])
        urls.add(url)
        native = rss.get(url)
        schema = item.get("_jobposting")
        if (not native or native["guid"] != item["id"] or not isinstance(item.get("title"), str)
                or not item["title"].strip() or native["title"] != item["title"]
                or not isinstance(schema, dict) or schema.get("@type") != "JobPosting"):
            raise SourceError("native_json_rss_job_identity_mismatch")
        description = visible_text(item.get("content_html"))
        rss_description = visible_text(native["description_html"])
        schema_description = schema.get("description")
        jobs.append({"id": base + "::" + item["id"], "native_guid": item["id"], "url": url,
                     "title": item["title"], "description": description, "description_html": item["content_html"],
                     "body_representation": "native_teamtailor_json_feed_content", "source_body_untruncated": True,
                     "native_job_posting": schema, "native_rss": native,
                     "native_rss_description": rss_description,
                     "body_variants_differ": not (item["content_html"] == native["description_html"] == schema_description),
                     "source_date_published": item.get("date_published"), "original_published_at": None,
                     "native_date_modified": item.get("date_modified"), "full_posting_reviewed": False})
    if urls != set(rss):
        raise SourceError("native_json_rss_uri_sets_differ")
    return {"status": "ok", "source": "teamtailor", "kind": "teamtailor_native_feed", "careers_origin": base,
            "returned_count": len(jobs), "source_result_count": manifest["declared_count"], "listings": jobs,
            "native_count_reconciled": manifest["declared_count"] == len(jobs),
            "pagination": {"next_url": None, "native_feed_next_url": None,
                           "native_ui_count": manifest["declared_count"], "native_feed_count": len(jobs)},
            "source_hashes": {"json": hashlib.sha256(raw).hexdigest(), "rss": hashlib.sha256(rss_raw).hexdigest(),
                              "native_jobs_html": hashlib.sha256(manifest_raw).hexdigest()},
            "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS}


def read(careers_origin, *, job_id=None, transport=request):
    base = origin(careers_origin)
    if job_id is not None and (not isinstance(job_id, str) or not UUID.fullmatch(job_id)):
        raise SourceError("invalid_exact_native_job_guid")
    rules, policy = robot_policy(base, transport=transport)
    provenance = []
    def get(path, accept):
        url = base + path
        if rules is not None and not rules.can_fetch(AGENT, url):
            raise SourceError("robots_denied")
        result = transport(url, accept=accept)
        provenance.append({"url": url, "method": "GET", "bytes": len(result["body"]),
                           "sha256": hashlib.sha256(result["body"]).hexdigest(),
                           "requested_at": result.get("requested_at"), "observed_at": result.get("observed_at")})
        return result
    page = get("/jobs", "text/html")
    catalogue_links = re.findall(r'<([^>]+)>;\s*rel="api-catalog"', page.get("link") or "")
    if catalogue_links != [base + "/.well-known/api-catalog"]:
        raise SourceError("native_api_catalogue_not_advertised_or_ambiguous")
    catalogue = load_json(get("/.well-known/api-catalog", "application/linkset+json,application/json")["body"])
    links = [link for entry in catalogue.get("linkset", []) if entry.get("anchor") == base + "/jobs"
             for link in entry.get("service-desc", [])
             if link.get("type") == "application/feed+json"]
    if links != [{"href": base + "/jobs.json", "type": "application/feed+json"}]:
        raise SourceError("native_json_feed_not_advertised_or_ambiguous")
    native_manifest(page["body"], base)
    feed = get("/jobs.json", "application/feed+json,application/json")
    rss = get("/jobs.rss", "application/rss+xml,application/xml")
    result = parse_feed(feed["body"], rss["body"], page["body"], base)
    result.update(policy=policy, provenance=provenance)
    if job_id is not None:
        matching = [job for job in result["listings"] if job["native_guid"] == job_id]
        if len(matching) != 1:
            raise SourceError("exact_job_not_present_in_current_native_feed")
        return {"status": "ok", "source": "teamtailor", "kind": "teamtailor_native_detail",
                "careers_origin": base, **matching[0], "policy": policy, "provenance": provenance,
                "native_feed_returned_count": result["returned_count"],
                "coverage_complete": False, "reviewed_by_model": False, "limits": LIMITS}
    return result


def capabilities():
    return {"status": "ok", "source": "teamtailor", "operations": ["inventory", "detail"],
            "seed_required": True, "vendor_origins": "Explicit identified *.teamtailor.com career origins, excluding account/support hosts.",
            "verified_custom_origins": CUSTOM_ORIGINS, "max_complete_response_bytes": MAX_BYTES,
            "protocol": "Native /jobs advertises API catalogue and RSS; catalogue advertises JSON Feed1.1. Reconcile all native JSON/RSS IDs and source count; preserve full body variants.",
            "acquisition_filters": [], "coverage_complete": False, "limits": LIMITS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--careers-origin")
    parser.add_argument("--job-id")
    args = parser.parse_args()
    try:
        result = capabilities() if args.capabilities else read(args.careers_origin, job_id=args.job_id)
    except (ValueError, KeyError, TypeError, AttributeError, ElementTree.ParseError) as error:
        result = {"status": "source_limited", "source": "teamtailor", "returned_count": None,
                  "source_result_count": None, "error": error.code if isinstance(error, SourceError) else "invalid_native_source_response",
                  "http_status": getattr(error, "http_status", None), "retry_after": getattr(error, "retry_after", None),
                  "coverage_complete": False, "reviewed_by_model": False}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
