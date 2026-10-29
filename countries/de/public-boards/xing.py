"""Original anonymous native XING inventory, taxonomy and full-job parsing."""

import json
import re
import unicodedata
from urllib.parse import parse_qs, urljoin, urlsplit
from xml.etree import ElementTree

from lxml import html
from native_object import crate_object

ORIGIN = "https://www.xing.com"


class XingError(ValueError):
    pass


def checked_url(url, operation):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != "www.xing.com" or parts.fragment:
        raise XingError("Exact anonymous native HTTPS origin required")
    if operation == "detail":
        if not parts.query and re.fullmatch(r"/jobs/[^/]+-[0-9]{6,12}", parts.path):
            return url
        raise XingError("Exact observed numeric native job detail required")
    if operation != "inventory":
        raise XingError("Unsupported anonymous native operation")
    if parts.path.endswith(".xml.gz"):
        if parts.query or not re.fullmatch(
            r"/(?:sitemap\.xml\.gz|jobs/(?:sitemap|[1-9][0-9]*-sitemap|(?:[1-9][0-9]*-)?jobs_(?:admin_area|employment_types)_sitemap)\.xml\.gz)",
            parts.path,
        ):
            raise XingError("Only advertised jobs/objective-taxonomy sitemap routes supported")
        return url
    if not (
        parts.path in {"/jobs/k-student", "/jobs/k-teilzeit"}
        or re.fullmatch(r"/jobs/jobs-in-[a-z0-9-]+", parts.path)
    ):
        raise XingError("Only observed objective location/student/type inventory routes supported")
    query = parse_qs(parts.query, keep_blank_values=True)
    if set(query) - {"page"} or any(len(v) != 1 for v in query.values()):
        raise XingError("Only native page continuation; no career or unknown query fields")
    if "page" in query and not re.fullmatch(r"[1-9][0-9]{0,5}", query["page"][0]):
        raise XingError("Invalid native page")
    return url


def native_id(url):
    checked_url(url, "detail")
    return re.search(r"-([0-9]{6,12})$", urlsplit(url).path)[1]


def resolve(value, cache):
    if isinstance(value, dict) and "__ref" in value:
        result = cache.get(value["__ref"])
        if not isinstance(result, dict):
            raise XingError("Missing native data reference")
        return result
    if isinstance(value, dict):
        return value
    raise XingError("Expected native object/reference")


def job_value(value, cache, seen=None, depth=0):
    """Hydrate selected job-fact references, never the viewer/account graph."""
    if depth > 20:
        raise XingError("Native job-fact graph exceeds its explicit depth")
    seen = set() if seen is None else seen
    if isinstance(value, list):
        return [job_value(item, cache, seen, depth + 1) for item in value]
    if isinstance(value, dict):
        if "__ref" in value:
            reference = value["__ref"]
            if reference in seen:
                raise XingError("Cyclic native job-fact reference")
            target = resolve(value, cache)
            if re.search(r"user|viewer|profile|account", str(target.get("__typename", "")), re.I):
                raise XingError("Account/profile data is not a job fact")
            return job_value(target, cache, seen | {reference}, depth + 1)
        return {
            key: job_value(item, cache, seen, depth + 1)
            for key, item in value.items()
            if not re.search(
                r"tracking|token|image|logo|avatar|visitor|viewer|userInteraction|userProfile|application",
                key,
                re.I,
            )
        }
    return value


def company_name(job, cache):
    info = job.get("companyInfo") or {}
    if not isinstance(info, dict):
        return None
    if info.get("companyNameOverride"):
        return info["companyNameOverride"]
    company = info.get("company")
    if not company:
        return None
    company = resolve(company, cache)
    return company.get("name") or company.get("companyName")


def metadata(job, cache):
    target = urljoin(ORIGIN, job.get("url") or "")
    reference = native_id(target)
    if str(job.get("id", "")).split(".", 1)[0] != reference:
        raise XingError("Native job URL identity differs from its record")
    employment = resolve(job["employmentType"], cache) if job.get("employmentType") else None
    # Whitelist only job facts. Account, profile matching, tracking tokens and
    # signed image/application objects never reach returned metadata.
    return {
        "id": reference,
        "url": target,
        "title": job.get("title"),
        "company": company_name(job, cache),
        "native_location": job_value(job.get("location"), cache),
        "native_locations": job_value(job.get("locations"), cache),
        "native_employment_type": employment,
        "source_active_until": job.get("activeUntil"),
        "source_refreshed_at": job.get("refreshedAt"),
        "original_source_date": None,
        "source_body_complete": False,
        "applicant_fit_assessed": False,
        "model_reconciliation_required": True,
        "native_external_redirect": job.get("redirectsToThirdPartyUrl") is True,
        "external_original_body_verified": False,
    }


def inventory(body, url):
    checked_url(url, "inventory")
    if urlsplit(url).path.endswith(".xml.gz"):
        return discovery(body, url)
    data, unknowns = crate_object(body)
    cache = data.get("serverData", {}).get("APOLLO_STATE", {})
    root = cache.get("ROOT_QUERY", {})
    keys = [k for k in root if k.startswith("jobSearchByQuery(") and k.endswith(")")]
    if len(keys) != 1:
        raise XingError("One native anonymous search response required")
    request = json.loads(keys[0][len("jobSearchByQuery(") : -1])
    query = request.get("query") or {}
    if set(query) - {"location", "filter"}:
        raise XingError("Native keyword or unknown acquisition filters refused")
    if query.get("filter") and set(query["filter"]) - {"employmentType"}:
        raise XingError("Only native objective work-model filters supported")
    location = query.get("location") or {}
    if set(location) - {"radius", "text", "city"}:
        raise XingError("Unverified native location semantics")
    path = urlsplit(url).path
    if path.startswith("/jobs/jobs-in-"):
        label = (
            unicodedata.normalize("NFKD", str(location.get("text") or ""))
            .encode("ascii", "ignore")
            .decode()
            .lower()
        )
        label = re.sub(r"[^a-z0-9]+", "-", label).strip("-")
        if set(query) != {"location"} or label != path.removeprefix("/jobs/jobs-in-"):
            raise XingError("Native location query differs from its requested partition")
    elif path == "/jobs/k-student" and query != {
        "filter": {"employmentType": {"id": ["INTERN.dc571c"]}}
    }:
        raise XingError("Native student-type filter differs from observed source controls")
    result = root[keys[0]]
    echoed = result.get("searchQuery", {}).get("body") or {}
    if echoed.get("keywords"):
        raise XingError("Native search echo contains a career keyword")
    page = int(parse_qs(urlsplit(url).query).get("page", ["1"])[0])
    limit, offset = request.get("limit"), request.get("offset")
    if not isinstance(limit, int) or limit <= 0 or offset != (page - 1) * limit:
        raise XingError("Native range does not match the requested page")
    collection = result.get("collection")
    if not isinstance(collection, list):
        raise XingError("Native search collection missing")
    rows = [metadata(resolve(item.get("jobDetail"), cache), cache) for item in collection]
    if len({row["id"] for row in rows}) != len(rows) or len(rows) > limit:
        raise XingError("Native collection has duplicate identity or invalid range size")
    tree = html.fromstring(body)
    cards = tree.xpath('//article[@data-testid="job-search-result"]')
    dom_ids = []
    for position, card in enumerate(cards):
        targets = {
            re.search(r"-([0-9]{6,12})$", urlsplit(a.get("href")).path)[1]
            for a in card.xpath(".//a[@href]")
            if urlsplit(urljoin(url, a.get("href"))).netloc == "www.xing.com"
            and re.fullmatch(r"/jobs/[^/]+-[0-9]{6,12}", urlsplit(a.get("href")).path)
        }
        if not targets and position < len(rows) and rows[position]["native_external_redirect"]:
            external = {
                urljoin(url, anchor.get("href"))
                for anchor in card.xpath(".//a[@href]")
                if urlsplit(urljoin(url, anchor.get("href"))).netloc != "www.xing.com"
            }
            headings = card.xpath('.//*[@data-testid="job-teaser-list-title"]')
            if (
                len(external) != 1
                or len(headings) != 1
                or " ".join(headings[0].text_content().split()) != rows[position]["title"]
            ):
                raise XingError("Native external primary card identity is not reconciled")
            target = next(iter(external))
            parsed = urlsplit(target)
            if parsed.scheme != "https" or parsed.username or parsed.password:
                raise XingError("Unsafe native external reference")
            rows[position]["native_external_public_url"] = (
                target if not parsed.query and not parsed.fragment else None
            )
            rows[position]["external_route_values_omitted"] = bool(parsed.query or parsed.fragment)
            rows[position]["body_route_status"] = (
                "independent_original_source_policy_and_body_required"
            )
            dom_ids.append(rows[position]["id"])
            continue
        if len(targets) != 1:
            raise XingError("Native primary card identity is ambiguous")
        dom_ids.append(next(iter(targets)))
    if dom_ids != [row["id"] for row in rows]:
        raise XingError("Full native primary cards differ from response records")
    active = tree.xpath('//*[@aria-current="page"]')
    if len(active) != 1 or active[0].text_content().strip() != str(page):
        raise XingError("Native selected page missing or different")
    bounded = result.get("boundedTotal")
    if not isinstance(bounded, dict) or not isinstance(bounded.get("total"), int):
        raise XingError("Native bounded count missing")
    total = bounded["total"]
    if not rows and total != 0:
        raise XingError("No primary records; no verified empty state")
    nexts = {urljoin(url, href) for href in tree.xpath('//a[@rel="next"]/@href')}
    if len(nexts) > 1:
        raise XingError("Conflicting native continuation")
    next_url = next(iter(nexts), None)
    if next_url:
        checked_url(next_url, "inventory")
        if urlsplit(next_url).path != urlsplit(url).path or parse_qs(urlsplit(next_url).query).get(
            "page"
        ) != [str(page + 1)]:
            raise XingError("Native continuation skips page or changes partition")
    unresolved = not next_url and offset + len(rows) < total
    return {
        "listings": rows,
        "returned_count": len(rows),
        "reported_total": total,
        "native_total": result.get("total"),
        "native_bounded_total": bounded,
        "native_acquisition_query": query,
        "native_search_mode": request.get("searchMode"),
        "native_search_echo": echoed,
        "native_undefined_literals_as_unknown": unknowns,
        "pagination": {
            "page": page,
            "offset": offset,
            "limit": limit,
            "next_url": next_url,
            "continuation_unresolved": unresolved,
            "provider_result_cap_reached": unresolved,
            "historical_coverage_verified": False,
        },
        "geography_membership_verified": False,
        "scope": "Literal native location text/radius is not a verified state polygon. Studierende/INTERN enum and source refresh clocks require reconciliation; no country-week or individual-fit claim.",
    }


def discovery(body, url):
    root = ElementTree.fromstring(body)
    if root.tag not in {
        "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex",
        "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset",
    }:
        raise XingError("Whole native sitemap index or URL set required")
    records = []
    for element in root:
        fields = {child.tag.rsplit("}", 1)[-1]: child.text for child in element}
        target = fields.get("loc")
        if (
            not target
            or urlsplit(target).scheme != "https"
            or urlsplit(target).netloc != "www.xing.com"
            or urlsplit(target).query
            or urlsplit(target).fragment
        ):
            raise XingError("Native sitemap URL identity/origin missing")
        records.append({"url": target, "source_last_modified": fields.get("lastmod")})
    if not records or len({row["url"] for row in records}) != len(records):
        raise XingError("Native sitemap entries missing or duplicated")
    return {
        "kind": "source_uri_discovery",
        "discovery_uris": records,
        "returned_uri_count": len(records),
        "native_sitemap_kind": root.tag.rsplit("}", 1)[-1],
        "current_vacancy_status_verified": False,
        "scope": "Advertised URI discovery only. Sitemaps include expired adverts and directory/category routes; counts are never active jobs or an employer census.",
    }


def detail(body, url):
    checked_url(url, "detail")
    data, unknowns = crate_object(body)
    cache = data.get("serverData", {}).get("APOLLO_STATE", {})
    root = cache.get("ROOT_QUERY", {})
    keys = [k for k in root if k.startswith("job(") and k.endswith(")")]
    if len(keys) != 1:
        raise XingError("One native full job response required")
    job = resolve(root[keys[0]], cache)
    facts = metadata(job, cache)
    if facts["id"] != native_id(url):
        raise XingError("Native detail identity differs from request")
    description = job.get("description") or {}
    content = description.get("content") if isinstance(description, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise XingError("Full native description is not available; no snippet fallback")
    tree = html.fromstring(body)
    native = []
    for script in tree.xpath('//script[@type="application/ld+json"]'):
        try:
            value = json.loads(script.text or "")
        except ValueError:
            continue
        if isinstance(value, dict) and value.get("@type") == "JobPosting":
            native.append(value)
    if len(native) != 1:
        raise XingError("One independent native JobPosting required")
    containers = tree.xpath('//div[contains(@class,"html-description__DescriptionContainer")]')
    if len(containers) != 1:
        raise XingError("Full native visible description container required")
    full_text = " ".join(html.fromstring(content).text_content().split())
    visible_text = " ".join(containers[0].text_content().split())
    if not full_text or full_text != visible_text:
        raise XingError("Native description differs from the complete visible container")
    # Drop signed branding images, not the description or job requirements.
    posting = dict(native[0])
    if isinstance(posting.get("hiringOrganization"), dict):
        posting["hiringOrganization"] = {
            k: v for k, v in posting["hiringOrganization"].items() if k != "logo"
        }
    return {
        **facts,
        "description": full_text,
        "description_html": content,
        "native_job_posting": posting,
        "native_body_fields": {
            key: job_value(job.get(key), cache)
            for key in [
                "activatedAt",
                "refreshedAt",
                "activeUntil",
                "careerLevel",
                "discipline",
                "industry",
                "remoteOptions",
                "screenOutCriteria",
            ]
        },
        "native_undefined_literals_as_unknown": unknowns,
        "source_body_untruncated": True,
        "source_body_complete": True,
        "full_posting_reviewed": False,
        "requirements_completeness_verified": False,
    }
