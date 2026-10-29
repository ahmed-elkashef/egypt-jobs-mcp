"""Synthetic source completeness, provenance and denied-route regressions."""

import importlib
import json
import sys
from pathlib import Path
from unittest import TestCase, mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
r = importlib.import_module("readers")
berlin = importlib.import_module("berlin")
englishjobs = importlib.import_module("englishjobs")
jobware = importlib.import_module("jobware")


def next_data(props):
    return (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps({"props": {"pageProps": props}})
        + "</script>"
    ).encode()


def jobs_page(page=1, total=3, keyword="", offset=None):
    query = {
        "condition_group": {"conjunction": "AND", "groups": []},
        "fulltext": {"keys": keyword},
        "language": ["de"],
        "ranges": {"first": page - 1 if offset is None else offset, "last": 1},
    }
    record = {
        "id": page,
        "title": "Synthetic native title",
        "urlNoPrefix": "/job/native-" + str(page),
        "published": "2026-10-29T00:00:00+01:00",
        "formattedPublished": "Heute",
    }
    return next_data(
        {
            "data": {"jobs": {"result_count": total, "pages": [record]}},
            "__APOLLO_STATE__": {"ROOT_QUERY": {"jobs(" + json.dumps(query) + ")": {}}},
        }
    )


JURL = "https://www.jobware.de/job/synthetic-advert-000000123"
IFRAME = "/jobsearch/embed/job/12/000000123/42/index.html"
WRAPPER = (
    '<script type="application/ld+json">'
    + json.dumps(
        {"@type": "JobPosting", "title": "Synthetic ad", "description": "Short structured field"}
    )
    + '</script><iframe src="'
    + IFRAME
    + '"></iframe>'
).encode()


def sitemap(urls):
    return (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(
            "<url><loc>"
            + url
            + "</loc><lastmod>2026-09-01</lastmod><expires>2028-01-01</expires></url>"
            for url in urls
        )
        + "</urlset>"
    ).encode()


def english_page(page=1):
    return (
        '<h1>45 English-speaking jobs in Hesse</h1><div class="pagination"><span aria-current="true">'
        + str(page)
        + '</span><a href="/in/hessen?page='
        + str(page + 1)
        + '">next</a></div><div class="job js-job" id="0123456789abcdef"><a class="js-joblink" href="/clickout/0123456789abcdef?sig=DO_NOT_RETURN_SIG&amp;e=DO_NOT_RETURN_ENCRYPTED"><h3>Synthetic title</h3></a><div>October 29 Working student Frankfurt</div></div>'
    ).encode()


def berlin_page(*, page=1, total=1, count=1, next_page=None):
    nav = (
        '<div><h4>Jobs by category</h4><ul><li><a href="https://berlinstartupjobs.com/finance/">Finance ('
        + str(total)
        + ')</a></li><li><a href="https://berlinstartupjobs.com/engineering/">Engineering (5)</a></li><li><a href="https://berlinstartupjobs.com/new-native-category/">New native category (2)</a></li></ul></div>'
    )
    current = '<span class="page-numbers current">' + str(page) + "</span>" if total > 25 else ""
    continuation = (
        '<a class="next page-numbers" href="/finance/page/' + str(next_page) + '/">Next</a>'
        if next_page
        else ""
    )
    cards = "".join(
        '<li class="bjs-jlid"><h4 class="bjs-jlid__h"><a href="/finance/synthetic-'
        + str(i + 25 * (page - 1))
        + '/">Native title</a></h4><div>Metadata snippet</div></li>'
        for i in range(count)
    )
    return (
        nav + current + continuation + '<ul class="jobs-list-items">' + cards + "</ul>"
    ).encode()


class NextSourcesTests(TestCase):
    def test_jobs_native_last_range_is_count_not_end_offset(self):
        result = r.parse_inventory("jobs_de", jobs_page(3), "https://www.jobs.de/jobs?page=3")
        self.assertEqual(result["pagination"]["offset"], 2)
        self.assertEqual(result["pagination"]["limit"], 1)
        self.assertIsNone(result["pagination"]["next_url"])

    def test_jobs_native_keyword_and_range_mismatch_refused(self):
        for body in [jobs_page(2, keyword="marketing"), jobs_page(2, offset=9)]:
            with self.assertRaises(r.SourceError):
                r.parse_inventory("jobs_de", body, "https://www.jobs.de/jobs?page=2")

    def test_jobs_renewal_label_does_not_become_original_instant(self):
        row = r.parse_inventory("jobs_de", jobs_page(), "https://www.jobs.de/jobs")["listings"][0]
        self.assertIsNone(row["original_source_date"])
        self.assertEqual(row["native_clock_fields"]["formattedPublished"], "Heute")

    def test_jobs_full_body_and_portal_flags_remain_unapproved(self):
        body = next_data(
            {
                "data": {
                    "jobByPath": {
                        "content": {
                            "id": 1,
                            "title": "Native title",
                            "description": "<p>Requirement beyond a card snippet.</p>",
                            "applicationRequireCv": False,
                            "formattedOriginalPublished": "Heute",
                        }
                    }
                }
            }
        )
        result = r.parse_detail("jobs_de", body, "https://www.jobs.de/job/native-1")
        self.assertIn("beyond a card", result["description"])
        self.assertIs(result["native_body_fields"]["applicationRequireCv"], False)
        self.assertFalse(result["requirements_completeness_verified"])
        self.assertFalse(result["full_posting_reviewed"])

    def test_jobs_detail_identity_change_refused(self):
        body = next_data(
            {"data": {"jobByPath": {"content": {"id": 2, "description": "Full body"}}}}
        )
        with self.assertRaises(r.SourceError):
            r.parse_detail("jobs_de", body, "https://www.jobs.de/job/native-1")

    def test_jobware_preserves_leading_zero_and_distinct_clocks(self):
        result = jobware.inventory(sitemap([JURL]))
        row = result["listings"][0]
        self.assertEqual(row["id"], "000000123")
        self.assertIsNone(row["original_source_date"])
        self.assertEqual(row["source_last_modified"], "2026-09-01")
        self.assertIsNone(result["pagination"]["next_url"])
        self.assertFalse(result["pagination"]["historical_coverage_verified"])

    def test_jobware_duplicate_missing_and_wrong_origin_inventory_refused(self):
        for body in [
            sitemap([JURL, JURL]),
            sitemap(["https://outside.invalid/job/x-000000123"]),
            b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url/></urlset>',
        ]:
            with self.assertRaises(jobware.JobwareError):
                jobware.inventory(body)

    def test_jobware_full_iframe_requirements_retained_and_css_removed(self):
        body = b"<html><head><style>SECRET_STYLE</style></head><body><style>BODY_STYLE</style><p>Requirement only in visible iframe.</p><script>DO_NOT_EVALUATE</script></body></html>"
        result = jobware.detail(WRAPPER, JURL, body, "https://www.jobware.de" + IFRAME)
        self.assertIn("only in visible iframe", result["description"])
        self.assertNotIn("STYLE", result["description"])
        self.assertNotIn("DO_NOT_EVALUATE", result["description"])
        self.assertFalse(result["full_posting_reviewed"])

    def test_jobware_wrong_origin_or_ad_identity_iframe_refused(self):
        for wrapper in [
            WRAPPER.replace(IFRAME.encode(), b"https://outside.invalid/" + IFRAME.encode()),
            WRAPPER.replace(b"/000000123/", b"/999999999/"),
        ]:
            with self.assertRaises(jobware.JobwareError):
                jobware.embedded_url(wrapper, JURL)

    def test_jobware_denied_iframe_is_not_requested(self):
        calls = []

        def fetch(source, url, operation, policy=None):
            calls.append(url)
            if operation == "robots":
                return b"User-agent: *\nDisallow: /jobsearch/embed/\n", url
            return WRAPPER, url

        with (
            mock.patch.object(r, "fetch", side_effect=fetch),
            self.assertRaisesRegex(r.SourceError, "denies the native iframe"),
        ):
            r.read("jobware", "detail", JURL)
        self.assertFalse(any("/jobsearch/embed/" in url for url in calls))

    def test_english_native_metadata_pagination_without_signed_values(self):
        result = englishjobs.inventory(english_page(), "https://englishjobs.de/in/hessen")
        text = json.dumps(result)
        self.assertNotIn("DO_NOT_RETURN", text)
        self.assertNotIn("/clickout/", text)
        self.assertEqual(
            result["pagination"]["next_url"], "https://englishjobs.de/in/hessen?page=2"
        )
        self.assertEqual(result["reported_total"], 45)
        self.assertIsNone(result["listings"][0]["original_source_date"])

    def test_english_current_policy_denial_is_metadata_and_no_request(self):
        policy = r.RobotFileParser()
        policy.parse(["User-agent: *", "Disallow: /clickout/"])
        result = englishjobs.inventory(english_page(), "https://englishjobs.de/in/hessen", policy)
        self.assertEqual(
            result["listings"][0]["body_route_status"], "signed_redirect_denied_before_request"
        )
        self.assertFalse(result["listings"][0]["source_body_complete"])

    def test_english_no_detail_or_keyword_acquisition(self):
        with self.assertRaises(englishjobs.EnglishJobsError):
            englishjobs.checked_url("https://englishjobs.de/in/hessen", "detail")
        for url in [
            "https://englishjobs.de/in/hessen?q=marketing",
            "https://englishjobs.de/in/hessen?include=en",
            "https://englishjobs.de/clickout/0123456789abcdef",
        ]:
            with self.assertRaises(englishjobs.EnglishJobsError):
                r.checked_url("englishjobs", url, "inventory")

    def test_english_wrong_native_page_refused(self):
        with self.assertRaises(englishjobs.EnglishJobsError):
            englishjobs.inventory(english_page(), "https://englishjobs.de/in/hessen?page=2")

    def test_berlin_catalogue_retains_every_category_and_new_unknown_routes(self):
        result = berlin.inventory(berlin_page(), "https://berlinstartupjobs.com/")
        self.assertEqual(result["kind"], "german_public_board_partition_catalogue")
        self.assertEqual(len(result["native_partitions"]), 3)
        self.assertFalse(result["native_partitions"][-1]["reader_route_supported"])
        self.assertNotIn("listings", result)
        self.assertFalse(result["featured_homepage_is_complete_inventory"])

    def test_berlin_primary_cards_emitted_next_and_terminal_page(self):
        first = berlin.inventory(
            berlin_page(total=26, count=25, next_page=2), "https://berlinstartupjobs.com/finance/"
        )
        last = berlin.inventory(
            berlin_page(page=2, total=26, count=1), "https://berlinstartupjobs.com/finance/page/2/"
        )
        self.assertEqual(first["returned_count"], 25)
        self.assertEqual(
            first["pagination"]["next_url"], "https://berlinstartupjobs.com/finance/page/2/"
        )
        self.assertIsNone(last["pagination"]["next_url"])
        self.assertNotEqual(first["listings"][0]["id"], last["listings"][0]["id"])

    def test_berlin_truncated_partition_cannot_be_exhausted(self):
        for body in [berlin_page(total=26, count=25), berlin_page(total=26, count=1, next_page=2)]:
            with self.assertRaises(berlin.BerlinError):
                berlin.inventory(body, "https://berlinstartupjobs.com/finance/")

    def test_berlin_full_visible_requirements_beyond_structured_description(self):
        body = (
            '<script type="application/ld+json">'
            + json.dumps(
                {
                    "@type": "JobPosting",
                    "title": "Native job",
                    "description": "Structured requirements",
                    "datePosted": "2026-10-29",
                }
            )
            + '</script><div class="bsj-template__content">Additional complete visible requirements</div>'
        ).encode()
        result = berlin.detail(body, "https://berlinstartupjobs.com/finance/native-job/")
        self.assertIn("Additional complete", result["description"])
        self.assertIsNone(result["original_source_date"])
        self.assertFalse(result["requirements_completeness_verified"])

    def test_all_new_origins_reject_actions_foreign_and_keyword_routes(self):
        for source, url in [
            ("jobs_de", "https://www.jobs.de/jobs?q=hr"),
            ("jobware", JURL + "?apply=1"),
            ("berlinstartupjobs", "https://berlinstartupjobs.com/wp-json/sj/v1/submit-job"),
        ]:
            with self.assertRaises((ValueError, r.SourceError)):
                r.checked_url(source, url, "inventory")


class AdditionalMetadataSafetyTests(TestCase):
    def test_english_duplicate_identity_is_not_two_independent_jobs(self):
        body = english_page()
        start = body.index(b'<div class="job js-job"')
        body += body[start:]
        with self.assertRaises(englishjobs.EnglishJobsError):
            englishjobs.inventory(body, "https://englishjobs.de/in/hessen")

    def test_english_script_tracking_values_do_not_leak_into_card_text(self):
        body = english_page().replace(b"<h3>", b"<script>DO_NOT_EMIT_SCRIPT_TRACKING</script><h3>")
        result = englishjobs.inventory(body, "https://englishjobs.de/in/hessen")
        self.assertNotIn("DO_NOT_EMIT_SCRIPT_TRACKING", json.dumps(result))
