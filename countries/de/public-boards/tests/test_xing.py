"""Synthetic native XING scope, full-field and immutable URI capture regressions."""

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
x = importlib.import_module("xing")
n = importlib.import_module("native_object")
c = importlib.import_module("source_capture")
URL = "https://www.xing.com/jobs/native-title-123456"


def script(data):
    return (
        '<script id="runtime-config">window.crate='
        + json.dumps(data).replace("<", r"\u003c")
        + ";</script>"
    )


def native_page(page=1, total=3, next_page=2, external=False, keyword=False):
    job = {
        "__typename": "VisibleJob",
        "id": "123456.synthetic",
        "title": "Native title",
        "url": URL,
        "activeUntil": "2027-01-01T00:00:00Z",
        "refreshedAt": "2026-10-29T00:00:00Z",
        "location": {"city": "Hessen"},
        "locations": [{"city": "Hessen"}],
        "employmentType": {"localizationValue": "Studierende"},
        "companyInfo": {"company": {"__ref": "Company:42"}},
        "redirectsToThirdPartyUrl": external,
        "userInteractions": {"secret": "DO_NOT_EMIT_INTERACTION"},
    }
    request = {
        "limit": 1,
        "offset": page - 1,
        "query": {"location": {"text": "Hessen", "radius": 20}},
        "searchMode": "SEMANTIC",
    }
    if keyword:
        request["query"]["keywords"] = "marketing"
    result = {
        "total": -1,
        "boundedTotal": {"total": total, "bound": 2, "countType": "EXACT"},
        "trackingToken": "DO_NOT_EMIT_TRACKING",
        "collection": [{"jobDetail": {"__ref": "VisibleJob:123456"}}],
        "searchQuery": {"body": {"keywords": None}},
    }
    cache = {
        "ROOT_QUERY": {"jobSearchByQuery(" + json.dumps(request) + ")": result},
        "VisibleJob:123456": job,
        "Company:42": {
            "__typename": "Company",
            "name": "Native employer",
            "logo": "https://images.invalid/a?signature=DO_NOT_EMIT_LOGO",
        },
    }
    data = {"serverData": {"APOLLO_STATE": cache}, "viewer": {"private": "DO_NOT_EMIT_VIEWER"}}
    target = (
        "https://external.invalid/public-job/42?signature=DO_NOT_EMIT_EXTERNAL" if external else URL
    )
    card = (
        '<article data-testid="job-search-result"><a href="'
        + target
        + '"></a><h2 data-testid="job-teaser-list-title">Native title</h2></article>'
    )
    nav = '<button aria-current="page">' + str(page) + "</button>"
    if next_page:
        nav += '<a rel="next" href="/jobs/jobs-in-hessen?page=' + str(next_page) + '">Next</a>'
    return (script(data) + card + nav).encode()


def full_detail():
    description = "<p>Complete native requirements beyond a snippet.</p>"
    job = {
        "__typename": "VisibleJob",
        "id": "123456.synthetic",
        "url": URL,
        "title": "Native title",
        "description": {"content": description},
        "careerLevel": {"__ref": "CareerLevel:1"},
        "employmentType": {"localizationValue": "Studierende"},
        "companyInfo": {},
        "locations": [],
    }
    cache = {
        "ROOT_QUERY": {'job({"id":"123456"})': {"__ref": "VisibleJob:123456"}},
        "VisibleJob:123456": job,
        "CareerLevel:1": {"__typename": "CareerLevel", "localizationValue": "Student"},
    }
    posting = {
        "@type": "JobPosting",
        "title": "Native title",
        "description": description,
        "employmentType": "FULL_TIME",
        "hiringOrganization": {
            "name": "Native company",
            "logo": "https://images.invalid/a?signature=DO_NOT_EMIT_LOGO",
        },
    }
    return (
        script({"serverData": {"APOLLO_STATE": cache}})
        + '<script type="application/ld+json">'
        + json.dumps(posting)
        + '</script><div class="html-description__DescriptionContainer">'
        + description
        + "</div>"
    ).encode()


class NativeObjectTests(TestCase):
    def test_undefined_is_unknown_without_changing_quoted_text(self):
        data, count = n.crate_object(
            b'<script id="runtime-config">window.crate={"missing":undefined,"text":"undefined"};</script>'
        )
        self.assertEqual(count, 1)
        self.assertIsNone(data["missing"])
        self.assertEqual(data["text"], "undefined")

    def test_executable_nonfinite_or_trailing_expressions_refused(self):
        for value in [
            '{"x":function(){return 1}}',
            '{"x":NaN}',
            '{"x":Infinity}',
            '{"x":1};doSomething()',
        ]:
            with self.assertRaises(n.NativeObjectError):
                n.crate_object(
                    ('<script id="runtime-config">window.crate=' + value + "</script>").encode()
                )

    def test_missing_duplicate_or_wrong_declaration_is_not_empty_data(self):
        for body in [
            b"<html/>",
            b'<script id="runtime-config">other={};</script>',
            (script({}) + script({})).encode(),
        ]:
            with self.assertRaises(n.NativeObjectError):
                n.crate_object(body)


class XingNativeTests(TestCase):
    def test_complete_primary_metadata_and_actual_next_without_tracking(self):
        result = x.inventory(native_page(), "https://www.xing.com/jobs/jobs-in-hessen")
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["native_total"], -1)
        self.assertEqual(result["reported_total"], 3)
        self.assertEqual(
            result["pagination"]["next_url"], "https://www.xing.com/jobs/jobs-in-hessen?page=2"
        )
        self.assertNotIn("DO_NOT_EMIT", json.dumps(result))
        self.assertFalse(result["geography_membership_verified"])

    def test_native_cap_cannot_become_exhausted_supply(self):
        result = x.inventory(
            native_page(page=2, total=5, next_page=None),
            "https://www.xing.com/jobs/jobs-in-hessen?page=2",
        )
        self.assertIsNone(result["pagination"]["next_url"])
        self.assertTrue(result["pagination"]["continuation_unresolved"])
        self.assertTrue(result["pagination"]["provider_result_cap_reached"])

    def test_wrong_page_or_native_keyword_refused(self):
        with self.assertRaises(x.XingError):
            x.inventory(native_page(), "https://www.xing.com/jobs/jobs-in-hessen?page=2")
        with self.assertRaises(x.XingError):
            x.inventory(native_page(keyword=True), "https://www.xing.com/jobs/jobs-in-hessen")

    def test_wrong_location_echo_not_another_partition(self):
        with self.assertRaises(x.XingError):
            x.inventory(native_page(), "https://www.xing.com/jobs/jobs-in-berlin")

    def test_external_primary_cards_survive_without_signed_values(self):
        result = x.inventory(native_page(external=True), "https://www.xing.com/jobs/jobs-in-hessen")
        row = result["listings"][0]
        self.assertTrue(row["native_external_redirect"])
        self.assertIsNone(row["native_external_public_url"])
        self.assertTrue(row["external_route_values_omitted"])
        self.assertNotIn("DO_NOT_EMIT", json.dumps(result))

    def test_foreign_native_looking_url_cannot_impersonate_identity(self):
        body = native_page().replace(
            URL.encode(), b"https://outside.invalid/jobs/native-title-123456", 1
        )
        with self.assertRaises(x.XingError):
            x.inventory(body, "https://www.xing.com/jobs/jobs-in-hessen")

    def test_full_native_visible_body_and_reference_fields_survive(self):
        result = x.detail(full_detail(), URL)
        self.assertIn("beyond a snippet", result["description"])
        self.assertEqual(
            result["native_body_fields"]["careerLevel"]["localizationValue"], "Student"
        )
        self.assertEqual(result["native_job_posting"]["employmentType"], "FULL_TIME")
        self.assertTrue(result["model_reconciliation_required"])
        self.assertFalse(result["requirements_completeness_verified"])
        self.assertFalse(result["full_posting_reviewed"])
        self.assertNotIn("DO_NOT_EMIT_LOGO", json.dumps(result))

    def test_visible_body_mismatch_never_hidden_or_partial_success(self):
        body = full_detail().replace(
            b'<div class="html-description__DescriptionContainer"><p>Complete native requirements beyond a snippet.</p></div>',
            b'<div class="html-description__DescriptionContainer">Short preview only</div>',
        )
        with self.assertRaises(x.XingError):
            x.detail(body, URL)

    def test_account_graph_and_reference_cycles_refused(self):
        with self.assertRaises(x.XingError):
            x.job_value({"__ref": "User:1"}, {"User:1": {"__typename": "User", "name": "Private"}})
        with self.assertRaises(x.XingError):
            x.job_value(
                {"__ref": "Level:1"},
                {"Level:1": {"__typename": "CareerLevel", "child": {"__ref": "Level:1"}}},
            )

    def test_uri_discovery_not_current_vacancy_supply(self):
        body = b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://www.xing.com/jobs/old-ad-123456</loc></url></urlset>'
        result = x.discovery(body, "https://www.xing.com/jobs/1-sitemap.xml.gz")
        self.assertEqual(result["returned_uri_count"], 1)
        self.assertFalse(result["current_vacancy_status_verified"])
        self.assertNotIn("listings", result)

    def test_action_keyword_account_routes_refused(self):
        for url in [
            "https://www.xing.com/login",
            "https://www.xing.com/jobs/search/ki",
            "https://www.xing.com/jobs/k-student?q=hr",
            "https://www.xing.com/jobs/jobs-in-hessen?page=0",
        ]:
            with self.assertRaises(x.XingError):
                x.checked_url(url, "inventory")


class SourceCaptureTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"JOB_MARKET_CAPTURE_DIR": self.directory.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.directory.cleanup()

    def result(self, count=2501):
        records = [
            {
                "url": "https://www.xing.com/jobs/native-" + str(100000 + i),
                "source_last_modified": None,
            }
            for i in range(count)
        ]
        return {
            "source": "xing",
            "kind": "source_uri_discovery",
            "source_url": "https://www.xing.com/jobs/1-sitemap.xml.gz",
            "source_sha256": "a" * 64,
            "native_sitemap_kind": "urlset",
            "discovery_uris": records,
            "returned_uri_count": len(records),
        }

    def test_all_segments_preserve_every_uri(self):
        manifest = c.record_capture(self.result())
        self.assertEqual(manifest["native_uri_count"], 2501)
        self.assertFalse(manifest["native_pagination"])
        self.assertNotIn("listings", manifest)
        rows = []
        for index in range(manifest["consumer_segment_count"]):
            part = c.read_segment(manifest["capture_id"], index)
            rows.extend(part["discovery_uris"])
            self.assertFalse(part["current_vacancy_status_verified"])
        self.assertEqual(len(rows), 2501)
        self.assertEqual(len({r["url"] for r in rows}), 2501)
        self.assertIsNone(part["next_consumer_segment_index"])

    def test_same_capture_immutable_and_reused(self):
        first = c.record_capture(self.result(1))
        second = c.record_capture(self.result(1))
        self.assertEqual(first["capture_id"], second["capture_id"])
        self.assertFalse(list(c.cache_directory().glob(".source-capture-*")))

    def test_tamper_fails_without_repair(self):
        manifest = c.record_capture(self.result(1))
        path = c.cache_directory() / (manifest["capture_id"] + ".json")
        path.write_bytes(b"changed")
        with self.assertRaises(c.CaptureError):
            c.read_segment(manifest["capture_id"], 0)
        with self.assertRaises(c.CaptureError):
            c.record_capture(self.result(1))
        self.assertEqual(path.read_bytes(), b"changed")

    def test_wrong_id_index_symlink_not_arbitrary_file_read(self):
        for identifier in ["../private", "a" * 63]:
            with self.assertRaises(c.CaptureError):
                c.read_segment(identifier, 0)
        manifest = c.record_capture(self.result(1))
        for index in [-1, 1, True]:
            with self.assertRaises(c.CaptureError):
                c.read_segment(manifest["capture_id"], index)
        path = c.cache_directory() / ("f" * 64 + ".json")
        path.symlink_to(c.cache_directory() / (manifest["capture_id"] + ".json"))
        with self.assertRaises(c.CaptureError):
            c.read_segment("f" * 64, 0)

    def test_missing_private_configuration_never_truncates(self):
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(c.CaptureError):
            c.record_capture(self.result())

    def test_non_uri_artifact_is_not_capture(self):
        result = self.result(1)
        result["source"] = "another-provider"
        with self.assertRaises(c.CaptureError):
            c.record_capture(result)
