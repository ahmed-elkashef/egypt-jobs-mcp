"""Bounded anonymous transport for independently qualified German read routes."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

AGENT = "job-market-mcp/0.4.21 (+https://github.com/ahmed-elkashef/job-market-mcp)"
MAX_BYTES = 8 * 1024 * 1024
MEIN = "https://www.meinpraktikum.de"
MEIN_REST = "https://rest.meinpraktikum.de"
MEIN_SEARCH = MEIN_REST + "/api/v1/search/read/jobposting/search"
GVP = "https://personaldienstleister.de"
GVP_PAGE = GVP + "/der-gvp/mitglieder/gvp-mitglieder/"
GVP_FILTER = GVP + "/wp-json/memberlist/v1/filter/"
HRK = "https://www.hochschulkompass.de"
HRK_PAGE = HRK + "/hochschulen/downloads.html"
HRK_DOWNLOAD_ORIGIN = "https://hs-kompass.de"
HRK_DOWNLOAD = HRK_DOWNLOAD_ORIGIN + "/kompass/xml/download/hs_liste.txt"
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
ORIGINS = {MEIN, MEIN_REST, GVP, HRK, HRK_DOWNLOAD_ORIGIN}
# Only these two independently qualified origins exposed unavailable robots
# (HTTP404). RFC9309 section2.3.1.3 permits access; this never overrides a
# denial, authentication response, throttle, server failure or unknown origin.
ROBOTS404 = {MEIN_REST, HRK_DOWNLOAD_ORIGIN}


class SourceError(ValueError):
    def __init__(self, message, **evidence):
        super().__init__(message)
        self.evidence = evidence


def checked_url(url, method="GET"):
    if not isinstance(url, str) or not 0 < len(url) <= 4096:
        raise SourceError("A bounded exact native read URL is required")
    parts = urlsplit(url)
    origin = parts.scheme + "://" + parts.netloc
    path = unquote(parts.path)
    if (
        origin not in ORIGINS
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or "%" in path
        or "\\" in path
        or any(c.isspace() or ord(c) < 32 for c in url + path)
    ):
        raise SourceError("Only qualified HTTPS origins and unambiguous native routes are supported")
    allowed = method == "GET" and path == "/robots.txt"
    allowed |= method == "POST" and url in {MEIN_SEARCH, GVP_FILTER}
    allowed |= method == "GET" and url in {GVP_PAGE, HRK_PAGE, HRK_DOWNLOAD}
    allowed |= method == "GET" and origin == MEIN and bool(
        re.fullmatch(r"/stellen/[^/?#;\\]+-(" + UUID + r")", path, re.I)
    )
    if not allowed:
        raise SourceError("Unqualified route or method; no application, challenge, detail unlock or write API")
    return url


def personal_use(value):
    if value is not True:
        raise SourceError("Explicit personal_noncommercial_use=true is required before any request")


def positive_page(value):
    if type(value) is not int or not 1 <= value <= 10000:
        raise SourceError("A native page between 1 and the explicit 10,000-page client bound is required")
    return value


def uuid(value):
    if not isinstance(value, str) or not re.fullmatch(UUID, value, re.I):
        raise SourceError("Native UUID identity is missing or malformed")
    return value.lower()


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    content_type: str = ""

    def json(self):
        try:
            return json.loads(self.body)
        except (ValueError, UnicodeError) as error:
            raise SourceError("Native read response is not valid JSON") from error


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    """No cookies, credentials, redirects, source scripts or persistent state."""

    def __init__(self):
        self.opener = build_opener(NoRedirect)
        self.policies = {}
        self.last_request = {}
        self.get_count = 0
        self.read_post_count = 0

    def _raw(self, url, method="GET", body=None, headers=None):
        checked_url(url, method)
        request_headers = {"User-Agent": AGENT, "Accept": "application/json,text/html,text/plain;q=0.9"}
        if headers:
            if set(headers) - {"Content-Type", "X-WP-Nonce"}:
                raise SourceError("Only the fixed public read content type/anonymous CSRF header is permitted")
            if "X-WP-Nonce" in headers and (
                url != GVP_FILTER or not re.fullmatch(r"[A-Za-z0-9]{6,40}", headers["X-WP-Nonce"])
            ):
                raise SourceError("The anonymous public CSRF nonce is restricted to the exact GVP filter")
            request_headers.update(headers)
        request = Request(url, method=method, data=body, headers=request_headers)
        self.get_count += method == "GET"
        self.read_post_count += method == "POST"
        try:
            with self.opener.open(request, timeout=15) as response:
                if response.headers.get("Content-Encoding", "identity").lower() not in {"", "identity"}:
                    raise SourceError("Unexpected source content encoding; no clipped or implicit fallback")
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise SourceError("Whole source response exceeds the explicit byte bound; no clipping")
                return Response(response.status, raw, response.headers.get("Content-Type", ""))
        except HTTPError as error:
            retry = error.headers.get("Retry-After")
            raise SourceError(
                "Native HTTP response refused; no retry, redirect or alternate route",
                http_status=error.code,
                retry_after=retry if retry and re.fullmatch(r"[0-9]{1,8}|[A-Z][a-z]{2}, [0-9]{2} [A-Z][a-z]{2} [0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT", retry) else None,
            ) from None
        except (URLError, TimeoutError, OSError) as error:
            raise SourceError("Native read connection failed", error_type=type(error).__name__) from None

    def _policy(self, url):
        parsed = urlsplit(url)
        origin = parsed.scheme + "://" + parsed.netloc
        if origin not in self.policies:
            try:
                response = self._raw(origin + "/robots.txt")
            except SourceError as error:
                if origin in ROBOTS404 and error.evidence.get("http_status") == 404:
                    self.policies[origin] = (None, 0)
                else:
                    raise SourceError("Current robots policy is unqualified", **error.evidence) from None
            else:
                if response.status != 200:
                    raise SourceError("Current robots policy is unqualified", http_status=response.status)
                parser = RobotFileParser()
                parser.parse(response.body.decode("utf8", "replace").splitlines())
                rate = parser.request_rate(AGENT)
                gap = max(parser.crawl_delay(AGENT) or 0, rate.seconds / rate.requests if rate else 0)
                if gap > 10:
                    raise SourceError("Declared request interval exceeds this bounded operation; a longer run is needed")
                self.policies[origin] = (parser, gap)
        parser, gap = self.policies[origin]
        if parser is not None and not parser.can_fetch(AGENT, url):
            raise SourceError("Current robots policy denies this exact native route")
        elapsed = time.monotonic() - self.last_request.get(origin, 0)
        if elapsed < gap:
            time.sleep(gap - elapsed)
        self.last_request[origin] = time.monotonic()

    def get(self, url):
        checked_url(url)
        self._policy(url)
        return self._raw(url)

    def post(self, url, body, content_type="application/json", public_nonce=None):
        checked_url(url, "POST")
        self._policy(url)
        headers = {"Content-Type": content_type}
        if public_nonce is not None:
            headers["X-WP-Nonce"] = public_nonce
        return self._raw(url, "POST", body, headers)


def base_result(source, kind):
    return {
        "status": "ok", "source": source, "kind": kind,
        "coverage_complete": False, "full_posting_reviewed": False, "reviewed_by_model": False,
        "original_publication_verified": False,
        "accounts_applications_contacts_subscriptions_or_payments_requested": False,
        "source_scripts_executed_or_implementation_copied": False,
        "user_credentials_cookies_or_session_state_exported": False,
    }
