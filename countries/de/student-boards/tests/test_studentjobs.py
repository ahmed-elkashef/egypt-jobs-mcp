"""Original synthetic tests for complete acquisition and misleading native metadata."""

import importlib
import json
import sys
from pathlib import Path
from unittest import TestCase, mock
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
s = importlib.import_module("studentjobs")


def page(*, model="", external=True, active=1, next_page=2, total=2):
    selected = " checked" if model else ""
    target = (
        "/vacatures/923-synthetic/redirect_to_external"
        if external
        else "/stellenangebote/923-synthetic"
    )
    return f'''<form action="/stellenangebote"><input type="checkbox" name="{s.MODEL_KEY}" id="model" value="9"{selected}><label for="model">Werkstudentenstelle</label></form>
    <select name="sort_by"><option value="relevancy" selected>Relevancy</option></select>
    <a class="job-opening__item" data-job-opening-id="923" data-job-opening-employment="Werkstudentenstelle" data-job-opening-topjob="true" href="{target}"><h3>Complete synthetic title</h3><p><span class="nyc-icon-location"></span>Swiss location, Switzerland</p><p><span class="nyc-icon-time"></span>10–20 hours</p></a>
    <p>There Are {total} Jobs wurden gefunden</p><ul class="pagination"><li class="-active">{active}</li><li><a href="/stellenangebote?page={next_page}{"&amp;search%5Bjob_types%5D%5Bid%5D%5B%5D=9" if model else ""}">{next_page}</a></li></ul>'''.encode()


def detail():
    job = {
        "@type": "JobPosting",
        "identifier": {"value": "1"},
        "title": "Schema title",
        "description": "Short schema body",
        "employmentType": ["INTERN"],
        "datePosted": "2026-10-19",
    }
    return (
        f'<script type="application/ld+json">{json.dumps(job)}</script><div class="job-opening__title"><h1>Working student native title</h1></div><div class="job-opening__description" itemprop="description"><p>'
        + ("Full native duties. " * 3000)
        + '</p><dl><dt>Jobart</dt><dd itemprop="employmentType">Werkstudentenstelle</dd><dt>Application documents</dt><dd>CV required; motivation not required</dd></dl></div><a href="javascript:alert(1)">Bewerben</a><a href="https://example.test/apply">Jetzt bewerben</a>'
    ).encode()


class StudentBoardsTests(TestCase):
    def test_external_promoted_card_retained_without_fabricated_detail_or_country(self):
        result = s.parse_page("studentjob", page(), s.ORIGINS["studentjob"] + "/stellenangebote")
        row = result["listings"][0]
        self.assertEqual(row["id"], "923")
        self.assertEqual(row["promoted"], "true")
        self.assertIsNone(row["native_detail_url"])
        self.assertTrue(row["external_redirect_url"].endswith("/redirect_to_external"))
        self.assertEqual(row["body_route_status"], "external_source_resolution_required")
        self.assertIn("Switzerland", row["native_fields"]["location"][0])
        self.assertNotIn("country", row)
        self.assertFalse(row["source_body_complete"])
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(
            result["pagination"]["next_url"], s.ORIGINS["studentjob"] + "/stellenangebote?page=2"
        )

    def test_both_source_origins_and_native_model_partition(self):
        for source in s.ORIGINS:
            result = s.parse_page(
                source,
                page(model="9", external=False),
                s.ORIGINS[source] + "/stellenangebote?search%5Bjob_types%5D%5Bid%5D%5B%5D=9",
            )
            self.assertEqual(result["native_selected_model_ids"], ["9"])
            self.assertTrue(result["listings"][0]["native_detail_url"])
            self.assertIn("search%5Bjob_types", result["pagination"]["next_url"])

    def test_missing_selected_model_not_a_successful_filtered_inventory(self):
        with self.assertRaisesRegex(ValueError, "selected model"):
            s.parse_page(
                "studentjob",
                page(),
                s.ORIGINS["studentjob"] + "/stellenangebote?search%5Bjob_types%5D%5Bid%5D%5B%5D=9",
            )

    def test_explicit_sort_requires_actual_native_echo(self):
        body = page().replace(b'<option value="relevancy" selected>', b'<option value="relevancy">')
        with self.assertRaisesRegex(ValueError, "sort"):
            s.parse_page(
                "studentjob",
                body,
                s.ORIGINS["studentjob"] + "/stellenangebote?sort_by=published_date",
            )

    def test_native_continuation_gap_and_active_page_mismatch_refused(self):
        for body in [page(next_page=3), page(active=2)]:
            with self.assertRaises(ValueError):
                s.parse_page("studentjob", body, s.ORIGINS["studentjob"] + "/stellenangebote")

    def test_duplicate_primary_native_identity_and_mismatched_card_id_refused(self):
        body = page()
        start = body.index(b"<a class=")
        end = body.index(b"</a>") + 4
        for value in [
            body + body[start:end],
            body.replace(b'data-job-opening-id="923"', b'data-job-opening-id="924"'),
        ]:
            with self.assertRaises(ValueError):
                s.parse_page("studentjob", value, s.ORIGINS["studentjob"] + "/stellenangebote")

    def test_foreign_link_or_lost_filter_continuation_refused(self):
        for body in [
            page().replace(
                b'href="/stellenangebote?page=2"',
                b'href="https://evil.test/stellenangebote?page=2"',
            ),
            page(model="9").replace(b"&amp;search%5Bjob_types%5D%5Bid%5D%5B%5D=9", b""),
        ]:
            with self.assertRaises(ValueError):
                s.parse_page(
                    "studentjob",
                    body,
                    s.ORIGINS["studentjob"]
                    + "/stellenangebote"
                    + ("?search%5Bjob_types%5D%5Bid%5D%5B%5D=9" if b" checked" in body else ""),
                )

    def test_full_visible_body_retains_requirements_beyond_schema_and_conflicts(self):
        result = s.parse_detail(
            "studentjob", detail(), s.ORIGINS["studentjob"] + "/stellenangebote/923-synthetic"
        )
        self.assertEqual(result["id"], "923")
        self.assertEqual(result["native_job_posting"]["identifier"]["value"], "1")
        self.assertGreater(len(result["description"]), 50000)
        self.assertIn("motivation not required", result["description"])
        self.assertEqual(result["native_model_labels"], ["Werkstudentenstelle"])
        self.assertEqual(result["employment_type"], ["INTERN"])
        self.assertEqual(result["title"], "Working student native title")
        self.assertEqual(result["original_source_date"], "2026-10-19")
        self.assertFalse(result["full_posting_reviewed"])
        self.assertTrue(result["model_reconciliation_required"])
        self.assertEqual(result["apply_urls"], ["https://example.test/apply"])

    def test_unknown_layout_or_schema_only_snippet_never_empty_or_complete(self):
        for body in [
            b"<h1>Security</h1>",
            detail().replace(b'class="job-opening__description"', b'class="unrelated"'),
        ]:
            with self.assertRaises(ValueError):
                s.parse_detail(
                    "youngcapital",
                    body,
                    s.ORIGINS["youngcapital"] + "/stellenangebote/923-synthetic",
                )
        with self.assertRaises(ValueError):
            s.parse_page("studentjob", b"<p>0</p>", s.ORIGINS["studentjob"] + "/stellenangebote")

    def test_query_keyword_credential_action_and_encoded_path_restrictions(self):
        for suffix in [
            "/login",
            "/stellenangebote?search[keywords]=HR",
            "/stellenangebote?page=1&page=2",
            "/stellenangebote?search%5Bjob_types%5D%5Bid%5D%5B%5D=999",
            "/stellenangebote/923-synthetic?token=x",
            "/stellenangebote/923-x%252Flogin",
        ]:
            with self.assertRaises(ValueError):
                s.checked_url("studentjob", s.ORIGINS["studentjob"] + suffix)

    def test_robots_denies_before_native_inventory_or_external_head(self):
        for operation, url in [
            ("page", "/stellenangebote"),
            ("external", "/vacatures/923-synthetic/redirect_to_external"),
        ]:
            with (
                mock.patch.object(
                    s,
                    "fetch",
                    return_value=(
                        b"User-agent: *\nDisallow: /\n",
                        s.ORIGINS["studentjob"] + "/robots.txt",
                    ),
                ) as fetch,
                mock.patch.object(s, "build_opener") as opener,
            ):
                with self.assertRaisesRegex(ValueError, "robots denies"):
                    (
                        s.resolve_external("studentjob", s.ORIGINS["studentjob"] + url)
                        if operation == "external"
                        else s.read("studentjob", operation, s.ORIGINS["studentjob"] + url)
                    )
                self.assertEqual(fetch.call_count, 1)
                opener.assert_not_called()

    def test_source_redirect_cannot_change_model_page_identity_or_origin(self):
        initial = (
            s.ORIGINS["studentjob"]
            + "/stellenangebote?page=2&search%5Bjob_types%5D%5Bid%5D%5B%5D=9"
        )
        for target in [
            s.ORIGINS["studentjob"] + "/stellenangebote?page=2",
            s.ORIGINS["studentjob"]
            + "/stellenangebote?page=3&search%5Bjob_types%5D%5Bid%5D%5B%5D=9",
            "https://evil.test/stellenangebote?page=2",
        ]:
            with self.assertRaises(ValueError):
                s.SafeRedirect("studentjob", initial, "page").redirect_request(
                    Request(initial), None, 302, "Found", {}, target
                )
        url = s.ORIGINS["studentjob"] + "/stellenangebote/923-synthetic"
        with self.assertRaises(ValueError):
            s.SafeRedirect("studentjob", url, "detail").redirect_request(
                Request(url), None, 302, "Found", {}, url.replace("923", "924")
            )
