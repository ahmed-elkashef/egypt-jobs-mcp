"""Original anonymous Personio primary advert reader; no framework execution."""

import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

from lxml import etree, html

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.public_http import SourceError, load_json, request, robot_policy  # noqa: E402

AGENT = "job-market-mcp/0.4.20"
SOURCE = "personio"
PUBLIC_FIELDS = {
    "@context",
    "@type",
    "title",
    "description",
    "identifier",
    "datePosted",
    "validThrough",
    "employmentType",
    "hiringOrganization",
    "jobLocation",
    "jobLocationType",
    "applicantLocationRequirements",
    "baseSalary",
    "educationRequirements",
    "qualifications",
    "responsibilities",
    "experienceRequirements",
    "workHours",
    "industry",
    "occupationalCategory",
    "incentiveCompensation",
    "jobBenefits",
}
REMOVED = ".//script|.//style|.//iframe|.//form|.//input|.//button|.//select|.//textarea|.//object|.//embed|.//svg|.//img|.//video|.//audio"
LIMITS = [
    "Requires an independently verified exact employer advert; this is not employer discovery, a country inventory or historical coverage.",
    "Complete primary public text/markup and separate About us context are preserved. Media-only requirements remain unverified; no scripts, media or application controls are requested.",
    "Career-page display language and native description translation are independent of working-language requirements. Source schema and native clocks are not original publication or personal fit.",
    "No account, application, credential, cookie, contact, submission or payment operation is supported. No session/hydration state is exported.",
]


def checked_url(uri):
    if (
        not isinstance(uri, str)
        or len(uri) > 4096
        or uri != uri.strip()
        or any(ord(char) < 32 for char in uri)
    ):
        raise SourceError("invalid_personio_job_url")
    try:
        parsed = urlsplit(uri)
    except ValueError:
        raise SourceError("invalid_personio_job_url") from None
    query = parse_qs(parsed.query, keep_blank_values=True)
    if (
        parsed.scheme != "https"
        or parsed.fragment
        or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,119}\.jobs\.personio\.(?:de|com)", parsed.netloc)
        or not re.fullmatch(r"/job/[1-9][0-9]{0,19}", parsed.path)
        or query
        and (
            set(query) != {"language"}
            or len(query["language"]) != 1
            or not re.fullmatch(r"[a-z]{2}", query["language"][0])
        )
        or parsed.query
        and not query
    ):
        raise SourceError("invalid_personio_job_url")
    return parsed.netloc, parsed.path.rsplit("/", 1)[1], query.get("language", [None])[0]


def token_nodes(node, token):
    return node.xpath(
        ".//*[contains(concat(' ', normalize-space(@class), ' '), ' " + token + " ')]"
    )


def one(nodes, code):
    if len(nodes) != 1:
        raise SourceError(code)
    return nodes[0]


def public_html(node):
    clone = deepcopy(node)
    for child in clone.xpath(REMOVED):
        child.drop_tree()
    for child in clone.iter():
        for name in list(child.attrib):
            if (
                name not in {"href", "title"}
                or name == "href"
                and urlsplit(child.attrib[name]).scheme not in {"", "https", "http"}
            ):
                del child.attrib[name]
    return {
        "html": html.tostring(clone, encoding="unicode"),
        "text": " ".join(" ".join(clone.itertext()).split()),
    }


def public_schema_description(value):
    if not isinstance(value, str):
        raise SourceError("missing_personio_schema_description")
    try:
        return public_html(html.fragment_fromstring(value, create_parent="section"))
    except (ValueError, TypeError, etree.ParserError):
        raise SourceError("invalid_personio_schema_description") from None


def job_schemas(value):
    if isinstance(value, list):
        return [job for entry in value for job in job_schemas(entry)]
    if isinstance(value, dict):
        kind = value.get("@type")
        if kind == "JobPosting" or isinstance(kind, list) and "JobPosting" in kind:
            return [value]
        if "@graph" in value:
            return job_schemas(value["@graph"])
    return []


def parse(raw, uri):
    host, native_id, requested_locale = checked_url(uri)
    if not isinstance(raw, bytes) or not raw or len(raw) > 8 * 1024 * 1024:
        raise SourceError("invalid_complete_personio_html")
    try:
        doc = html.fromstring(raw)
    except (ValueError, TypeError, etree.ParserError):
        raise SourceError("invalid_complete_personio_html") from None
    main = one(doc.xpath("//main"), "ambiguous_personio_main")
    primary = one(
        token_nodes(main, "detail-content-block-conditions"),
        "missing_or_competing_personio_primary",
    )
    title = one(token_nodes(main, "job-position-title"), "missing_or_competing_personio_title")
    header = one(token_nodes(main, "job-header"), "missing_or_competing_personio_header")
    canonical = urljoin(
        uri, one(doc.xpath("//link[@rel='canonical']/@href"), "ambiguous_personio_canonical")
    )
    canonical_host, canonical_id, canonical_locale = checked_url(canonical)
    if (canonical_host, canonical_id) != (host, native_id):
        raise SourceError("personio_canonical_identity_differs")
    schemas = []
    for node in doc.xpath("//script[@type='application/ld+json']"):
        schemas.extend(job_schemas(load_json(node.text or "")))
    schema = one(schemas, "missing_or_competing_personio_jobposting")
    identifier = schema.get("identifier")
    value = identifier.get("value") if isinstance(identifier, dict) else None
    match = (
        re.fullmatch(r"([1-9][0-9]{0,19})-([1-9][0-9]{0,19})", value)
        if isinstance(value, str)
        else None
    )
    native_title = " ".join(title.text_content().split())
    if (
        not match
        or match[1] != native_id
        or not native_title
        or not isinstance(schema.get("title"), str)
        or " ".join(schema["title"].split()) != native_title
    ):
        raise SourceError("personio_schema_native_identity_or_title_differs")
    about = token_nodes(main, "detail-content-block-about-us")
    if len(about) > 1:
        raise SourceError("competing_personio_company_context")
    for heading in main.xpath(".//h2"):
        if (
            " ".join(heading.text_content().split()) in {"About us", "Über uns"}
            and heading not in primary.iter()
            and not any(heading in node.iter() for node in about)
        ):
            raise SourceError("unmapped_personio_company_context")
    body = public_html(primary)
    if not body["text"]:
        raise SourceError("empty_personio_primary_description")
    context = [public_html(node) for node in about]
    sections = []
    for node in token_nodes(primary, "jb-description-item"):
        section = public_html(node)
        headings = node.xpath(".//h2|.//h3")
        section["heading"] = " ".join(headings[0].text_content().split()) if headings else None
        sections.append(section)
    schema_body = public_schema_description(schema.get("description"))
    projection = {key: deepcopy(value) for key, value in schema.items() if key in PUBLIC_FIELDS}
    projection["description"] = schema_body["html"]
    return {
        "source": SOURCE,
        "status": "ok",
        "kind": "personio_public_detail",
        "id": "personio::" + host + "::" + native_id,
        "native_job_id": native_id,
        "native_platform_company_id": match[2],
        "native_jobposting_identifier": identifier,
        "title": native_title,
        "url": canonical,
        "source_url": canonical,
        "requested_url": uri,
        "source_board_url": "https://" + host + "/",
        "source_canonical_locale": canonical_locale,
        "requested_description_locale": requested_locale,
        "native_document_language": doc.get("lang"),
        "description": body["html"],
        "description_html": body["html"],
        "source_primary_text": body["text"],
        "native_primary_sections": sections,
        "native_company_context_sections": context,
        "native_company_context_status": "separately_exposed"
        if context
        else "not_exposed_in_current_primary_page",
        "native_header_text": public_html(header)["text"],
        "schema_description": schema_body,
        "source_jobposting_schema": projection,
        "schema_description_used_as_primary": False,
        "native_nontext_media_count": len(primary.xpath(".//img|.//svg|.//video|.//audio")),
        "nontext_media_requirements_verified": False,
        "body_representation": "native_personio_full_primary_html",
        "source_body_untruncated": True,
        "original_published_at": None,
        "returned_count": 1,
        "source_result_count": None,
        "coverage_complete": False,
        "full_posting_reviewed": False,
        "reviewed_by_model": False,
        "credentials_cookies_forms_or_hydration_state_exported": False,
        "source_scripts_media_accounts_or_applications_requested": False,
        "raw_html_sha256": hashlib.sha256(raw).hexdigest(),
        "limits": LIMITS,
    }


def read(uri, *, transport=request):
    checked_url(uri)
    rules, policy = robot_policy(uri, transport=transport)
    if rules is not None and not rules.can_fetch(AGENT, uri):
        raise SourceError("robots_disallowed")
    response = transport(uri, accept="text/html", agent=AGENT)
    if "html" not in str(response.get("content_type", "")).lower():
        raise SourceError("unexpected_personio_content_type")
    result = parse(response["body"], uri)
    result["provenance"] = {
        "requested_at": response.get("requested_at"),
        "observed_at": response.get("observed_at"),
        "robots": policy,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-url", required=True)
    args = parser.parse_args()
    try:
        result = read(args.job_url)
    except SourceError as error:
        result = {
            "source": SOURCE,
            "status": "source_limited",
            "returned_count": None,
            "source_result_count": None,
            "error": error.code,
            "http_status": error.http_status,
            "retry_after": error.retry_after,
            "coverage_complete": False,
            "reviewed_by_model": False,
        }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
