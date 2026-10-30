"""Original, source-bound ROR public release and immutable directory contracts.

Only explicitly advertised public HTML and bulk-file routes; never Zenodo API,
candidate data, organisation websites, application endpoints or source scripts.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import build_opener

from lxml import html

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from public_http import NoRedirect, SourceError, load_json, request, robot_policy  # noqa: E402

ORIGIN = "https://zenodo.org"
CONCEPT = ORIGIN + "/records/6347574"
AGENT = "JobMarketMCP/0.4.26 (+https://github.com/ahmed-elkashef/job-market-mcp)"
COUNTRIES = {"DE", "EG"}
STATUSES = {"active", "inactive", "withdrawn"}
TYPES = {"education", "funder", "healthcare", "company", "archive", "nonprofit", "government", "facility", "other"}
ZIP_BOUND, JSON_BOUND = 128 * 1024 * 1024, 512 * 1024 * 1024
LIMITS = [
    "ROR research-organisation directory memberships, not all legal employers, worksites, vacancies or a historical country/week census.",
    "Native active status means research activity, not hiring. Inactive/withdrawn records and successor/other relationships are retained.",
    "All native organisation types, name variants, locations and original record fields are preserved; aliases can be historical and locations do not establish job workplaces or worker eligibility.",
    "Use an exact resolved immutable release. Country segments follow its verified full JSON array, never filter-only API pages; no career/degree/employer query.",
    "Published metadata/ZIP checksum and the complete native JSON must reconcile. No silent repair, missing-country omission, partial archive or provider-limit-as-empty fallback.",
    "Only independently policy-permitted public HTML and advertised bulk files. Denied API routes, credentials, cookies, accounts, scripts, applications and contact are not used.",
]


def base(kind):
    return {"status": "ok", "source": "ror", "kind": kind, "coverage_complete": False,
            "reviewed_by_model": False, "full_posting_reviewed": False, "original_publication_verified": False,
            "source_active_vacancy_verified": False, "legal_employer_or_job_worksite_verified": False,
            "accounts_applications_contacts_subscriptions_or_payments_requested": False,
            "source_scripts_executed_or_implementation_copied": False,
            "user_credentials_cookies_or_session_state_exported": False,
            "API_routes_requested": False, "source_result_count": None, "limits": LIMITS}


def record_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{3,11}", value) or value == "6347574":
        raise SourceError("exact_version_specific_ROR_record_ID_required")
    return value


def record_url(value):
    return ORIGIN + "/records/" + record_id(value)


def checked_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise SourceError("invalid_ROR_public_route")
    p = urlsplit(value)
    if p.scheme + "://" + p.netloc != ORIGIN or p.fragment or any(c.isspace() or ord(c) < 32 for c in value):
        raise SourceError("fixed_ROR_public_origin_required")
    if p.path == "/robots.txt" and not p.query:
        return value
    if re.fullmatch(r"/records/[1-9][0-9]{3,11}", p.path) and not p.query:
        return value
    if (re.fullmatch(r"/records/[1-9][0-9]{3,11}/files/v[0-9]+(?:\.[0-9]+){1,2}-[0-9]{4}-[0-9]{2}-[0-9]{2}-ror-data\.zip", p.path)
            and p.query == "download=1"):
        return value
    raise SourceError("only_ROR_public_record_and_advertised_bulk_routes_no_API")


class RedirectHeaders(NoRedirect):
    retry_after = None

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.retry_after = headers.get("Retry-After")
        return None


class Client:
    def __init__(self, transport=request):
        self.transport, self.redirect = transport, RedirectHeaders()
        self.opener = build_opener(self.redirect)
        self.rules, self.policy, self.last, self.get_count = None, None, 0, 0

    def raw(self, url, **kwargs):
        checked_url(url)
        self.get_count += 1
        self.redirect.retry_after = None
        result = self.transport(url, agent=AGENT, opener=self.opener, **kwargs)
        if result.get("http_status") in {301, 302, 303, 307, 308}:
            result["retry_after"] = self.redirect.retry_after or result.get("retry_after")
        return result

    def get(self, url, *, archive=False, resolve=False):
        checked_url(url)
        if self.policy is None:
            self.rules, self.policy = robot_policy(url, transport=self.raw)
            self.last = time.monotonic()
        if self.rules is not None and not self.rules.can_fetch(AGENT, url):
            raise SourceError("robots_denies_exact_ROR_public_route")
        rate = self.rules.request_rate(AGENT) if self.rules else None
        gap = max((self.rules.crawl_delay(AGENT) or 0) if self.rules else 0, rate.seconds / rate.requests if rate else 0)
        if gap > 10:
            raise SourceError("declared_ROR_interval_requires_longer_operation")
        elapsed = time.monotonic() - self.last
        if elapsed < gap:
            time.sleep(gap - elapsed)
        self.last = time.monotonic()
        return self.raw(url, accept="application/octet-stream,application/zip" if archive else "text/html",
                        bound=ZIP_BOUND if archive else 4 * 1024 * 1024, timeout=30 if archive else 15,
                        redirect_metadata=resolve)


def document(raw, content_type):
    if (not isinstance(raw, bytes) or not re.search(rb"</html\s*>\s*$", raw, re.I)
            or not isinstance(content_type, str)
            or not re.fullmatch(r'text/html\s*;\s*charset\s*=\s*"?utf-8"?', content_type.lower())):
        raise SourceError("whole_explicit_UTF8_ROR_HTML_required")
    try:
        return html.fromstring(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise SourceError("invalid_ROR_UTF8_HTML") from None


def metadata(raw, rid, content_type="text/html; charset=utf-8"):
    url = record_url(rid)
    tree = document(raw, content_type)
    if (tree.xpath('//link[@rel="canonical"]/@href') != [url]
            or tree.xpath('//meta[@property="og:url"]/@content') != [url]
            or len(tree.xpath('//main')) != 1 or tree.xpath('//title/text()') != ["ROR Data | Zenodo"]):
        raise SourceError("complete_canonical_ROR_release_metadata_required")
    main = tree.xpath('//main')[0]
    links = {urljoin(url, a.get("href")) for a in main.xpath('.//a[@href]') if "/files/" in a.get("href", "") and "ror-data.zip" in a.get("href", "")}
    licenses = sorted({a.get("href") for a in main.xpath('.//a[@href]') if "creativecommons.org/" in a.get("href", "")})
    for node in main.xpath('.//script|.//style|.//form|.//input|.//button|.//select|.//textarea|.//iframe|.//svg|.//img|.//video|.//audio|.//object|.//embed|.//nav|.//header|.//footer'):
        node.drop_tree()
    text = " ".join(" ".join(main.itertext()).split())
    counts = re.findall(r"Release v([0-9]+(?:\.[0-9]+){1,2}) contains ROR IDs and metadata for ([0-9,]+) research organizations", text)
    hashes = set(re.findall(r"md5[:\s]+([0-9a-f]{32})", text))
    if len(links) != 1 or len(counts) != 1 or len(hashes) != 1 or "https://creativecommons.org/publicdomain/zero/1.0" not in licenses:
        raise SourceError("one_complete_published_ROR_archive_count_checksum_license_required")
    archive = links.pop()
    checked_url(archive)
    name = urlsplit(archive).path.rsplit("/", 1)[1]
    match = re.fullmatch(r"v([0-9]+(?:\.[0-9]+){1,2})-([0-9]{4}-[0-9]{2}-[0-9]{2})-ror-data\.zip", name)
    if not match or not archive.startswith(url + "/files/") or match[1] != counts[0][0] or not 0 < int(counts[0][1].replace(",", "")) <= 1000000:
        raise SourceError("native_ROR_record_version_file_and_count_differ")
    return {**base("ror_release_metadata"), "record_id": rid, "source_url": url, "version": match[1],
            "release_date": match[2], "archive_url": archive, "archive_filename": name,
            "published_archive_md5": hashes.pop(), "declared_dataset_records": int(counts[0][1].replace(",", "")),
            "native_license_references": licenses, "native_public_record_text": text,
            "raw_metadata_html_sha256": hashlib.sha256(raw).hexdigest(), "source_text_decoding": "strict_utf8_before_HTML",
            "original_published_at": None, "organization_count": None, "is_latest_release_verified": False}


def release(rid=None, *, client=None):
    transport = client or Client()
    if rid is not None:
        response = transport.get(record_url(rid))
        result = metadata(response["body"], rid, response["content_type"])
    else:
        response = transport.get(CONCEPT, resolve=True)
        if response.get("http_status") not in {301, 302, 303, 307, 308}:
            raise SourceError("explicit_native_ROR_concept_resolution_required")
        location = response.get("location")
        if not isinstance(location, str):
            raise SourceError("native_ROR_resolution_target_missing")
        target = urljoin(CONCEPT, location)
        checked_url(target)
        match = re.fullmatch(re.escape(ORIGIN) + r"/records/([1-9][0-9]{3,11})", target)
        if not match:
            raise SourceError("native_ROR_resolution_must_be_exact_public_record")
        value = response.get("retry_after")
        if value is not None and (not re.fullmatch(r"[0-9]{1,5}", value) or int(value) > 3600):
            raise SourceError("native_ROR_retry_after_requires_operator_review", retry_after=value)
        delay = int(value or 0)
        result = {**base("ror_release_resolution"), "concept_url": CONCEPT, "resolved_record_id": record_id(match[1]),
                  "resolved_record_url": target, "redirect_HTTP_status": response["http_status"],
                  "redirects_followed": 0, "retry_after_seconds": delay,
                  "record_read_not_before": (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat(),
                  "next_request": {"record_id": match[1]}, "organization_count": None}
    return {**result, "native_GET_requests": transport.get_count, "native_read_POST_requests": 0,
            "native_request_started_at": response.get("requested_at"),
            "native_response_observed_at": response.get("observed_at"),
            "native_robots_policy": getattr(transport, "policy", None)}


def archive_records(raw, meta):
    if (not isinstance(raw, bytes) or len(raw) > ZIP_BOUND or not raw.startswith(b"PK\x03\x04")
            or hashlib.md5(raw).hexdigest() != meta["published_archive_md5"]):
        raise SourceError("complete_published_ROR_archive_checksum_required")
    stem = meta["archive_filename"][:-4]
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if (len(members) != 2 or {i.filename for i in members} != {stem + ".json", stem + ".csv"}
                    or any(i.flag_bits & 1 or i.compress_type not in {0, 8} or i.file_size > JSON_BOUND for i in members)):
                raise SourceError("only_complete_bounded_ROR_JSON_CSV_archive_members")
            data = load_json(archive.read(stem + ".json"))
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError):
        raise SourceError("invalid_or_incomplete_ROR_archive") from None
    if not isinstance(data, list) or len(data) != meta["declared_dataset_records"]:
        raise SourceError("complete_native_ROR_array_and_published_count_required")
    seen, status_counts, countries = set(), Counter(), {code: [] for code in COUNTRIES}
    required = {"id", "admin", "domains", "established", "external_ids", "links", "locations", "names", "relationships", "status", "types"}
    for index, record in enumerate(data):
        if (not isinstance(record, dict) or not required <= set(record)
                or not isinstance(record.get("id"), str) or not re.fullmatch(r"https://ror.org/[0-9a-hj-km-np-tv-z]{9}", record["id"])
                or record["id"] in seen or not isinstance(record.get("status"), str) or record["status"] not in STATUSES
                or not isinstance(record.get("types"), list) or not record["types"] or any(not isinstance(v, str) or v not in TYPES for v in record["types"])
                or not isinstance(record.get("names"), list) or not record["names"]
                or not isinstance(record.get("locations"), list) or not record["locations"]
                or any(not isinstance(record.get(k), list) for k in ["domains", "links", "relationships", "external_ids"])
                or not isinstance(record.get("admin"), dict)):
            raise SourceError("whole_unique_typed_native_ROR_records_required")
        codes = set()
        for location in record["locations"]:
            code = (location.get("geonames_details") or {}).get("country_code") if isinstance(location, dict) else None
            if not isinstance(code, str) or not re.fullmatch(r"[A-Z]{2}", code):
                raise SourceError("missing_native_ROR_country_requires_ambiguity_review_no_silent_omission")
            codes.add(code)
        seen.add(record["id"])
        status_counts[record["status"]] += 1
        for code in codes & COUNTRIES:
            countries[code].append({"native_array_index": index, "record": record})
    return {"archive_sha256": hashlib.sha256(raw).hexdigest(), "dataset_records": len(data),
            "status_counts": dict(status_counts), "country_records": countries}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def atomic(path, raw):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".ror-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(raw)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def cache_folder(rid, root=None):
    root = root or os.environ.get("JOB_MARKET_CAPTURE_DIR")
    if not root or not Path(root).is_absolute():
        raise SourceError("explicit_private_absolute_capture_directory_required")
    folder = Path(root) / "ror" / record_id(rid)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def store_archive(folder, meta, raw):
    parsed = archive_records(raw, meta)
    countries = {}
    for country, rows in parsed["country_records"].items():
        data = encoded(rows)
        atomic(folder / (country + ".json"), data)
        countries[country] = {"records": len(rows), "sha256": hashlib.sha256(data).hexdigest(),
                              "status_counts": dict(Counter(r["record"]["status"] for r in rows))}
    atomic(folder / "archive.zip", raw)
    manifest = {"format": "job-market-ror-verified-directory-v1", "release": meta,
                "archive_sha256": parsed["archive_sha256"], "archive_bytes": len(raw),
                "dataset_records": parsed["dataset_records"], "dataset_status_counts": parsed["status_counts"],
                "countries": countries, "cache_validated_at": datetime.now(timezone.utc).isoformat()}
    # The manifest is the commit point; no partial country projection is used.
    atomic(folder / "manifest.json", encoded(manifest))
    return manifest


def cached_manifest(folder, rid):
    path = folder / "manifest.json"
    if not path.exists():
        return None
    try:
        manifest = load_json(path.read_bytes())
        if (manifest.get("format") != "job-market-ror-verified-directory-v1"
                or manifest["release"]["record_id"] != rid
                or manifest["release"]["source_url"] != record_url(rid)
                or not re.fullmatch(r"[0-9a-f]{64}", manifest["archive_sha256"])
                or set(manifest["countries"]) != COUNTRIES
                or manifest["dataset_records"] != manifest["release"]["declared_dataset_records"]):
            raise SourceError("cached_ROR_release_manifest_drift")
        return manifest
    except (ValueError, TypeError, KeyError, AttributeError, OSError):
        raise SourceError("cached_ROR_release_manifest_invalid_no_silent_refetch") from None


def acquire_cache(folder, rid, client):
    lock = folder / "building.json"
    if lock.exists():
        if time.time() - lock.stat().st_mtime <= 180:
            raise SourceError("ROR_cache_build_in_progress_resume_later")
        # Preserve a stale lease after the bounded reader has expired. Never
        # inspect or signal another process, or discard a completed snapshot.
        lock.rename(folder / ("stale-lease-" + str(time.time_ns()) + ".json"))
    try:
        with lock.open("xb") as handle:
            handle.write(encoded({"record_id": rid, "lease_seconds": 180}))
    except FileExistsError:
        raise SourceError("ROR_cache_build_in_progress_resume_later") from None
    try:
        meta = release(rid, client=client)
        response = client.get(meta["archive_url"], archive=True)
        if response.get("content_type", "").split(";")[0].strip().lower() not in {"application/zip", "application/octet-stream"}:
            raise SourceError("native_ROR_archive_content_type_changed")
        return store_archive(folder, meta, response["body"])
    finally:
        lock.unlink(missing_ok=True)


def directory(rid, country, offset=0, limit=200, snapshot_sha256=None, *, client=None, cache_root=None):
    record_id(rid)
    if (not isinstance(country, str) or country not in COUNTRIES or type(offset) is not int or not 0 <= offset <= 1000000
            or type(limit) is not int or not 1 <= limit <= 500
            or offset > 0 and snapshot_sha256 is None
            or snapshot_sha256 is not None and (not isinstance(snapshot_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256))):
        raise SourceError("exact_ROR_country_and_snapshot_bound_segment_required_no_role_query")
    folder = cache_folder(rid, cache_root)
    manifest = cached_manifest(folder, rid)
    transport, hit = client or Client(), manifest is not None
    if manifest is None:
        manifest = acquire_cache(folder, rid, transport)
    if snapshot_sha256 is not None and snapshot_sha256 != manifest["archive_sha256"]:
        raise SourceError("ROR_snapshot_digest_differs_no_reset_or_merge")
    info = manifest["countries"][country]
    try:
        data = (folder / (country + ".json")).read_bytes()
        if hashlib.sha256(data).hexdigest() != info["sha256"]:
            raise SourceError("ROR_country_projection_digest_drift")
        rows = load_json(data)
        if not isinstance(rows, list) or len(rows) != info["records"]:
            raise SourceError("ROR_country_projection_count_drift")
    except OSError:
        raise SourceError("ROR_country_projection_unavailable_no_silent_refetch") from None
    total = len(rows)
    if offset >= total and (offset != 0 or total != 0):
        raise SourceError("ROR_segment_outside_verified_country_array")
    selected = rows[offset:offset + limit]
    for row in selected:
        if (not isinstance(row, dict) or type(row.get("native_array_index")) is not int
                or not 0 <= row["native_array_index"] < manifest["dataset_records"]
                or not isinstance(row.get("record"), dict)
                or country not in {(r.get("geonames_details") or {}).get("country_code") for r in row["record"].get("locations", [])}):
            raise SourceError("native_ROR_country_membership_or_array_position_drift")
    next_offset = offset + len(selected) if offset + len(selected) < total else None
    following = {"record_id": rid, "country": country, "offset": next_offset, "limit": limit,
                 "snapshot_sha256": manifest["archive_sha256"]} if next_offset is not None else None
    return {**base("organisation_directory"), "record_id": rid, "country": country,
            "release": manifest["release"], "snapshot_sha256": manifest["archive_sha256"],
            "dataset_records": manifest["dataset_records"], "dataset_status_counts": manifest["dataset_status_counts"],
            "country_organization_records": total, "country_status_counts": info["status_counts"],
            "organization_count": len(selected), "organizations": selected,
            "offset": offset, "limit": limit, "next_request": following,
            "native_directory_country_array_exhausted": following is None,
            "snapshot_validated_at": manifest["cache_validated_at"], "cache_hit": hit,
            "native_GET_requests": transport.get_count, "native_read_POST_requests": 0,
            "source_scripts_controls_or_hydration_exported": False,
            "original_published_at": None, "vacancy_count": None}
