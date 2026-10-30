"""Synthetic public-advert contracts; no copied employer adverts or applicants."""

import json
import unittest
from copy import deepcopy

from reader import SourceError, checked_url, parse, read

URL = "https://example.jobs.personio.de/job/67"


def page(
    *,
    locale="de",
    company=True,
    schema=None,
    primary="<p>Complete <strong>primary</strong> role</p>",
):
    schema = (
        deepcopy(schema)
        if schema is not None
        else {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Student role",
            "identifier": {"@type": "PropertyValue", "name": "Example", "value": "67-12"},
            "description": "<p>Short schema summary</p>",
            "datePosted": "2026-10-01",
            "workHours": "40 hours",
            "employmentType": ["FULL_TIME"],
            "jobLocation": {"address": {"addressCountry": "DE"}},
        }
    )
    about = (
        '<div class="detail-content-block-about-us"><h2>About us</h2><p>Separate company context</p></div>'
        if company
        else ""
    )
    return (
        f'<html lang="en"><head><link rel="canonical" href="{URL}?language={locale}">'
        f'<script type="application/ld+json">{json.dumps(schema)}</script>'
        '<script id="__NEXT_DATA__">{"session":"DO_NOT_EXPORT"}</script></head><body><main>'
        '<div class="job-header"><h1 class="job-position-title">Student role</h1><p>Permanent, full-time · Example city</p></div>'
        f'<div class="detail-content-block-conditions"><div class="jb-description-item"><h2>Mission</h2>{primary}</div></div>{about}'
        '<form><input name="csrf" value="DO_NOT_EXPORT"><button>Apply</button></form>'
        "</main></body></html>"
    ).encode()


class PersonioPrimaryTests(unittest.TestCase):
    def test_complete_primary_is_not_replaced_by_schema_or_company_context(self):
        result = parse(page(), URL)
        self.assertIn("Complete primary role", result["source_primary_text"])
        self.assertNotIn("Separate company context", result["source_primary_text"])
        self.assertIn(
            "Separate company context", result["native_company_context_sections"][0]["text"]
        )
        self.assertEqual(result["schema_description"]["text"], "Short schema summary")
        self.assertFalse(result["schema_description_used_as_primary"])

    def test_document_display_language_does_not_become_primary_or_working_language(self):
        result = parse(page(locale="de"), URL)
        self.assertEqual(result["native_document_language"], "en")
        self.assertEqual(result["source_canonical_locale"], "de")
        self.assertIsNone(result["requested_description_locale"])
        self.assertNotIn("working_language", result)

    def test_native_job_and_platform_company_identity_are_distinct(self):
        result = parse(page(), URL)
        self.assertEqual(result["id"], "personio::example.jobs.personio.de::67")
        self.assertEqual(result["native_job_id"], "67")
        self.assertEqual(result["native_platform_company_id"], "12")

    def test_advert_is_not_original_clock_student_contract_or_human_review(self):
        result = parse(page(), URL)
        self.assertEqual(result["source_jobposting_schema"]["datePosted"], "2026-10-01")
        self.assertEqual(result["source_jobposting_schema"]["workHours"], "40 hours")
        self.assertIsNone(result["original_published_at"])
        self.assertFalse(result["coverage_complete"])
        self.assertFalse(result["full_posting_reviewed"])
        self.assertFalse(result["reviewed_by_model"])

    def test_forms_hydration_and_control_attributes_never_export(self):
        result = parse(
            page(
                primary='<p onclick="DO_NOT_EXPORT">Role</p><form><input value="DO_NOT_EXPORT"></form><script>DO_NOT_EXPORT</script>'
            ),
            URL,
        )
        rendered = json.dumps(result)
        self.assertNotIn("DO_NOT_EXPORT", rendered)
        self.assertNotIn("onclick", rendered)
        self.assertFalse(result["credentials_cookies_forms_or_hydration_state_exported"])

    def test_unknown_schema_state_is_not_exported_as_job_metadata(self):
        schema = {
            "@type": "JobPosting",
            "title": "Student role",
            "identifier": {"value": "67-12"},
            "description": "Role",
            "sessionState": "DO_NOT_EXPORT",
        }
        self.assertNotIn("DO_NOT_EXPORT", json.dumps(parse(page(schema=schema), URL)))

    def test_absent_optional_company_context_is_not_invented(self):
        result = parse(page(company=False), URL)
        self.assertEqual(result["native_company_context_sections"], [])
        self.assertEqual(
            result["native_company_context_status"], "not_exposed_in_current_primary_page"
        )

    def test_unmapped_company_context_is_refused_instead_of_dropped(self):
        raw = page().replace(b"detail-content-block-about-us", b"unqualified-company-layout")
        with self.assertRaisesRegex(SourceError, "unmapped_personio_company_context"):
            parse(raw, URL)

    def test_missing_primary_marker_or_title_is_not_a_full_body(self):
        for marker in [b"detail-content-block-conditions", b"job-position-title", b"job-header"]:
            with self.subTest(marker=marker), self.assertRaises(SourceError):
                parse(page().replace(marker, b"unknown-layout"), URL)

    def test_competing_primary_roots_are_explicit(self):
        raw = page().replace(
            b"</main>", b'<div class="detail-content-block-conditions">Second body</div></main>'
        )
        with self.assertRaisesRegex(SourceError, "competing_personio_primary"):
            parse(raw, URL)

    def test_competing_jobpostings_are_not_arbitrarily_selected(self):
        raw = page().replace(
            b"</head>", b'<script type="application/ld+json">{"@type":"JobPosting"}</script></head>'
        )
        with self.assertRaisesRegex(SourceError, "competing_personio_jobposting"):
            parse(raw, URL)

    def test_jobpostings_in_native_graph_are_read_as_data(self):
        schema = {
            "@graph": [
                {"@type": "Organization", "name": "Example"},
                {
                    "@type": ["JobPosting"],
                    "title": "Student role",
                    "identifier": {"value": "67-12"},
                    "description": "Role",
                },
            ]
        }
        self.assertEqual(parse(page(schema=schema), URL)["native_job_id"], "67")

    def test_schema_job_id_and_title_must_match_the_primary(self):
        for schema in [
            {
                "@type": "JobPosting",
                "title": "Student role",
                "identifier": {"value": "68-12"},
                "description": "Role",
            },
            {
                "@type": "JobPosting",
                "title": "Other role",
                "identifier": {"value": "67-12"},
                "description": "Role",
            },
        ]:
            with self.assertRaises(SourceError):
                parse(page(schema=schema), URL)

    def test_canonical_job_or_employer_reset_fails(self):
        for replacement in [
            b"https://example.jobs.personio.de/job/68?language=de",
            b"https://other.jobs.personio.de/job/67?language=de",
        ]:
            with self.assertRaisesRegex(SourceError, "canonical_identity_differs"):
                parse(page().replace((URL + "?language=de").encode(), replacement), URL)

    def test_job_routes_reject_accounts_application_credentials_and_filters(self):
        for uri in [
            URL + "/apply",
            URL + "#apply",
            URL + "?country=DE",
            URL + "?language=en&language=en",
            URL.replace("/67", "/%36%37"),
            URL.replace("https://", "http://"),
            URL.replace("https://", "https://user:password@"),
            URL.replace(".de/", ".de:8443/"),
            "https://example.org/job/67",
            "https://example.jobs.personio.de/login",
            URL + "?language=de&title=HR",
            "https://[",
            "\n" + URL,
            " " + URL,
        ]:
            with self.subTest(uri=uri), self.assertRaises(SourceError):
                checked_url(uri)

    def test_qualified_com_origin_and_locale_remain_distinct(self):
        self.assertEqual(
            checked_url("https://example.jobs.personio.com/job/67?language=en"),
            ("example.jobs.personio.com", "67", "en"),
        )

    def test_empty_and_oversized_html_are_not_truncated_successes(self):
        for raw in [b"", b"x" * (8 * 1024 * 1024 + 1)]:
            with self.assertRaises(SourceError):
                parse(raw, URL)

    def test_media_only_content_requires_separate_verification(self):
        result = parse(
            page(primary='<p>Role</p><img src="https://example.org/requirements.png">'), URL
        )
        self.assertEqual(result["native_nontext_media_count"], 1)
        self.assertFalse(result["nontext_media_requirements_verified"])
        self.assertNotIn("<img", result["description"])

    def test_robots_denial_performs_no_ad_request(self):
        calls = []

        def transport(uri, **kwargs):
            calls.append(uri)
            return {"body": b"User-agent: *\nDisallow: /job/\n", "content_type": "text/plain"}

        with self.assertRaisesRegex(SourceError, "robots_disallowed"):
            read(URL, transport=transport)
        self.assertEqual(calls, ["https://example.jobs.personio.de/robots.txt"])

    def test_missing_robots_resource_allows_exact_ad_only_under_rfc9309(self):
        calls = []

        def transport(uri, **kwargs):
            calls.append(uri)
            if uri.endswith("/robots.txt"):
                raise SourceError("source_http_error", http_status=404)
            return {
                "body": page(),
                "content_type": "text/html; charset=utf-8",
                "requested_at": "2026-10-01T00:00:00Z",
            }

        result = read(URL, transport=transport)
        self.assertEqual(calls, ["https://example.jobs.personio.de/robots.txt", URL])
        self.assertFalse(result["source_scripts_media_accounts_or_applications_requested"])

    def test_unavailable_or_denied_robots_are_not_successful_empty_ads(self):
        for status in [403, 429, 500]:

            def transport(uri, **kwargs):
                raise SourceError("source_http_error", http_status=status)

            with self.assertRaises(SourceError):
                read(URL, transport=transport)

    def test_wrong_resource_content_type_is_explicit(self):
        def transport(uri, **kwargs):
            if uri.endswith("/robots.txt"):
                return {"body": b"User-agent: *\nAllow: /\n", "content_type": "text/plain"}
            return {"body": b"{}", "content_type": "application/json"}

        with self.assertRaisesRegex(SourceError, "unexpected_personio_content_type"):
            read(URL, transport=transport)

    def test_application_guard_runs_before_any_transport(self):
        def transport(uri, **kwargs):
            self.fail("An application route must never invoke transport")

        with self.assertRaises(SourceError):
            read(URL + "/apply", transport=transport)


if __name__ == "__main__":
    unittest.main()
