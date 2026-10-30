"""Bounded anonymous HTTP and strict JSON for original public source readers."""
import json
import math
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

MAX_BYTES = 8 * 1024 * 1024


class SourceError(ValueError):
    def __init__(self, code, *, http_status=None, retry_after=None):
        super().__init__(code)
        self.code, self.http_status, self.retry_after = code, http_status, retry_after


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, *, accept, agent="job-market-mcp/0.4.12", bound=MAX_BYTES, opener=None):
    started = datetime.now(timezone.utc).isoformat()
    try:
        with (opener or build_opener(NoRedirect())).open(
                Request(url, headers={"User-Agent": agent, "Accept": accept}), timeout=15) as response:
            raw = response.read(bound + 1)
            if response.status != 200:
                raise SourceError("unexpected_http_status", http_status=response.status)
            if len(raw) > bound:
                raise SourceError("complete_response_exceeds_bound")
            return {"body": raw, "content_type": response.headers.get("Content-Type"),
                    "requested_at": started, "observed_at": datetime.now(timezone.utc).isoformat()}
    except HTTPError as error:
        raise SourceError("source_http_error", http_status=error.code,
                          retry_after=error.headers.get("Retry-After")) from None
    except SourceError:
        raise
    except Exception:
        raise SourceError("source_transport_failed") from None


def robot_policy(base, *, transport=request):
    parsed = urlsplit(base)
    origin = parsed.scheme + "://" + parsed.netloc
    try:
        response = transport(origin + "/robots.txt", accept="text/plain", bound=256 * 1024)
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


def _finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite_json_number")
    return number


def load_json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_object, parse_float=_finite,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeDecodeError):
        raise SourceError("invalid_native_json") from None
