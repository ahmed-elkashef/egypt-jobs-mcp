"""Immutable, explicit consumer segmentation of large public URI discovery.

This is not provider pagination or vacancy eligibility. Only native XING URI
catalogues enter this private, configured cache; no arbitrary file API exists.
"""

import hashlib
import json
import math
import os
import re
import stat
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

SEGMENT_SIZE = 1000
MAX_CAPTURE_BYTES = 40 * 1024 * 1024


class CaptureError(ValueError):
    pass


def cache_directory():
    value = os.environ.get("JOB_MARKET_CAPTURE_DIR")
    if not value:
        raise CaptureError(
            "Set an explicit private JOB_MARKET_CAPTURE_DIR for complete large URI discovery; no truncated fallback"
        )
    directory = Path(value).expanduser().resolve() / "public-uri-captures"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink():
        raise CaptureError("Source capture directory must not be a symlink")
    return directory


def encode(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def record_capture(result):
    if result.get("source") != "xing" or result.get("kind") != "source_uri_discovery":
        raise CaptureError("Only original public URI discovery can be segmented")
    records = result.get("discovery_uris")
    if not isinstance(records, list) or len(records) != result.get("returned_uri_count"):
        raise CaptureError("Complete native URI count is required")
    artifact = {
        "schema_version": 1,
        "source": "xing",
        "kind": "source_uri_discovery",
        "source_url": result["source_url"],
        "source_sha256": result["source_sha256"],
        "native_sitemap_kind": result["native_sitemap_kind"],
        "records": records,
    }
    body = encode(artifact)
    if len(body) > MAX_CAPTURE_BYTES:
        raise CaptureError("Whole native capture exceeds the explicit local bound; no clipping")
    capture_id = hashlib.sha256(body).hexdigest()
    path = cache_directory() / (capture_id + ".json")
    # Publish only complete bytes. A concurrent reader never sees a partially
    # written final path, and a competing writer cannot replace it.
    descriptor, temporary_name = tempfile.mkstemp(prefix=".source-capture-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            existing = _read(capture_id)
            if encode(existing) != body:
                raise CaptureError("Existing immutable source capture differs")
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "status": "ok",
        "source": "xing",
        "kind": "source_uri_capture_manifest",
        "source_url": artifact["source_url"],
        "source_sha256": artifact["source_sha256"],
        "capture_id": capture_id,
        "native_uri_count": len(records),
        "consumer_segment_size": SEGMENT_SIZE,
        "consumer_segment_count": math.ceil(len(records) / SEGMENT_SIZE),
        "native_pagination": False,
        "current_vacancy_status_verified": False,
        "coverage_complete": False,
        "scope": "Whole native URI partition preserved privately. Read every immutable consumer segment; this is not source pagination, active jobs, an employer census or historical coverage.",
    }


def _read(capture_id):
    if not isinstance(capture_id, str) or not re.fullmatch(r"[a-f0-9]{64}", capture_id):
        raise CaptureError("A native content-addressed source capture ID is required")
    path = cache_directory() / (capture_id + ".json")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    if path.is_symlink():
        raise CaptureError("Source capture symlinks are refused")
    with os.fdopen(os.open(path, flags), "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_CAPTURE_BYTES:
            raise CaptureError("Not one whole bounded native source capture")
        body = handle.read(MAX_CAPTURE_BYTES + 1)
    if hashlib.sha256(body).hexdigest() != capture_id:
        raise CaptureError("Immutable source capture checksum changed")
    result = json.loads(body)
    if (
        result.get("schema_version") != 1
        or result.get("source") != "xing"
        or result.get("kind") != "source_uri_discovery"
        or not isinstance(result.get("records"), list)
    ):
        raise CaptureError("Not a public URI discovery artifact")
    origin = urlsplit(result.get("source_url", ""))
    if (
        origin.scheme != "https"
        or origin.netloc != "www.xing.com"
        or not origin.path.endswith(".xml.gz")
        or origin.query
        or origin.fragment
    ):
        raise CaptureError("Not a native XING sitemap capture")
    for row in result["records"]:
        if not isinstance(row, dict) or set(row) != {"url", "source_last_modified"}:
            raise CaptureError("Not a native URI/clock record")
        target = urlsplit(row.get("url", ""))
        if (
            target.scheme != "https"
            or target.netloc != "www.xing.com"
            or target.query
            or target.fragment
        ):
            raise CaptureError("Unsafe captured native URI")
    return result


def read_segment(capture_id, segment_index):
    if not isinstance(segment_index, int) or isinstance(segment_index, bool) or segment_index < 0:
        raise CaptureError("A nonnegative consumer segment index is required")
    data = _read(capture_id)
    records = data["records"]
    total_segments = math.ceil(len(records) / SEGMENT_SIZE)
    if segment_index >= total_segments:
        raise CaptureError("Consumer segment outside the complete captured resource")
    start = segment_index * SEGMENT_SIZE
    selected = records[start : start + SEGMENT_SIZE]
    return {
        "status": "ok",
        "source": "xing",
        "kind": "source_uri_capture_segment",
        "capture_id": capture_id,
        "source_url": data["source_url"],
        "source_sha256": data["source_sha256"],
        "native_uri_count": len(records),
        "consumer_segment_index": segment_index,
        "consumer_segment_count": total_segments,
        "consumer_segment_size": SEGMENT_SIZE,
        "next_consumer_segment_index": segment_index + 1
        if segment_index + 1 < total_segments
        else None,
        "discovery_uris": selected,
        "returned_uri_count": len(selected),
        "native_pagination": False,
        "current_vacancy_status_verified": False,
        "coverage_complete": False,
    }
