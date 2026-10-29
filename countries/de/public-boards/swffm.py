"""Original permitted Frankfurt student-portal ads and finite employer discovery."""

import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from lxml import html

ORIGIN = "https://stellenmarkt.swffm.de"
LIST_PATH = "/stellenangebote/"
DETAIL_PATH = r"/anzeige/([1-9][0-9]*)-[a-z0-9-]+"
PROFILE_PATH = r"/unternehmensprofile/detail/[a-z0-9-]+"


class SwffmError(ValueError):
    pass


def clean(value):
    return " ".join(value.split())


def checked_url(url, operation):
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.netloc != "stellenmarkt.swffm.de"
        or parts.query
        or parts.fragment
    ):
        raise SwffmError("Exact public portal HTTPS origin/path without query required")
    if operation == "detail" and re.fullmatch(DETAIL_PATH, parts.path):
        return url
    if operation == "inventory" and (
        parts.path in {"/", LIST_PATH, "/unternehmensprofile"}
        or re.fullmatch(r"/stellenangebote/seite/[1-9][0-9]{0,5}", parts.path)
        or re.fullmatch(PROFILE_PATH, parts.path)
    ):
        return url
    raise SwffmError(
        "Only native whole lists, page links, finite profile discovery or exact ad; no search, Ajax, account or application"
    )


def native_id(url):
    checked_url(url, "detail")
    return re.fullmatch(DETAIL_PATH, urlsplit(url).path)[1]


def whole_main(body):
    tree = html.fromstring(body)
    mains = tree.xpath("//main")
    if len(mains) != 1:
        raise SwffmError("One complete native main required")
    return tree, mains[0]


def clean_main(main):
    for node in main.xpath(".//script|.//style|.//noscript"):
        node.drop_tree()
    return clean(main.text_content())


def ad_references(main, url):
    rows = []
    for node in main.xpath('.//a[starts-with(@href,"/anzeige/")]'):
        target = urljoin(url, node.get("href"))
        rows.append(
            {"id": native_id(target), "url": target, "native_link_text": clean(node.text_content())}
        )
    return rows


def inventory(body, url):
    checked_url(url, "inventory")
    _, main = whole_main(body)
    path = urlsplit(url).path
    if path == "/":
        links = {urljoin(url, href) for href in main.xpath(".//a/@href")}
        # The main navigation can be outside main; inspect links only, never JS.
        tree = html.fromstring(body)
        links.update(urljoin(url, href) for href in tree.xpath("//a/@href"))
        targets = [ORIGIN + LIST_PATH, ORIGIN + "/unternehmensprofile"]
        if not set(targets) <= links:
            raise SwffmError("Native full-list/directory navigation absent")
        return {
            "kind": "german_public_board_partition_catalogue",
            "native_partitions": [{"url": target} for target in targets],
            "featured_job_references": ad_references(main, url),
            "homepage_is_complete_inventory": False,
        }
    if path == "/unternehmensprofile":
        targets = list(
            dict.fromkeys(
                urljoin(url, href)
                for href in main.xpath(
                    './/a[starts-with(@href,"/unternehmensprofile/detail/")]/@href'
                )
            )
        )
        if not targets:
            raise SwffmError("Finite native employer references absent; not an empty census")
        for target in targets:
            checked_url(target, "inventory")
        return {
            "kind": "german_public_board_employer_directory",
            "native_employer_profile_references": targets,
            "native_profile_reference_count": len(targets),
            "complete_employer_census": False,
            "portal_profile_is_every_advertiser": False,
        }
    if re.fullmatch(PROFILE_PATH, path):
        refs = ad_references(main, url)
        headings = [clean(node.text_content()) for node in main.xpath(".//h1|.//h2")]
        text = clean_main(main)
        if not text or not headings:
            raise SwffmError("Whole native employer profile absent")
        return {
            "kind": "german_public_board_employer_profile_context",
            "native_headings": headings,
            "description": text,
            "native_job_references": refs,
            "complete_employer_census": False,
            "native_profile_job_references_are_complete_company_supply": False,
        }
    page = int(path.rsplit("/", 1)[-1]) if "/seite/" in path else 1
    navigations = main.xpath(
        './/ul[contains(concat(" ",normalize-space(@class)," ")," pagination ")]'
    )
    if len(navigations) != 1:
        raise SwffmError("One complete native pagination control required")
    active = navigations[0].xpath(
        './li[contains(concat(" ",normalize-space(@class)," ")," active ")]'
    )
    if len(active) != 1 or clean(active[0].text_content()) != str(page):
        raise SwffmError("Native active page differs from request")
    cards = main.xpath(
        './/div[contains(concat(" ",normalize-space(@class)," ")," job-list-item ")]'
    )
    rows = []
    for card in cards:
        anchors = card.xpath('.//a[starts-with(@href,"/anzeige/")]')
        models = card.xpath(
            './/div[contains(concat(" ",normalize-space(@class)," ")," mt-1 ") and contains(concat(" ",normalize-space(@class)," ")," mb-2 ")]'
        )
        companies = card.xpath(
            './/div[contains(concat(" ",normalize-space(@class)," ")," card-subtitle ")]'
        )
        footers = card.xpath(
            './/div[contains(concat(" ",normalize-space(@class)," ")," card-footer ")]'
        )
        if len(anchors) != 1 or len(models) != 1 or len(companies) != 1 or len(footers) != 1:
            raise SwffmError("Full native card title/model/company/footer structure changed")
        columns = footers[0].xpath(
            './/div[contains(concat(" ",normalize-space(@class)," ")," col-9 ") or contains(concat(" ",normalize-space(@class)," ")," col-3 ")]'
        )
        if len(columns) != 2:
            raise SwffmError("Native city/publication columns missing")
        date_raw = clean(columns[1].text_content())
        date = datetime.strptime(date_raw, "%d.%m.%Y").date().isoformat()
        target = urljoin(url, anchors[0].get("href"))
        rows.append(
            {
                "id": native_id(target),
                "url": target,
                "title": clean(anchors[0].text_content()),
                "company": clean(companies[0].text_content()),
                "native_model_label": clean(models[0].text_content()),
                "native_city": clean(columns[0].text_content()),
                "source_publication_raw": date_raw,
                "source_publication_date": date,
                "original_source_date": None,
                "native_card_text": clean(card.text_content()),
                "source_body_complete": False,
                "model_reconciliation_required": True,
                "applicant_fit_assessed": False,
                "hesse_membership_verified": False,
            }
        )
    if not rows or len(ad_references(main, url)) != len(rows):
        raise SwffmError("Every native primary ad must reconcile; empty state unverified")
    if len({row["id"] for row in rows}) != len(rows):
        raise SwffmError("Duplicate native primary identity needs source reconciliation")
    links = {}
    for node in navigations[0].xpath(
        './li[not(contains(concat(" ",normalize-space(@class)," ")," disabled "))]//a[@href]'
    ):
        target = urljoin(url, node.get("href"))
        checked_url(target, "inventory")
        number = int(urlsplit(target).path.rsplit("/", 1)[-1]) if "/seite/" in target else 1
        links[number] = target
    later = sorted(number for number in links if number > page)
    if later and later[0] != page + 1:
        raise SwffmError("Native continuation has a page gap")
    return {
        "listings": rows,
        "returned_count": len(rows),
        "reported_total": None,
        "pagination": {
            "page": page,
            "native_page_links": links,
            "next_url": links[later[0]] if later else None,
            "continuation_basis": "Actual enabled native page controls; disabled Next root href ignored",
            "historical_coverage_verified": False,
        },
    }


def job_postings(value):
    if isinstance(value, list):
        for item in value:
            yield from job_postings(item)
    elif isinstance(value, dict):
        if value.get("@type") == "JobPosting":
            yield value
        if "@graph" in value:
            yield from job_postings(value["@graph"])


def detail(body, url):
    checked_url(url, "detail")
    tree, main = whole_main(body)
    postings = []
    for node in tree.xpath('//script[@type="application/ld+json"]'):
        postings.extend(job_postings(json.loads(node.text or "")))
    headings = main.xpath(".//h1")
    text = clean_main(main)
    match = re.search(
        r"Anzeigen-Nr\.\s*([0-9]+),\s*veröffentlicht am\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text
    )
    if len(headings) != 1 or not match or match[1] != native_id(url):
        raise SwffmError("Native visible ad ID/title/publication differs from requested ad")
    title = clean(headings[0].text_content())
    if len(postings) > 1 or (postings and clean(postings[0].get("title") or "") != title):
        raise SwffmError("Independent native JobPosting title is ambiguous or different")
    visible_sections = "Stellenbeschreibung" in {
        clean(node.text_content()) for node in main.xpath(".//h3")
    }
    alternatives = main.xpath('.//p[contains(concat(" ",normalize-space(@class)," ")," d-none ")]')
    frames = main.xpath(
        './/div[contains(concat(" ",normalize-space(@class)," ")," dw-pdf-iframe-container ")]'
    )
    pdfs = list(
        dict.fromkeys(
            urljoin(url, href)
            for href in main.xpath(
                './/a[starts-with(@href,"/fileadmin/") and contains(@href,".pdf")]/@href'
            )
        )
    )
    published_pdf_text = (
        len(alternatives) == 1
        and bool(clean(alternatives[0].text_content()))
        and len(frames) == 1
        and bool(pdfs)
    )
    if not visible_sections and not published_pdf_text:
        raise SwffmError(
            "Full native sections or independently published PDF text alternative absent; no snippet/viewer fallback"
        )
    facts = []
    for dl in main.xpath(".//dl"):
        labels, values = dl.xpath("./dt"), dl.xpath("./dd")
        if len(labels) != len(values):
            raise SwffmError("Native fact labels and complete values disagree")
        facts.extend(
            {
                "label": clean(label.text_content()).rstrip(":"),
                "value": clean(value.text_content()),
                "native_links": [
                    {"href": node.get("href"), "text": clean(node.text_content())}
                    for node in value.xpath(".//a[@href]")
                ],
            }
            for label, value in zip(labels, values)
        )
    # Retain source references as inert data. Never hand a consumer an active
    # viewer/object that could fetch a denied PDF when HTML is displayed.
    for node in main.xpath(".//iframe|.//embed|.//object"):
        node.drop_tree()
    return {
        "id": native_id(url),
        "title": title,
        "description": text,
        "description_html": html.tostring(main, encoding="unicode"),
        "native_facts": facts,
        "body_representation": "native_visible_html_sections"
        if visible_sections
        else "native_published_pdf_text_alternative",
        "native_body_fields": {
            "published_pdf_text_alternative": clean(alternatives[0].text_content())
            if published_pdf_text
            else None,
            "independent_schema_description": postings[0].get("description") if postings else None,
        },
        "native_pdf_references": pdfs,
        "native_pdf_verification_complete": False if pdfs else None,
        "pdf_or_viewer_requested": False,
        "native_job_posting": postings[0] if postings else None,
        "structured_native_job_present": bool(postings),
        "source_publication_raw": match[2],
        "source_publication_date": datetime.strptime(match[2], "%d.%m.%Y").date().isoformat(),
        "source_schema_date_posted": postings[0].get("datePosted") if postings else None,
        "original_source_date": None,
        "source_body_untruncated": True,
        "model_reconciliation_required": True,
        "full_posting_reviewed": False,
        "requirements_completeness_verified": False,
        "hesse_membership_verified": False,
    }
