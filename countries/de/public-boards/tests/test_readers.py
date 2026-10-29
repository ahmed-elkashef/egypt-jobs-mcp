"""Synthetic complete-page, clock, native-body and policy contracts."""

import importlib
import json
import sys
from pathlib import Path
from unittest import TestCase, mock
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
r = importlib.import_module("readers")


def static(source, page=1, next_page=2):
    if source == "absolventa":
        return f'<a data-job-offer-target="jobOfferTeaser" id="teaser_job_offer_42" href="/stellenangebote/42-synthetic"><h2>Native title</h2><h2>Native title</h2></a><nav aria-label="Mobile Pagination"><span>{page}</span><span>…</span><a href="/jobs?page={next_page}">{next_page}</a></nav>'.encode()
    return f'<a data-stm-job-id="42" id="job-42" title="Native title" href="/jobs/synthetic-42">Full native card</a><div><a id="job-teasers-select-page-{page}" class="underline" href="/stellenanzeigen?page={page}">{page}</a><a id="job-teasers-select-page-{next_page}" href="/stellenanzeigen?page={next_page}">{next_page}</a></div>'.encode()


def ssr(
    *,
    page=2,
    total=3,
    portal="stanz",
    offset=None,
    keyword="",
    title="Native title",
    identity="SDE-42",
):
    job = {
        "id": identity,
        "positionTitle": title,
        "originalStartDate": "2026-09-14T00:00:00Z",
        "startDate": "2026-10-29T00:00:00Z",
    }
    model = {
        "jobAds": [{"jobAd": job, "isRelevant": True}],
        "count": total,
        "countRelevant": total,
        "offlineJobAds": [],
    }
    state = {
        "searchQuery": {
            "query": {
                "page": page,
                "portal": portal,
                "fulltext": keyword,
                "limit": 1,
                "onlyTopJobs": False,
                "locationIds": [],
            }
        },
        "currentPageParams": {
            "pageParams": {
                "searchParams": {
                    "pageNumber": page,
                    "offset": page - 1 if offset is None else offset,
                    "limit": 1,
                }
            }
        },
        "api": {
            "queries": {
                "synthetic": {
                    "data": {"requests": {"jobSearchResult": {"jobAdSearchResultModel": model}}}
                }
            }
        },
    }
    stream = "1:" + json.dumps({"preloadedState": state}) + "\n"
    flight = (
        "<script>self.__next_f.push("
        + json.dumps([1, stream]).replace("<", r"\u003c")
        + ");</script>"
    )
    path = (
        "/job/synthetic-sde-42/"
        if portal == "stanz"
        else "/job/synthetic-employer/native-title/yf-42/"
    )
    return (
        flight
        + f'<div data-jobid="{identity}"><a data-testid="qa-hitzone" title="{title}" href="{path}"></a><h3>{title}</h3></div>'
    ).encode()


class PublicBoardTests(TestCase):
    def test_static_native_titles_mobile_duplicates_and_actual_next_links(self):
        for source in ["absolventa", "academics"]:
            url = r.ORIGINS[source] + r.LIST_PATHS[source]
            data = r.parse_inventory(source, static(source), url)
            self.assertEqual(data["returned_count"], 1)
            self.assertEqual(data["listings"][0]["title"], "Native title")
            self.assertEqual(data["pagination"]["next_url"], url + "?page=2")
            self.assertFalse(data["coverage_complete"])

    def test_static_page_mismatch_gap_and_foreign_native_link_refused(self):
        url = r.ORIGINS["absolventa"] + "/jobs"
        for body in [
            static("absolventa", page=2),
            static("absolventa", next_page=3),
            static("absolventa").replace(b"/jobs?page=2", b"https://evil.test/jobs?page=2"),
        ]:
            with self.assertRaises(ValueError):
                r.parse_inventory("absolventa", body, url)

    def test_ssr_prefixed_identity_original_and_renewal_clocks_remain_distinct(self):
        data = r.parse_inventory(
            "stellenanzeigen", ssr(), r.ORIGINS["stellenanzeigen"] + "/jobs/?page=2"
        )
        row = data["listings"][0]
        self.assertEqual(row["id"], "SDE-42")
        self.assertEqual(row["native_clock_fields"]["originalStartDate"], "2026-09-14T00:00:00Z")
        self.assertEqual(row["native_clock_fields"]["startDate"], "2026-10-29T00:00:00Z")
        self.assertIsNone(row["original_source_date"])
        self.assertEqual(
            data["pagination"]["next_url"], r.ORIGINS["stellenanzeigen"] + "/jobs/?page=3"
        )
        self.assertFalse(data["pagination"]["next_url_is_provider_emitted_href"])
        self.assertNotIn("country", row)
        self.assertFalse(row["applicant_fit_assessed"])

    def test_ssr_native_terminal_only_when_offset_and_count_reconcile(self):
        data = r.parse_inventory(
            "stellenanzeigen", ssr(page=3, total=3), r.ORIGINS["stellenanzeigen"] + "/jobs/?page=3"
        )
        self.assertIsNone(data["pagination"]["next_url"])
        self.assertFalse(data["coverage_complete"])

    def test_ssr_wrong_offset_page_hidden_keyword_or_portal_not_success(self):
        for body, url in [
            (ssr(offset=0), "/jobs/?page=2"),
            (ssr(page=1), "/jobs/?page=2"),
            (ssr(keyword="marketing"), "/jobs/?page=2"),
            (ssr(portal="yourfirm", identity="YF-42"), "/jobs/?page=2"),
        ]:
            with self.assertRaises(ValueError):
                r.parse_inventory("stellenanzeigen", body, r.ORIGINS["stellenanzeigen"] + url)

    def test_ssr_missing_visible_card_cannot_hide_native_metadata_loss(self):
        body = ssr().replace(b'data-jobid="SDE-42"', b'data-other="SDE-42"')
        with self.assertRaisesRegex(ValueError, "counts disagree"):
            r.parse_inventory(
                "stellenanzeigen", body, r.ORIGINS["stellenanzeigen"] + "/jobs/?page=2"
            )

    def test_native_api_whole_array_and_activation_date_not_original_publication(self):
        jobs = [
            {
                "_id": str(i),
                "jobUrl": "synthetic-" + str(i),
                "name": "Synthetic title",
                "activeFrom": "2026-10-30",
            }
            for i in range(250)
        ]
        data = r.parse_inventory(
            "germantechjobs",
            json.dumps(jobs).encode(),
            r.ORIGINS["germantechjobs"] + "/api/jobsLight",
        )
        self.assertEqual(data["returned_count"], 250)
        self.assertTrue(data["pagination"]["native_whole_array_response"])
        self.assertIsNone(data["listings"][0]["original_source_date"])
        self.assertEqual(data["listings"][0]["activation_clock"], "2026-10-30")

    def test_api_duplicate_identity_or_wrong_detail_slug_refused(self):
        job = {"_id": "same", "jobUrl": "native-slug", "name": "Synthetic"}
        with self.assertRaisesRegex(ValueError, "duplicated"):
            r.parse_inventory(
                "germantechjobs",
                json.dumps([job, job]).encode(),
                r.ORIGINS["germantechjobs"] + "/api/jobsLight",
            )
        with self.assertRaisesRegex(ValueError, "identity"):
            r.parse_detail(
                "germantechjobs",
                json.dumps(job).encode(),
                r.ORIGINS["germantechjobs"] + "/api/jobWithUrl/another-slug",
            )

    def test_full_api_body_includes_requirements_and_responsibilities_beyond_description(self):
        job = {
            "_id": "native-id",
            "jobUrl": "native-slug",
            "name": "Synthetic",
            "description": "Intro only",
            "requirementsMustTextArea": "Required evidence. " * 2000,
            "requirementsNiceTextArea": "Optional evidence",
            "responsibilitiesTextArea": "Complete duties",
        }
        data = r.parse_detail(
            "germantechjobs",
            json.dumps(job).encode(),
            r.ORIGINS["germantechjobs"] + "/api/jobWithUrl/native-slug",
        )
        self.assertGreater(len(data["description"]), 35000)
        self.assertIn("Complete duties", data["description"])
        self.assertEqual(data["native_job"], job)
        self.assertFalse(data["requirements_completeness_verified"])

    def test_full_visible_html_retains_requirements_beyond_schema(self):
        job = {"@type": "JobPosting", "title": "Native title", "description": "Short schema body"}
        for source, container, path in [
            ("absolventa", "internal-job-offer", "/stellenangebote/42-native"),
            ("academics", "job-ad-content", "/jobs/native-42"),
            ("stellenanzeigen", "job-ad-details-widget", "/job/native-42/"),
            ("yourfirm", "job-ad-details-widget", "/job/company/native/yf-42/"),
        ]:
            body = (
                '<script type="application/ld+json">'
                + json.dumps(job)
                + '</script><div id="'
                + container
                + '">'
                + ("All required evidence. " * 2000)
                + "<p>Final requirement</p></div>"
            ).encode()
            data = r.parse_detail(source, body, r.ORIGINS[source] + path)
            self.assertGreater(len(data["description"]), 40000)
            self.assertIn("Final requirement", data["description"])
            self.assertFalse(data["full_posting_reviewed"])

    def test_feed_retains_missing_title_external_route_and_namespace_without_session(self):
        def item(provider, identity, title="Native title", host="www.service.bund.de"):
            return f"<item><title>{title}</title><link>https://{host}/IMPORTE/Stellenangebote/{provider}/2026/10/{identity}.html;jsessionid=SYNTHETIC_ONLY#track=feed-jobs</link><guid>native-{provider}-{identity}</guid><pubDate>Thu, 29 Oct 2026 14:00:00 +0100</pubDate><description>Snippet only</description></item>"

        body = (
            "<rss><channel>"
            + item("editor", "42")
            + item("other", "42", "")
            + item("external", "uuid-ref", host="outside.test")
            + "</channel></rss>"
        ).encode()
        data = r.parse_inventory("bund_de", body, r.ORIGINS["bund_de"] + r.LIST_PATHS["bund_de"])
        self.assertEqual(data["returned_count"], 3)
        self.assertEqual(len({x["id"] for x in data["listings"]}), 3)
        self.assertFalse(data["listings"][1]["title"])
        self.assertTrue(data["listings"][1]["metadata_verification_required"])
        self.assertIsNone(data["listings"][2]["native_detail_url"])
        self.assertNotIn("SYNTHETIC_ONLY", json.dumps(data))
        self.assertTrue(data["pagination"]["retention_or_history_cap_unresolved"])
        self.assertTrue(data["listings"][0]["native_client_fragment_removed"])
        self.assertFalse(data["listings"][0]["source_body_complete"])

    def test_no_arbitrary_actions_keywords_origins_duplicate_queries_or_credentials(self):
        for source, url in [
            ("germantechjobs", "https://germantechjobs.de/api/jobApply"),
            ("germantechjobs", "https://germantechjobs.de/api/newsletter"),
            ("absolventa", "https://www.absolventa.de/jobs?query=HR"),
            ("yourfirm", "https://www.yourfirm.de/stellenangebote/?page=2&page=3"),
            ("academics", "https://user:password@www.academics.de/stellenanzeigen"),
            (
                "bund_de",
                "https://evil.test/Content/Globals/Functions/RSSFeed/RSSGenerator_Stellen.xml",
            ),
        ]:
            with self.assertRaises(ValueError):
                r.checked_url(source, url, "inventory")

    def test_policy_denial_stops_before_the_resource_request(self):
        with mock.patch.object(
            r,
            "fetch",
            return_value=(b"User-agent: *\nDisallow: /\n", "https://www.academics.de/robots.txt"),
        ) as fetch:
            with self.assertRaisesRegex(ValueError, "robots denies"):
                r.read("academics", "inventory", r.ORIGINS["academics"] + "/stellenanzeigen")
            self.assertEqual(fetch.call_count, 1)

    def test_redirect_cannot_switch_page_identity_or_enter_account_route(self):
        source = "absolventa"
        url = r.ORIGINS[source] + "/jobs?page=2"
        for target in [
            r.ORIGINS[source] + "/jobs?page=3",
            r.ORIGINS[source] + "/login",
            "https://evil.test/jobs?page=2",
        ]:
            with self.assertRaises(ValueError):
                r.SafeRedirect(source, "inventory", url).redirect_request(
                    Request(url), None, 302, "Found", {}, target
                )

    def test_unknown_layout_never_becomes_empty_or_complete(self):
        for source in [
            "absolventa",
            "academics",
            "stellenanzeigen",
            "yourfirm",
            "germantechjobs",
            "bund_de",
        ]:
            with self.assertRaises(ValueError):
                r.parse_inventory(
                    source, b"<html>Security check</html>", r.ORIGINS[source] + r.LIST_PATHS[source]
                )

    def test_rate_limit_retains_retry_after_and_never_reports_zero(self):
        from urllib.error import HTTPError

        url = r.ORIGINS["academics"] + "/stellenanzeigen"
        error = HTTPError(url, 429, "Too Many Requests", {"Retry-After": "120"}, None)
        with (
            mock.patch.object(
                sys,
                "argv",
                ["reader", "--source", "academics", "--operation", "inventory", "--url", url],
            ),
            mock.patch.object(r, "read", side_effect=error),
            mock.patch("builtins.print") as output,
        ):
            self.assertEqual(r.main(), 2)
        data = json.loads(output.call_args.args[0])
        self.assertEqual(data["http_status"], 429)
        self.assertEqual(data["retry_after"], "120")
        self.assertIsNone(data["returned_count"])
