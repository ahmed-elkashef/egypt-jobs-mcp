"""Original anonymous Oracle Candidate Experience reader for qualified sites."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlencode, urlsplit
from urllib.robotparser import RobotFileParser

from lxml import etree, html

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from public_http import MAX_BYTES, SourceError, load_json, request  # noqa: E402

ORIGIN = "https://jpmc.fa.oraclecloud.com"
SITE = "CX_1001"
BOARD = ORIGIN + "/hcmUI/CandidateExperience/en/sites/" + SITE + "/jobs"
API = ORIGIN + "/hcmRestApi/resources/latest/"
PAGE_SIZE = 25
COUNTRIES = {"DE": "300000000289216"}
SECTIONS = ["ExternalDescriptionStr", "ExternalResponsibilitiesStr",
            "ExternalQualificationsStr", "CorporateDescriptionStr", "OrganizationDescriptionStr"]
PUBLIC_FIELDS = {
    "Id", "Title", "Category", "RequisitionType", "RequisitionId", "JobLevel", "JobSchedule",
    "JobShift", "StudyLevel", "InternationalTravelRequired", "ContractType", "JobFamilyId",
    "GeographyId", "GeographyNodeId", "ExternalPostedStartDate", "ExternalPostedEndDate",
    "ContentLocale", "PrimaryLocation", "PrimaryLocationCountry", "ExternalContactName",
    "ExternalContactEmail", "JobFunctionCode", "WorkplaceTypeCode", "WorkplaceType",
    "OtherRequisitionTitle", "NumberOfOpenings", "Organization", "BusinessUnitId",
    "LegalEmployerId", "OrganizationId", "WorkerType", "JobType", "WorkMonths", "WorkYears",
    "WorkHours", "WorkDays", "LegalEmployer", "BusinessUnit", "Department",
    "DomesticTravelRequired", "JobFunction", "secondaryLocations", "media", "workLocation",
    "otherWorkLocations", "requisitionFlexFields", "primaryLocationCoordinates", "skills",
    "ShortDescriptionStr", *SECTIONS,
}
LIMITS = [
    "Only the independently qualified JPMC external site CX_1001 is supported. Other sites, employers and Oracle career fronts require separate qualification.",
    "The wrapper count/hasMore/limit describe search containers, not vacancies. Pagination uses the one search item's TotalJobsCount, Limit, Offset and complete requisitionList.",
    "Whole-site and native Germany location partitions retain all roles. The global inventory is a complement for unresolved remote eligibility, not proof of permission to work from Germany.",
    "The native default RELEVANCY order is retained; it is not a publication-time ordering. A frozen first total and unique identities are required to reconcile continuation.",
    "Public primary, responsibilities, qualifications, corporate and organization sections are preserved separately. Internal description fields, hiring-manager fields and application controls are not exported or used.",
    "External posting dates, requisition type, schedules and contract labels remain raw. They do not prove original publication, student eligibility, remote permission, fit or historical weekly coverage.",
    "RFC9309 section 2.3.1.3 treats this qualified origin's unavailable robots resource separately from content. Actual job/API denial, throttling, malformed rules or unreachable policy stops the read.",
    "No account, candidate identifier, credential, cookie, script execution, application, preview, alert, recommendation, contact or subscription operation is supported.",
]


def integer(value, code, *, minimum=0, maximum=1000000):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise SourceError(code)
    return value


def scope(board_url, country=None, page=1, first_page_total=None):
    if board_url != BOARD:
        raise SourceError("unverified_oracle_board")
    if country is not None and country not in COUNTRIES:
        raise SourceError("unverified_native_country_partition")
    integer(page, "invalid_native_page", minimum=1, maximum=10000)
    if first_page_total is not None:
        integer(first_page_total, "invalid_first_page_total")
    if page > 1 and first_page_total is None:
        raise SourceError("continuation_requires_frozen_first_page_total")
    if page > 1 and (page - 1) * PAGE_SIZE >= first_page_total:
        raise SourceError("native_page_outside_frozen_inventory")


def inventory_uri(board_url, *, country=None, page=1, first_page_total=None):
    scope(board_url, country, page, first_page_total)
    finder = f"findReqs;siteNumber={SITE},facetsList=NONE,limit={PAGE_SIZE},offset={(page - 1) * PAGE_SIZE}"
    if country is not None:
        finder += ",locationId=" + COUNTRIES[country]
    return API + "recruitingCEJobRequisitions?" + urlencode({
        "onlyData": "true", "expand": "requisitionList.secondaryLocations", "finder": finder,
    })


def job_identity(value):
    if (not isinstance(value, str) or value != value.strip() or len(value) > 4096
            or any(ord(c) < 32 for c in value)):
        raise SourceError("invalid_native_oracle_job_uri")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise SourceError("invalid_native_oracle_job_uri") from None
    prefix = "/hcmUI/CandidateExperience/en/sites/" + SITE + "/job/"
    match = re.fullmatch(re.escape(prefix) + r"([1-9][0-9]{5,19})", parsed.path)
    if (parsed.scheme + "://" + parsed.netloc != ORIGIN or not match or parsed.query or parsed.fragment
            or unquote(parsed.path) != parsed.path):
        raise SourceError("unverified_native_oracle_job_uri")
    return match[1]


def job_uri(native_id):
    if not isinstance(native_id, str) or not re.fullmatch(r"[1-9][0-9]{5,19}", native_id):
        raise SourceError("invalid_native_oracle_job_id")
    return BOARD[:-4] + "job/" + native_id


def detail_uri(job_url):
    native_id = job_identity(job_url)
    return API + "recruitingCEJobRequisitionDetails?" + urlencode({
        "expand": "all", "onlyData": "true",
        "finder": f'ById;Id="{native_id}",siteNumber={SITE}',
    })


def search_item(raw):
    data = load_json(raw)
    if (not isinstance(data, dict) or type(data.get("count")) is not int or data.get("count") != 1
            or data.get("hasMore") is not False or not isinstance(data.get("items"), list)
            or len(data["items"]) != 1 or not isinstance(data["items"][0], dict)):
        raise SourceError("missing_or_conflicting_native_oracle_container")
    return data["items"][0]


def parse_inventory(raw, board_url, *, country=None, page=1, first_page_total=None):
    scope(board_url, country, page, first_page_total)
    item = search_item(raw)
    total = integer(item.get("TotalJobsCount"), "invalid_native_job_total")
    offset = integer(item.get("Offset"), "invalid_native_job_offset")
    limit = integer(item.get("Limit"), "invalid_native_job_limit", minimum=1)
    if (item.get("SiteNumber") != SITE or item.get("Facets") != "NONE"
            or item.get("LocationId") != COUNTRIES.get(country)
            or item.get("SortBy") != "RELEVANCY" or offset != (page - 1) * PAGE_SIZE
            or limit != PAGE_SIZE or first_page_total is not None and total != first_page_total):
        raise SourceError("native_oracle_scope_count_or_page_changed")
    prohibited = ["Keyword", "CorrectedKeyword", "SuggestedKeyword", "CandidateNumber",
                  "Location", "Latitude", "Longitude", "WorkplaceType",
                  "SelectedTitlesFacet", "SelectedCategoriesFacet", "SelectedPostingDatesFacet",
                  "SelectedLocationsFacet", "JobFamilyId", "PostingStartDate", "PostingEndDate",
                  "SelectedWorkLocationsFacet", "RequisitionId", "WorkLocationZipCode",
                  "WorkLocationCountryCode", "SelectedFlexFieldsFacets", "OrganizationId",
                  "SelectedOrganizationsFacet", "UserTargetFacetName", "UserTargetFacetInputTerm",
                  "HotJobFlag", "SelectedWorkplaceTypesFacet"]
    if any(item.get(key) not in (None, "") for key in prohibited):
        raise SourceError("unexpected_native_oracle_filter_or_candidate_context")
    if item.get("Radius", 0) != 0 or isinstance(item.get("Radius"), bool):
        raise SourceError("unexpected_native_oracle_radius")
    rows = item.get("requisitionList")
    if not isinstance(rows, list) or len(rows) != min(PAGE_SIZE, max(0, total - offset)):
        raise SourceError("native_oracle_page_incomplete")
    listings, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("Title"), str) or not row["Title"].strip():
            raise SourceError("missing_native_oracle_row_metadata")
        native_id = row.get("Id")
        url = job_uri(native_id)
        if native_id in seen:
            raise SourceError("duplicate_native_oracle_identity")
        seen.add(native_id)
        listings.append({
            "id": ORIGIN + "::" + SITE + "::" + native_id, "native_job_id": native_id,
            "title": row["Title"], "url": url, "native_row": row,
            "location": row.get("PrimaryLocation"), "native_primary_country": row.get("PrimaryLocationCountry"),
            "native_secondary_locations": row.get("secondaryLocations"),
            "native_posted_date": row.get("PostedDate"), "original_published_at": None,
            "full_posting_reviewed": False,
        })
    more = offset + len(rows) < total
    return {
        "status": "ok", "source": "oracle", "kind": "oracle_ce_native_inventory",
        "board_url": BOARD, "site_number": SITE, "country": country,
        "requested_uri": inventory_uri(BOARD, country=country, page=page, first_page_total=first_page_total),
        "page": page, "native_offset": offset, "native_limit": limit, "native_sort": item["SortBy"],
        "returned_count": len(rows), "source_result_count": total,
        "first_page_total": total if page == 1 else first_page_total,
        "has_more": more, "next_page": page + 1 if more else None,
        "next_uri": inventory_uri(BOARD, country=country, page=page + 1, first_page_total=total) if more else None,
        "native_search_fields": {key: value for key, value in item.items() if not isinstance(value, (list, dict))},
        "listings": listings, "original_clock_qualified": False,
        "credentials_exported_or_used": False, "coverage_complete": False, "limits": LIMITS,
    }


def section(value):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise SourceError("invalid_native_oracle_public_description")
    try:
        doc = html.fragment_fromstring(value or " ", create_parent="section")
    except (ValueError, TypeError, etree.ParserError):
        raise SourceError("invalid_native_oracle_public_html") from None
    for child in doc.xpath(".//script|.//style|.//iframe|.//object|.//embed|.//form|.//input"):
        child.drop_tree()
    for child in doc.iter():
        for name in list(child.attrib):
            if (name.lower().startswith(("on", "data-"))
                    or name.lower() in {"href", "src"} and re.match(r"\s*(?:javascript|vbscript|data):", child.attrib[name], re.I)):
                del child.attrib[name]
        if child.tag in {"p", "li", "div", "br", "h1", "h2", "h3", "h4", "section", "tr", "td", "ul", "ol"}:
            child.text, child.tail = " " + (child.text or ""), " " + (child.tail or "")
    return {"text": " ".join(doc.text_content().split()),
            "html": html.tostring(doc, encoding="unicode", method="html")}


def parse_detail(raw, job_url):
    native_id = job_identity(job_url)
    item = search_item(raw)
    if item.get("Id") != native_id or not isinstance(item.get("Title"), str) or not item["Title"].strip():
        raise SourceError("native_oracle_detail_identity_conflict")
    native_requisition = integer(item.get("RequisitionId"), "invalid_native_oracle_requisition_id", minimum=1, maximum=10**20)
    if any(key not in item for key in SECTIONS):
        raise SourceError("missing_native_oracle_public_description_sections")
    sections = {key: section(item[key]) for key in SECTIONS}
    primary = sections["ExternalDescriptionStr"]
    if len(primary["text"]) < 100:
        raise SourceError("missing_complete_native_oracle_primary_body")
    return {
        "status": "ok", "source": "oracle", "kind": "oracle_ce_native_detail",
        "id": ORIGIN + "::" + SITE + "::" + native_id, "native_job_id": native_id,
        "native_requisition_id": native_requisition, "site_number": SITE, "url": job_url,
        "title": item["Title"], "description": primary["text"], "description_html": primary["html"],
        "native_public_sections": sections, "native_public_fields": {k: v for k, v in item.items() if k in PUBLIC_FIELDS},
        "omitted_internal_or_nonpublic_field_names": sorted(set(item) - PUBLIC_FIELDS),
        "native_description_characters": len(primary["text"]), "source_body_untruncated": True,
        "original_published_at": None, "full_posting_reviewed": False,
        "credentials_exported_or_used": False, "coverage_complete": False, "limits": LIMITS,
    }


def policy(url, transport):
    try:
        response = transport(ORIGIN + "/robots.txt", accept="text/plain", bound=256 * 1024)
    except SourceError as error:
        if error.http_status in {403, 404, 410} and not error.retry_after:
            return {"robots_status": error.http_status, "basis": "RFC9309 2.3.1.3: unavailable robots resource; content denials are not bypassed."}
        raise SourceError("robots_unavailable_or_denied", http_status=error.http_status, retry_after=error.retry_after) from None
    if response.get("http_status", 200) != 200:
        raise SourceError("robots_unavailable_or_denied", http_status=response["http_status"])
    try:
        raw = response["body"].decode("utf-8-sig")
    except (KeyError, UnicodeDecodeError):
        raise SourceError("invalid_robots_response") from None
    if "<html" in raw.lower() or "<!doctype" in raw.lower():
        raise SourceError("invalid_robots_response")
    rules = RobotFileParser()
    rules.parse(raw.splitlines())
    if not rules.can_fetch("job-market-mcp", url):
        raise SourceError("robots_denied")
    return {"robots_status": 200, "allowed": True}


def read(*, board_url=None, job_url=None, country=None, page=1, first_page_total=None, transport=request):
    if (board_url is None) == (job_url is None):
        raise SourceError("require_exactly_one_native_oracle_read")
    if board_url is not None:
        url = inventory_uri(board_url, country=country, page=page, first_page_total=first_page_total)
    else:
        if country is not None or page != 1 or first_page_total is not None:
            raise SourceError("inventory_arguments_not_valid_for_detail")
        url = detail_uri(job_url)
    rules = policy(url, transport)
    response = transport(url, accept="application/json", timeout=20)
    if response.get("http_status", 200) != 200 or "json" not in (response.get("content_type") or "").lower():
        raise SourceError("unexpected_native_oracle_response")
    result = (parse_inventory(response["body"], board_url, country=country, page=page, first_page_total=first_page_total)
              if board_url is not None else parse_detail(response["body"], job_url))
    return {**result, "policy": rules, "provenance": {
        "requested_url": url, "method": "GET", "http_status": 200, "bytes": len(response["body"]),
        "sha256": hashlib.sha256(response["body"]).hexdigest(),
        "requested_at": response.get("requested_at"), "observed_at": response.get("observed_at"),
    }}


def capabilities():
    return {
        "status": "ok", "source": "oracle", "operations": ["inventory", "detail"],
        "independently_verified_boards": [BOARD], "native_country_location_partitions": COUNTRIES,
        "native_page_size": PAGE_SIZE, "max_complete_response_bytes": MAX_BYTES,
        "acquisition_role_filters": [], "coverage_complete": False, "limits": LIMITS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--board-url")
    parser.add_argument("--job-url")
    parser.add_argument("--country", choices=sorted(COUNTRIES))
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--first-page-total", type=int)
    args = parser.parse_args()
    try:
        result = capabilities() if args.capabilities else read(
            board_url=args.board_url, job_url=args.job_url, country=args.country,
            page=args.page, first_page_total=args.first_page_total)
        print(json.dumps(result, ensure_ascii=False))
    except (SourceError, ValueError, TypeError) as error:
        print(json.dumps({
            "status": "source_limited", "source": "oracle", "error": getattr(error, "code", "invalid_native_oracle_data"),
            "http_status": getattr(error, "http_status", None), "retry_after": getattr(error, "retry_after", None),
            "returned_count": None, "source_result_count": None, "coverage_complete": False, "limits": LIMITS,
        }))


if __name__ == "__main__":
    main()
