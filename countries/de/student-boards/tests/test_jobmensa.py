"""Synthetic source contracts only; no real vacancies or applicant fixtures."""

import importlib.util
import json
from pathlib import Path
from unittest import TestCase, mock

MODULE = Path(__file__).resolve().parents[1] / "jobmensa.py"
spec = importlib.util.spec_from_file_location("jobmensa", MODULE)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def page(*, next_url="/jobs-suchen?categories=internship&page=2", count=20):
    return f'''<html><script>999999 Jobs</script><span>{count} Jobs</span>
      <a data-testid="job-offer-item" data-jobvalley-job="false" href="/jobs/ex/synthetic-1234">
       <h2>Werkstudent / Praktikum Synthetic</h2><div>Empfohlen</div>
       <p><svg data-icon="location-dot"></svg>Synthetic place</p>
       <p><svg data-icon="building"></svg>Synthetic employer</p></a>
      <nav aria-label="Seitennummerierung"><a href="{next_url}">Seite 2</a></nav></html>'''.encode()


class JobmensaTests(TestCase):
    def test_complete_cards_native_fields_and_continuation(self):
        result = reader.parse_page(page(), reader.ORIGIN + "/jobs-suchen?categories=internship")
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["reported_total"], 20)
        self.assertEqual(
            result["pagination"]["next_url"],
            reader.ORIGIN + "/jobs-suchen?categories=internship&page=2",
        )
        row = result["listings"][0]
        self.assertEqual(row["employer_text"], "Synthetic employer")
        self.assertTrue(row["promoted_label_present"])
        self.assertFalse(row["contract_model_verified"])
        self.assertIsNone(row["original_published_at"])
        self.assertFalse(result["coverage_complete"])

    def test_unknown_layout_is_never_successful_empty(self):
        with self.assertRaises(ValueError):
            reader.parse_page(b"<html>Security check</html>", reader.ORIGIN + "/jobs-suchen")
        result = reader.parse_page(b"<span>0 Jobs</span>", reader.ORIGIN + "/jobs-suchen")
        self.assertEqual(result["returned_count"], 0)
        self.assertFalse(result["coverage_complete"])

    def test_unsafe_hosts_paths_and_keyword_or_duplicate_queries_refused(self):
        for url in [
            "https://www.jobmensa.de.evil/jobs-suchen",
            "http://www.jobmensa.de/jobs-suchen",
            reader.ORIGIN + "/login",
            reader.ORIGIN + "/jobs-suchen?query=HR",
            reader.ORIGIN + "/jobs-suchen?categories=marketing",
            reader.ORIGIN + "/jobs-suchen?page=1&page=2",
            reader.ORIGIN + "/jobs-suchen?page=0",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                reader.checked_url(url)

    def test_native_continuation_cannot_change_partition(self):
        with self.assertRaisesRegex(ValueError, "changed"):
            reader.parse_page(
                page(next_url="/jobs-suchen?categories=werkstudent&page=2"),
                reader.ORIGIN + "/jobs-suchen?categories=internship",
            )

    def test_duplicate_native_identity_refuses_silent_loss(self):
        value = page()
        card = value[value.index(b"<a data-testid") : value.index(b"</a>") + 4]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            reader.parse_page(
                value.replace(b"</html>", card + b"</html>"),
                reader.ORIGIN + "/jobs-suchen?categories=internship",
            )

    def test_full_detail_and_conflicting_native_constraints_remain_distinct(self):
        native = {
            "@type": "JobPosting",
            "title": "Synthetic Intern",
            "description": "<p>" + "Complete body. " * 3000 + "</p>",
            "datePosted": "2026-10-13T10:00:00+02:00",
            "validThrough": "2026-11-10T10:00:00+01:00",
            "employmentType": ["PART_TIME"],
            "workHours": "40 Stunden/Woche",
            "jobLocationType": "TELECOMMUTE",
            "applicantLocationRequirements": {"name": "Germany"},
        }
        body = (
            '<script type="application/ld+json">'
            + json.dumps(native)
            + '</script><a href="https://example.test/apply">Jetzt bewerben</a>'
        ).encode()
        result = reader.parse_detail(body, reader.ORIGIN + "/jobs/ex/synthetic-1234")
        self.assertEqual(result["native_job_posting"], native)
        self.assertGreater(len(result["description"]), 40000)
        self.assertEqual(result["employment_type"], ["PART_TIME"])
        self.assertEqual(result["work_hours"], "40 Stunden/Woche")
        self.assertFalse(result["full_posting_reviewed"])
        self.assertEqual(result["apply_urls"], ["https://example.test/apply"])

    def test_page_two_ignores_unrelated_fragment_links(self):
        body = page(next_url="/jobs-suchen?categories=internship&page=3#results")
        body += b'<footer><a href="#cookie-settings">Settings</a></footer>'
        result = reader.parse_page(
            body, reader.ORIGIN + "/jobs-suchen?categories=internship&page=2"
        )
        self.assertEqual(
            result["pagination"]["next_url"],
            reader.ORIGIN + "/jobs-suchen?categories=internship&page=3",
        )

    def test_missing_or_multiple_primary_postings_fail(self):
        for body in [
            b"<h1>Snippet</h1>",
            b'<script type="application/ld+json">[{"@type":"JobPosting","description":"one"},{"@type":"JobPosting","description":"two"}]</script>',
        ]:
            with self.assertRaises(ValueError):
                reader.parse_detail(body, reader.ORIGIN + "/jobs/ex/synthetic-1234")

    def test_live_policy_denial_stops_before_page_request(self):
        with mock.patch.object(
            reader, "fetch", return_value=b"User-agent: *\nDisallow: /\n"
        ) as fetch:
            with self.assertRaisesRegex(ValueError, "policy denies"):
                reader.read("page", reader.ORIGIN + "/jobs-suchen")
            self.assertEqual(fetch.call_count, 1)

    def test_redirect_to_auth_or_foreign_origin_refused(self):
        redirect = reader.SafeRedirect()
        for url in ["https://evil.test/jobs-suchen", reader.ORIGIN + "/login"]:
            with self.assertRaises(ValueError):
                redirect.redirect_request(None, None, 302, "Found", {}, url)

    def test_redirect_cannot_drop_partition_page_or_native_job_identity(self):
        from urllib.request import Request

        for initial, target in [
            (
                reader.ORIGIN + "/jobs-suchen?categories=internship&page=2",
                reader.ORIGIN + "/jobs-suchen?page=2",
            ),
            (reader.ORIGIN + "/jobs-suchen?page=2", reader.ORIGIN + "/jobs-suchen?page=3"),
            (reader.ORIGIN + "/jobs/ex/synthetic-1234", reader.ORIGIN + "/jobs/ex/synthetic-1235"),
            (reader.ORIGIN + "/robots.txt", reader.ORIGIN + "/login"),
        ]:
            with self.subTest(initial=initial, target=target), self.assertRaises(ValueError):
                reader.SafeRedirect().redirect_request(
                    Request(initial), None, 302, "Found", {}, target
                )

    def test_actual_final_url_is_preserved_without_caller_only_echo(self):
        requested = reader.ORIGIN + "/jobs-suchen?categories=internship&page=2"
        actual = reader.ORIGIN + "/jobs-suchen?page=2&categories=internship"
        with mock.patch.object(
            reader,
            "fetch",
            side_effect=[
                b"User-agent: *\nAllow: /\n",
                (page(next_url="/jobs-suchen?categories=internship&page=3"), actual),
            ],
        ):
            result = reader.read("page", requested)
            self.assertEqual(result["requested_url"], requested)
            self.assertEqual(result["source_url"], actual)

    def test_native_page_gap_is_not_silently_skipped(self):
        with self.assertRaisesRegex(ValueError, "page gap"):
            reader.parse_page(
                page(next_url="/jobs-suchen?categories=internship&page=3"),
                reader.ORIGIN + "/jobs-suchen?categories=internship",
            )
