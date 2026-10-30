"""Original personal-use native MeinPraktikum read contracts.

The public client advertises its anonymous REST read route, portal mp and
one-based page increments. Search records group multiple location vacancies.
The current detail template exposes a distinct complete advert container and
native jobPosting fields; neither a URL slug nor a generic source type is fit.
"""

from __future__ import annotations

import copy
import hashlib
import json
from urllib.parse import quote, unquote, urlsplit

from lxml import html
from lxml.etree import ParserError

from network import (
    MEIN,
    MEIN_SEARCH,
    Client,
    SourceError,
    base_result,
    checked_url,
    personal_use,
    positive_page,
    uuid,
)

SCOPES = {
    "internships": ["Auslandspraktikum", "Freiwilliges Praktikum", "Pflichtpraktikum", "Schülerpraktikum", "Abschlussarbeit"],
    "working_student": ["Werkstudent", "Studentische Hilfskraft"],
}
ENTRY = {"internships": MEIN + "/aktuelle-praktikumsplaetze", "working_student": MEIN + "/werkstudent"}
TERMS = MEIN + "/statisch/nutzungsbedingungen"
NATIVE_FIELDS = {
    "id", "companySlug", "companyDisplayName", "companyName", "company_alternative_spellings",
    "company_id", "company_url", "company_logo_url", "createdAt", "culturalfit_matching", "description",
    "division", "division_ids", "employmentStart", "employmentType", "employmentDuration", "industries",
    "is_nation_wide", "is_stale", "job_types", "personality_matching", "premium", "rating", "title", "updatedAt",
    "vacancies", "vacancies_amount", "vacancies_city", "vacancies_country", "vacancies_city_and_state",
    "vacancies_locations", "vacancies_place_id", "vacancies_state", "duration_period", "internship_type",
    "internship_type_value", "internship_categories", "expected_graduation", "apprenticeship_type",
}
DETAIL_FIELDS = {
    "name", "id", "created_at", "external_custom_reference_id", "description", "updated_at", "activated_till",
    "status", "expected_graduation", "duration_options", "salary_type", "profession", "subsidiary", "portal",
    "job_posting_industries", "vacancies", "employment_start_date", "education_condition", "salaries",
    "specific_videos", "general_videos",
}
SCHEMA_FIELDS = {
    "@type", "title", "description", "identifier", "datePosted", "validThrough", "employmentType", "jobLocation",
    "jobLocationType", "applicantLocationRequirements", "workHours", "hiringOrganization", "baseSalary",
    "educationRequirements", "experienceRequirements", "qualifications", "responsibilities", "skills",
}
LIMITS = [
    "Personal noncommercial job-search use only; comply with the source terms. No source dataset is bundled in this code.",
    "Native scope includes broader study models and overseas placements. Read all native pages, retain all locations, then apply actual person/geography/model evidence.",
    "Counts describe grouped source records, not distinct location vacancies, country coverage, a completed week or individual fit.",
    "Source creation, update, activation and observation clocks are distinct; none is promoted to verified original publication.",
    "Generic model labels, office countries, company benefits and remote words do not establish applicant or Germany-based-worker eligibility.",
    "No apply, login, save, account, contact, newsletter, subscription or write-service operation. Source scripts and nontext assets are never executed/requested.",
]


def clean(value):
    return " ".join(value.split())


def public_business_fields(value):
    blocked = {"user", "viewer", "access_token", "refresh_token", "id_token", "api_key", "apikey",
               "password", "authorization", "cookie", "cookies", "session", "session_id", "sessionid",
               "nonce", "csrf", "csrf_token", "headers"}
    if isinstance(value, dict):
        return {key: public_business_fields(item) for key, item in value.items() if key.casefold() not in blocked}
    if isinstance(value, list):
        return [public_business_fields(item) for item in value]
    return value


def vacancy_url(vacancy):
    if not isinstance(vacancy, dict):
        raise SourceError("Native location vacancy is not an object")
    identifier = uuid(vacancy.get("id"))
    slug = vacancy.get("slug")
    if not isinstance(slug, str) or not slug.lower().endswith("-" + identifier):
        raise SourceError("Native vacancy slug and UUID do not reconcile")
    url = MEIN + "/stellen/" + quote(slug, safe="-._~")
    checked_url(url)
    return url


def parse_inventory(native, scope, page):
    if scope not in SCOPES:
        raise SourceError("Unknown native student-market scope")
    positive_page(page)
    if not isinstance(native, dict) or native.get("statusCode") != 200:
        raise SourceError("Native read-service envelope is not a successful search response")
    try:
        hits = native["body"]["hits"]
        total = hits["total"]
        rows = hits["hits"]
    except (KeyError, TypeError):
        raise SourceError("Native search total/rows are missing") from None
    if (
        not isinstance(total, dict) or total.get("relation") != "eq"
        or type(total.get("value")) is not int or total["value"] < 0
        or not isinstance(rows, list)
    ):
        raise SourceError("Unqualified native total relation/count or row shape; no exact-count inference")
    count = total["value"]
    final_page = max(1, (count + 9) // 10)
    if page > final_page:
        raise SourceError("Requested native page is beyond this source scope", source_result_count=count)
    expected = min(10, max(0, count - (page - 1) * 10))
    if len(rows) != expected:
        raise SourceError("Native ten-record page/total contract changed; no clipped or empty success")
    records = []
    for hit in rows:
        source = hit.get("_source") if isinstance(hit, dict) else None
        if not isinstance(source, dict):
            raise SourceError("Complete native grouped source record is missing")
        identifier = uuid(source.get("id"))
        native_vacancies = source.get("vacancies")
        if not isinstance(native_vacancies, list):
            raise SourceError("Native location-vacancy array is missing; no first-location shortcut")
        locations = []
        for vacancy in native_vacancies:
            try:
                url = vacancy_url(vacancy)
                issue = None
            except SourceError as error:
                url, issue = None, str(error)
            locations.append({"native_record": public_business_fields(vacancy), "url": url, "native_route_issue": issue})
        source_data = {key: public_business_fields(value) for key, value in source.items() if key in NATIVE_FIELDS}
        records.append({
            "id": "meinpraktikum::" + identifier, "native_job_group_id": identifier,
            "title": source.get("title"), "company": source.get("companyDisplayName") or source.get("companyName"),
            "native_location_vacancies": locations,
            "source_data": source_data,
            "unprojected_native_field_names": sorted(set(source) - NATIVE_FIELDS),
            "group_not_independent_vacancy_or_approved_candidate": True,
            "native_type_requires_full_role_reconciliation": True,
            "original_published_at": None, "full_posting_reviewed": False, "reviewed_by_model": False,
        })
    more = page < final_page
    result = base_result("meinpraktikum", "student_market_inventory")
    result.update(
        source_url=MEIN_SEARCH, source_board_url=ENTRY[scope], scope=scope,
        native_page=page, native_page_size=10, source_result_count=count,
        source_count_unit="grouped_source_records", returned_count=len(records), metadata=records,
        native_total_relation="eq", native_final_page=final_page,
        has_more=more, next_page=page + 1 if more else None,
        next_request={"tool": "de_public_meinpraktikum_inventory", "backend_native_tool": "meinpraktikum_inventory", "arguments": {
            "scope": scope, "page": page + 1, "personal_noncommercial_use": True,
        }} if more else None,
        role_interest_query_filters=False, all_native_locations_preserved=True,
        original_published_at=None, limits=LIMITS, source_terms_url=TERMS,
    )
    return result


def inventory(scope, page=1, *, personal_noncommercial_use=False, client=None):
    personal_use(personal_noncommercial_use)
    positive_page(page)
    if scope not in SCOPES:
        raise SourceError("Unknown native student-market scope")
    where = {"input": "", "name": "", "lat": None, "lon": None}
    payload = {
        "portal_type": "mp", **where, "type": "jobposting", "what": "", "where": where,
        "radius": 25, "customer": "", "branches": [], "internship_types": SCOPES[scope],
        "sectors": [], "page": page, "state": "",
    }
    response = (client or Client()).post(MEIN_SEARCH, json.dumps(payload).encode())
    # The native read service's POST handler uses HTTP201, with statusCode200
    # in its search envelope. It does not create an application or account.
    if response.status not in {200, 201}:
        raise SourceError("Unqualified native read-service HTTP status", http_status=response.status)
    result = parse_inventory(response.json(), scope, page)
    result.update(native_HTTP_status=response.status, raw_response_sha256=hashlib.sha256(response.body).hexdigest())
    return result


def document(raw):
    try:
        return html.fromstring(raw)
    except (ValueError, TypeError, ParserError) as error:
        raise SourceError("Native advert is not a readable HTML document") from error


def safe_primary(node):
    result = copy.deepcopy(node)
    media = len(result.xpath(".//img|.//video|.//audio|.//iframe|.//object|.//embed"))
    for element in result.xpath(".//script|.//style|.//noscript|.//template|.//form|.//input|.//button|.//select|.//textarea|.//nav|.//svg|.//iframe|.//object|.//embed|.//video|.//audio"):
        element.drop_tree()
    for element in result.xpath('.//*[@id and starts-with(@id,"t-link-")]'):
        element.drop_tree()
    for element in list(result.iter()):
        if not isinstance(element.tag, str):
            parent = element.getparent()
            if parent is not None:
                tail = element.tail or ""
                previous = element.getprevious()
                if previous is None:
                    parent.text = (parent.text or "") + tail
                else:
                    previous.tail = (previous.tail or "") + tail
                parent.remove(element)
            continue
        if element.tag == "img":
            alternative = element.get("alt", "")
            element.tag, element.text = "span", alternative
        element.attrib.clear()
    return result, media


def checked_detail_url(url):
    checked_url(url)
    parts = urlsplit(url)
    if parts.scheme + "://" + parts.netloc != MEIN or not parts.path.startswith("/stellen/"):
        raise SourceError("Only an exact MeinPraktikum public advert URL is supported")
    return url


def parse_detail(raw, url):
    checked_detail_url(url)
    requested_slug = unquote(urlsplit(url).path).removeprefix("/stellen/")
    selected_id = uuid(requested_slug[-36:])
    tree = document(raw)
    scripts = tree.xpath('//script[@id="__NEXT_DATA__" and @type="application/json"]/text()')
    if len(scripts) != 1:
        raise SourceError("Expected one native advert state, not a generic/closed/login page")
    try:
        data = json.loads(scripts[0])
        result = data["props"]["pageProps"]["result"]
        job = result["jobPosting"]
    except (ValueError, KeyError, TypeError):
        raise SourceError("Complete native public jobPosting fields are missing") from None
    if (
        data.get("page") != "/stellen/[vacancySlug]"
        or result.get("vacancySlug") != requested_slug
        or uuid(result.get("vacancyId")) != selected_id
        or not isinstance(job, dict)
    ):
        raise SourceError("Native route/selected vacancy identity does not reconcile")
    group_id = uuid(job.get("id"))
    vacancies = job.get("vacancies")
    if not isinstance(vacancies, list) or selected_id not in {uuid(v.get("id")) for v in vacancies if isinstance(v, dict)}:
        raise SourceError("Selected location vacancy is not part of the native job group")
    title, description = job.get("name"), job.get("description")
    if not isinstance(title, str) or not clean(title) or not isinstance(description, str) or not clean(description):
        raise SourceError("Complete native title and description are required")
    headings = tree.xpath("//h1")
    if len(headings) != 1 or clean(headings[0].text_content()) != clean(title):
        raise SourceError("Visible primary title and native jobPosting title differ")
    # This exact generated component token is independently qualified on both
    # actual layouts. Footer shares the token, so only the h1 ancestor qualifies.
    containers = [parent for parent in headings[0].iterancestors()
                  if parent.tag == "div" and "sc-fa19c2e8-1" in parent.get("class", "").split()]
    if len(containers) != 1:
        raise SourceError("Primary advert container changed; no whole-page or field-only fallback")
    primary, media = safe_primary(containers[0])
    primary_text = clean(primary.text_content())
    if clean(title) not in primary_text or len(primary_text) <= len(clean(title)):
        raise SourceError("Primary public advert text is missing")
    schemas = []
    for text in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            value = json.loads(text)
        except ValueError:
            raise SourceError("Native public source schema is malformed") from None
        for candidate in value if isinstance(value, list) else [value]:
            if isinstance(candidate, dict) and candidate.get("@type") == "JobPosting":
                if not isinstance(candidate.get("title"), str) or clean(candidate["title"]) != clean(title):
                    raise SourceError("Public JobPosting schema title differs from the primary advert")
                schemas.append({key: public_business_fields(value) for key, value in candidate.items() if key in SCHEMA_FIELDS})
    native_job = {key: public_business_fields(value) for key, value in job.items() if key in DETAIL_FIELDS}
    output = base_result("meinpraktikum", "student_market_detail")
    output.update(
        id="meinpraktikum::" + group_id, native_job_group_id=group_id,
        native_selected_vacancy_id=selected_id, native_vacancy_slug=requested_slug,
        url=url, source_url=url, title=title,
        source_primary_text=primary_text, description=primary_text,
        description_html=html.tostring(primary, encoding="unicode"),
        native_role_markdown=description, source_data=native_job, native_source_schemas=schemas,
        body_representation="native_meinpraktikum_complete_public_advert_container",
        source_body_untruncated=True, raw_html_sha256=hashlib.sha256(raw).hexdigest(),
        native_nontext_media_count=media, nontext_media_requirements_verified=False,
        native_media_fields={key: public_business_fields(job.get(key)) for key in ["specific_videos", "general_videos"]},
        native_type_requires_full_role_reconciliation=True,
        application_controls_scripts_hydration_user_or_nonce_exported=False,
        actual_application_form_material_list_verified=False,
        source_terms_url=TERMS, limits=LIMITS, returned_count=1, source_result_count=1,
        original_published_at=None,
    )
    return output


def detail(url, *, personal_noncommercial_use=False, client=None):
    personal_use(personal_noncommercial_use)
    checked_detail_url(url)
    response = (client or Client()).get(url)
    if response.status != 200:
        raise SourceError("Unqualified native public advert HTTP status", http_status=response.status)
    return parse_detail(response.body, url)
