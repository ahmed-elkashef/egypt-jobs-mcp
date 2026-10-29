"""Original anonymous get in Engineering SSR/open-API and complete body reader."""

import json
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

from lxml import html

ORIGIN = "https://www.get-in-engineering.de"
API_PATH = "/api/v2/open/job/search"
LIMIT = 39


class EngineeringError(ValueError):
    pass


def checked_url(url, operation):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "www.get-in-engineering.de" or parts.fragment:
        raise EngineeringError("Exact native public HTTPS origin required")
    query = parse_qs(parts.query, keep_blank_values=True)
    if any(len(value) != 1 for value in query.values()):
        raise EngineeringError("Duplicate native query fields refused")
    if operation == "inventory":
        if parts.path == "/jobsuche" and not parts.query:
            return url
        if parts.path == API_PATH and set(query) == {"start", "limit"}:
            start = query["start"][0]
            if re.fullmatch(r"0|[1-9][0-9]{0,6}", start) and int(start) % LIMIT == 0:
                if query["limit"] == [str(LIMIT)]:
                    return url
        raise EngineeringError("Only whole native inventory and verified39-record open-API offsets")
    if operation == "detail" and re.fullmatch(r"/jobsuche/p[1-9][0-9]*", parts.path):
        if not query:
            return url
        if set(query) == {"start", "limit", "ref"} and query["ref"] == ["Jobsuche"]:
            if query["limit"] == [str(LIMIT)] and re.fullmatch(
                r"0|[1-9][0-9]{0,6}", query["start"][0]
            ):
                if int(query["start"][0]) % LIMIT == 0:
                    return url
    raise EngineeringError("Exact native detail or unfiltered read contract required")


def native_id(url):
    checked_url(url, "detail")
    return urlsplit(url).path.rsplit("/p", 1)[-1]


def next_data(body):
    tree = html.fromstring(body)
    nodes = tree.xpath('//script[@id="__NEXT_DATA__"]')
    if len(nodes) != 1:
        raise EngineeringError("One inert native JSON bootstrap required")
    value = json.loads(nodes[0].text or "")
    return tree, value["props"]


def clean(value):
    return " ".join(value.split())


def metadata(job):
    target = urljoin(ORIGIN, job.get("url") or "")
    reference = native_id(target)
    if str(job.get("id")) != reference or not job.get("title"):
        raise EngineeringError("Native job ID/title/URL disagree")
    company = job.get("company") or {}
    return {
        "id": reference,
        "url": target,
        "title": job["title"],
        "company": company.get("title"),
        "native_source_record": {
            key: job.get(key)
            for key in ("id", "title", "url", "homeOffice", "careers", "locations")
        },
        "original_source_date": None,
        "source_body_complete": False,
        "applicant_fit_assessed": False,
        "model_reconciliation_required": True,
        "germany_remote_eligibility_verified": False,
    }


def inventory(body, url):
    checked_url(url, "inventory")
    api = urlsplit(url).path == API_PATH
    if api:
        payload = json.loads(body)
        jobs, total = payload["items"]["results"], payload["total"]
        offset = int(parse_qs(urlsplit(url).query)["start"][0])
    else:
        tree, props = next_data(body)
        page = props["pageProps"]["pageProps"]
        filters = page.get("filters") or {}
        allowed = {
            "company",
            "degree",
            "studySubject",
            "thematicPriority",
            "city",
            "state",
            "radius",
            "homeOffice",
        }
        if set(filters) != allowed or any(filters[key] for key in allowed - {"radius"}):
            raise EngineeringError("Native narrowed/unknown acquisition filters refused")
        if page.get("start") != 0 or page.get("isDebug") is not False:
            raise EngineeringError("Native SSR state differs from whole first inventory")
        state = props["initialState"]["jobSearchJobs"]
        if state.get("loading") is not False or state.get("errorCode") != 0:
            raise EngineeringError("Native job result is incomplete")
        jobs, total, offset = state["jobs"], state["jobsCount"], 0
        cards = tree.xpath("//a[@data-job-id]")
        if len(cards) != len(jobs) or {node.get("data-job-id") for node in cards} != {
            str(job.get("id")) for job in jobs
        }:
            raise EngineeringError("Native SSR records and every visible primary card disagree")
    if not isinstance(jobs, list) or not jobs or type(total) is not int:
        raise EngineeringError("Unverified empty or malformed native result")
    if total < offset + len(jobs) or len(jobs) > LIMIT:
        raise EngineeringError("Native result count contradicts its request/total")
    if offset + len(jobs) < total and len(jobs) != LIMIT:
        raise EngineeringError("Short native result contradicts continuation")
    rows = [metadata(job) for job in jobs]
    if len({row["id"] for row in rows}) != len(rows):
        raise EngineeringError("Duplicate primary identity in native page")
    next_url = None
    if offset + len(jobs) < total:
        next_url = ORIGIN + API_PATH + "?" + urlencode({"start": offset + LIMIT, "limit": LIMIT})
    return {
        "listings": rows,
        "returned_count": len(rows),
        "reported_total": total,
        "pagination": {
            "offset": offset,
            "limit": LIMIT,
            "next_url": next_url,
            "continuation_basis": "Published anonymous openV2 job/search client, start=page_index*39; live offsets0/39/78 verified. SSR query start is not pagination.",
            "native_request_offset_echo_present": False,
            "historical_coverage_verified": False,
        },
    }


def detail(body, url):
    checked_url(url, "detail")
    tree, props = next_data(body)
    state = props["initialState"]["jobJob"]
    job = state.get("job") or {}
    if state.get("loading") is not False or str(job.get("id")) != native_id(url):
        raise EngineeringError("Complete requested native job is absent")
    if job.get("preview") is not False or job.get("publishState") != "published":
        raise EngineeringError("Native job is not a published public body")
    content = job.get("content")
    if not isinstance(content, str) or not content.strip():
        raise EngineeringError("Full native content absent; no snippet fallback")
    document = html.fromstring("<div>" + content + "</div>")
    sections = document.xpath(".//section[@data-section-id]")
    if (
        not sections
        or len(document) != len(sections)
        or any(clean(value) for value in document.xpath("./text()"))
        or document.xpath(".//script|.//style")
    ):
        raise EngineeringError("Native full content sections absent")
    for section in sections:
        section_id = section.get("data-section-id")
        visible = tree.xpath("//*[@data-section-id=$identity]", identity=section_id)
        if len(visible) != 1 or clean(visible[0].text_content()) != clean(section.text_content()):
            raise EngineeringError("Full native content differs from visible requirements/body")
    postings = []
    for node in tree.xpath('//script[@type="application/ld+json"]'):
        value = json.loads(node.text or "")
        if isinstance(value, dict) and value.get("@type") == "JobPosting":
            postings.append(value)
    if len(postings) != 1 or postings[0].get("url") != ORIGIN + urlsplit(url).path:
        raise EngineeringError("Independent native JobPosting identity absent or different")
    header = job.get("header") or {}
    return {
        "id": native_id(url),
        "title": header.get("title"),
        "native_job": {
            "id": job["id"],
            "header": {
                key: header.get(key)
                for key in ("title", "companyName", "locations", "badges", "homeOffice")
            },
            "jobInfo": job.get("jobInfo"),
            "content": content,
        },
        "native_job_posting": postings[0],
        "description": clean(document.text_content()),
        "description_html": content,
        "source_body_untruncated": True,
        "original_source_date": None,
        "source_schema_date_posted": postings[0].get("datePosted"),
        "model_reconciliation_required": True,
        "full_posting_reviewed": False,
        "requirements_completeness_verified": False,
    }
