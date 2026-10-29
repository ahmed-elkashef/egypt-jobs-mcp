"""Original native EnglishJobs metadata reader; signed redirects are never emitted."""

import re
from urllib.parse import parse_qs, urljoin, urlsplit

from lxml import html

ORIGIN = "https://englishjobs.de"
STATES = [
    "bayern",
    "nordrhein-westfalen",
    "berlin",
    "baden-wuerttemberg",
    "niedersachsen",
    "hessen",
    "rheinland-pfalz",
    "hamburg",
    "thueringen",
    "sachsen",
    "mecklenburg-vorpommern",
    "brandenburg",
    "bremen",
    "schleswig-holstein",
    "sachsen-anhalt",
    "saarland",
]
PATHS = {"/in/" + state for state in STATES} | {"/jobs/student", "/jobs/remote"}


class EnglishJobsError(ValueError):
    pass


def checked_url(url, operation="inventory"):
    p = urlsplit(url)
    if operation != "inventory":
        raise EnglishJobsError(
            "No native full-body route: independently evidence a permitted original employer URL; never bypass a denied signed redirect"
        )
    if (
        p.scheme != "https"
        or p.netloc != "englishjobs.de"
        or p.username
        or p.password
        or p.fragment
        or p.path not in PATHS
    ):
        raise EnglishJobsError(
            "An observed native state/student/remote metadata partition is required"
        )
    q = parse_qs(p.query, keep_blank_values=True)
    if set(q) - {"page"} or any(len(v) != 1 for v in q.values()):
        raise EnglishJobsError(
            "Only actual native page continuation is supported; no career/language keyword fields"
        )
    if "page" in q and not re.fullmatch(r"[1-9][0-9]{0,5}", q["page"][0]):
        raise EnglishJobsError("Invalid native page")
    return url


def inventory(body, url, policy=None, agent="job-market-mcp/0.4.5"):
    checked_url(url)
    tree = html.fromstring(body)
    page = int(parse_qs(urlsplit(url).query).get("page", ["1"])[0])
    navigations = tree.xpath(
        '//*[contains(concat(" ",normalize-space(@class)," ")," pagination ")]'
    )
    active = {
        " ".join(e.text_content().split())
        for nav in navigations
        for e in nav.xpath('.//*[@aria-current="true" or @aria-current="page"]')
    }
    if active != {str(page)}:
        raise EnglishJobsError("Native selected page missing or different from request")
    cards = tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," js-job ")]')
    rows = []
    for node in cards:
        for hidden in node.xpath(".//script|.//style|.//noscript"):
            hidden.drop_tree()
        identity = node.get("id")
        heads = node.xpath(".//h3")
        links = node.xpath('.//a[contains(concat(" ",normalize-space(@class)," ")," js-joblink ")]')
        if (
            not identity
            or not re.fullmatch(r"[a-f0-9]{16}", identity)
            or len(heads) != 1
            or len(links) != 1
        ):
            raise EnglishJobsError("Native primary metadata identity/title/link is ambiguous")
        target = urljoin(url, links[0].get("href", ""))
        p = urlsplit(target)
        if p.netloc != "englishjobs.de" or p.path != "/clickout/" + identity:
            raise EnglishJobsError("Native metadata redirect identity differs")
        allowed = policy.can_fetch(agent, target) if policy is not None else None
        rows.append(
            {
                "id": identity,
                "url": url + "#" + identity,
                "title": " ".join(heads[0].text_content().split()),
                "native_metadata_page": url,
                "native_card_text": " ".join(node.text_content().split()),
                "original_source_date": None,
                "native_detail_url": None,
                "source_body_complete": False,
                "applicant_fit_assessed": False,
                "signed_redirect_present": True,
                "signed_redirect_fields_returned": False,
                "signed_redirect_current_policy_allowed": allowed,
                "body_route_status": "signed_redirect_denied_before_request"
                if allowed is False
                else "original_source_resolution_and_current_policy_required",
            }
        )
    if len({row["id"] for row in rows}) != len(rows):
        raise EnglishJobsError("Duplicate native metadata identity")
    if not rows:
        raise EnglishJobsError("No verified primary records; empty state is not established")
    pages = {}
    for nav in navigations:
        for a in nav.xpath(".//a[@href]"):
            target = urljoin(url, a.get("href"))
            checked_url(target)
            if urlsplit(target).path != urlsplit(url).path:
                raise EnglishJobsError("Native continuation changes source partition")
            n = int(parse_qs(urlsplit(target).query).get("page", ["1"])[0])
            if n in pages and pages[n] != target:
                raise EnglishJobsError("Conflicting native page URLs")
            pages[n] = target
    later = sorted(n for n in pages if n > page)
    if later and later[0] != page + 1:
        raise EnglishJobsError("Native pagination gap")
    titles = [" ".join(h.text_content().split()) for h in tree.xpath("//h1")]
    totals = [
        int(m[1].replace(",", "").replace(".", ""))
        for t in titles
        if (m := re.match(r"^([0-9][0-9,.]*)\s", t))
    ]
    if len(set(totals)) > 1:
        raise EnglishJobsError("Native totals disagree")
    return {
        "listings": rows,
        "returned_count": len(rows),
        "reported_total": totals[0] if totals else None,
        "native_total_labels": titles,
        "source_partition_path": urlsplit(url).path,
        "scope": "One native geography/theme partition. Complete state, remote and unknown-model complements remain required; no national claim from this partition.",
        "pagination": {
            "page": page,
            "native_page_links": pages,
            "next_url": pages[later[0]] if later else None,
            "historical_coverage_verified": False,
        },
        "limits": [
            "Metadata only; signed redirect values are not returned or committed. Denied outbound routes are never requested.",
            "Visible month/day and source theme labels are not invented original instants or proof of contract/country eligibility.",
        ],
    }
