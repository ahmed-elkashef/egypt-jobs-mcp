"""Original personal-research organisation seed readers, never vacancy feeds."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from urllib.parse import urlencode, urljoin

from lxml import html
from lxml.etree import ParserError

from network import (
    GVP,
    GVP_FILTER,
    GVP_PAGE,
    HRK_DOWNLOAD,
    HRK_PAGE,
    Client,
    SourceError,
    base_result,
    personal_use,
    positive_page,
)

COLUMNS = ["Hs-Nr.", "Hochschulkurzname", "Hochschulname", "Hochschultyp", "Trägerschaft", "Bundesland", "Ort (Hausanschrift)", "Home Page"]
LIMITS = [
    "These are organisation discovery records, not vacancies, application candidates, verified workplaces or a national employer census.",
    "An institution's main-address state does not cover all campuses or job locations. Membership does not enumerate all staffing employers.",
    "Native homepage strings are unverified. No scheme/domain repair, career-path guess, account, contact, subscription or application request is made.",
    "The HRK directory permits personal use only; no source dataset is distributed in this code. Other use needs the source's permission.",
    "GVP uses an anonymous public CSRF nonce in memory for its ordinary metadata filter. Protected member details/challenges are never requested or solved. No nonce or session state is exported.",
]


def clean(value):
    return " ".join(value.split())


def parse_higher_education(raw):
    try:
        text = raw.decode("cp1252")
    except UnicodeError:
        raise SourceError("Unqualified native university TXT encoding") from None
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if not reader.fieldnames or len(reader.fieldnames) != 22 or not set(COLUMNS) <= set(reader.fieldnames):
        raise SourceError("Native university TSV header changed; no guessed column positions")
    rows = list(reader)
    if not rows or any(None in row or any(row.get(key) is None for key in COLUMNS) for row in rows):
        raise SourceError("Native complete institution rows are missing or malformed")
    identifiers = []
    records = []
    for row in rows:
        native_id = row["Hs-Nr."]
        if not re.fullmatch(r"[1-9][0-9]{0,6}", native_id) or not clean(row["Hochschulname"]):
            raise SourceError("Native institution identity/name missing")
        identifiers.append(native_id)
        records.append({
            "id": "hochschulkompass::" + native_id, "native_institution_id": native_id,
            "organisation_label": row["Hochschulname"],
            "native_organisation_fields": {key: row[key] for key in COLUMNS},
            "homepage_verified": False, "all_campuses_or_job_geography_verified": False,
            "record_kind": "institution_context_not_vacancy",
        })
    if len(set(identifiers)) != len(identifiers):
        raise SourceError("Duplicate native institution IDs; complete directory needs reconciliation")
    result = base_result("hochschulkompass", "organisation_directory")
    result.update(
        source_url=HRK_DOWNLOAD, source_directory_url=HRK_PAGE,
        directory="higher_education", source_count_unit="institution_rows",
        organisations=records, returned_count=len(records), source_result_count=len(rows),
        native_page=None, has_more=False, next_page=None,
        native_file_rows_preserved=True, source_fields_projection=COLUMNS,
        Hessen_main_address_rows=sum(row["Bundesland"] == "Hessen" for row in rows),
        individual_contact_records_exported=False, personal_use_only=True,
        public_dataset_redistribution_permitted=False,
        decoding="cp1252 native22-column TSV;8 organisational columns projected, no individual contacts",
        raw_directory_sha256=hashlib.sha256(raw).hexdigest(), limits=LIMITS,
    )
    return result


def higher_education(*, personal_noncommercial_use=False, client=None):
    personal_use(personal_noncommercial_use)
    client = client or Client()
    response = client.get(HRK_PAGE)
    if response.status != 200:
        raise SourceError("Official directory download page is unavailable", http_status=response.status)
    try:
        page = html.fromstring(response.body.decode("utf8"))
    except (TypeError, ValueError, UnicodeError, ParserError):
        raise SourceError("Official directory download page changed") from None
    targets = [urljoin(HRK_PAGE, link) for link in page.xpath("//a/@href")]
    text = clean(page.text_content()).casefold()
    if HRK_DOWNLOAD not in targets or "ausschließlich für den persönlichen gebrauch kostenfrei".casefold() not in text:
        raise SourceError("Exact advertised university download/personal-use scope changed; separate qualification required")
    response = client.get(HRK_DOWNLOAD)
    if response.status != 200:
        raise SourceError("Native university TXT is unavailable", http_status=response.status)
    return parse_higher_education(response.body)


def public_bootstrap(raw):
    try:
        text = raw.decode("utf8")
    except UnicodeError:
        raise SourceError("Native public directory bootstrap encoding changed") from None
    matches = re.findall(
        r"const\s+gvp_config\s*=\s*\{\s*rest_url\s*:\s*[\"']([^\"']+)[\"']\s*,\s*nonce\s*:\s*[\"']([A-Za-z0-9]{6,40})[\"']",
        text,
    )
    if len(matches) != 1 or matches[0][0] != GVP + "/wp-json/":
        raise SourceError("Expected one qualified anonymous public directory bootstrap")
    return matches[0][1]  # Only the fixed metadata POST uses this in-memory value.


def parse_staffing(raw, page):
    positive_page(page)
    try:
        native = json.loads(raw)
        if isinstance(native, str):
            native = json.loads(native)
    except (ValueError, UnicodeError):
        raise SourceError("Native public directory JSON encoding changed") from None
    if not isinstance(native, dict) or not {"data", "total_count", "current_count"} <= set(native):
        raise SourceError("Native public directory metadata is missing or limited; no empty success")
    total, current, markup = native["total_count"], native["current_count"], native["data"]
    if type(total) is not int or total < 0 or type(current) is not int or current < 0 or not isinstance(markup, str):
        raise SourceError("Native directory counts/markup are unqualified")
    if re.search(r"<(?:script|form|input)\b", markup, re.I):
        raise SourceError("Directory response contains controls/scripts instead of qualified metadata")
    final_page = max(1, (total + 9) // 10)
    if page > final_page or current != min(10, max(0, total - (page - 1) * 10)):
        raise SourceError("Native directory page/count contract changed or page is out of range")
    try:
        tree = html.fragment_fromstring(markup, create_parent="div")
    except (TypeError, ValueError, UnicodeError, ParserError):
        raise SourceError("Native directory metadata markup is malformed") from None
    entries = tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," memberlist__entry ")]')
    if len(entries) != current:
        raise SourceError("Native directory row/card counts differ")
    records = []
    for entry in entries:
        identifier = entry.get("data-company-id", "")
        headings = entry.xpath(".//h4")
        if not re.fullmatch(r"[1-9][0-9]{0,11}", identifier) or len(headings) != 1:
            raise SourceError("Native directory organisation identity/title is missing")
        label = clean(headings[0].text_content())
        if not label:
            raise SourceError("Native directory organisation title is empty")
        records.append({
            "id": "gvp_staffing::" + identifier, "native_company_id": identifier,
            "organisation_label": label, "native_summary_text": clean(entry.text_content()),
            "source_context_url": GVP_PAGE, "homepage_url": None,
            "homepage_verified": False, "workplace_or_vacancy_geography_verified": False,
            "record_kind": "staffing_member_context_not_vacancy",
        })
    result = base_result("gvp_staffing", "organisation_directory")
    more = page < final_page
    result.update(
        source_url=GVP_FILTER, source_directory_url=GVP_PAGE,
        directory="staffing_members", source_count_unit="member_metadata_rows",
        native_page=page, native_page_size=10, native_final_page=final_page,
        returned_count=current, source_result_count=total, organisations=records,
        has_more=more, next_page=page + 1 if more else None,
        next_request={"tool": "de_public_organisation_directory", "backend_native_tool": "organisation_directory", "arguments": {
            "directory": "staffing_members", "page": page + 1, "personal_noncommercial_use": True,
        }} if more else None,
        anonymous_public_CSRF_nonce_used_in_memory_only=True, nonce_exported=False,
        protected_detail_or_challenge_endpoints_requested_or_solved=False,
        native_response_encoding="JSON string containing native JSON object, or native object; bounded two-layer decoding",
        raw_metadata_response_sha256=hashlib.sha256(raw).hexdigest(), limits=LIMITS,
    )
    return result


def staffing(page=1, *, personal_noncommercial_use=False, client=None):
    personal_use(personal_noncommercial_use)
    positive_page(page)
    client = client or Client()
    bootstrap = client.get(GVP_PAGE)
    if bootstrap.status != 200:
        raise SourceError("Public directory bootstrap is unavailable", http_status=bootstrap.status)
    nonce = public_bootstrap(bootstrap.body)
    body = urlencode({
        "search": "", "zip": "", "city": "", "area": "", "quality": "",
        "listtype": "mitglieder", "branchswitch": "false", "page": str(page),
    }).encode()
    response = client.post(GVP_FILTER, body, "application/x-www-form-urlencoded; charset=UTF-8", nonce)
    if response.status != 200:
        raise SourceError("Native public directory metadata read is limited", http_status=response.status)
    return parse_staffing(response.body, page)


def directory(name, page=1, *, personal_noncommercial_use=False, client=None):
    personal_use(personal_noncommercial_use)
    positive_page(page)
    if name == "higher_education":
        if page != 1:
            raise SourceError("The university directory is one complete native file, not provider pages")
        return higher_education(personal_noncommercial_use=True, client=client)
    if name == "staffing_members":
        return staffing(page, personal_noncommercial_use=True, client=client)
    raise SourceError("Unknown qualified organisation directory")
