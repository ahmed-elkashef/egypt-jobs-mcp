import importlib.util
import json
import unittest
from pathlib import Path
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location("dvinci_reader", Path(__file__).parents[1] / "reader.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE = "https://example.dvinci-hr.com"


def row(identity=10, opening=20, **overrides):
    result = {"id": identity, "position": "Native publication", "language": "de",
              "jobPublicationURL": None, "applicationFormURL": BASE + "/apply/10",
              "startDate": "2026-10-01T12:00:00+02:00", "endDate": None,
              "jobOpening": {"id": opening, "type": "DEFAULT", "location": "Native place",
                  "locations": [{"country": {"isoA2": "DE"}}],
                  "workingTimes": [{"internalName": "CUSTOM_TIME", "name": "Employer label"}],
                  "targetGroups": [{"internalName": "CUSTOM_GROUP", "name": "Own group"}],
                  "contractPeriod": {"internalName": "OWN_TERM", "name": "Own term"},
                  "earliestEntryDate": "nach Vereinbarung", "createdDate": "2025-01-01T00:00:00Z",
                  "company": {"id": 3, "name": "Employer", "description10": "Unused company context"},
                  "costUnit": "internal", "responsibleUser": {"email": "unused@example.test"}},
              "introduction": "<p>Introduction</p>", "tasks": "<p>Native tasks</p>",
              "profile": "<p>Native profile</p>", "weOffer": None, "closingText": "<p>Extra closing</p>",
              "renderedContent": {"additionalInformation": {"body": "<p>Additional note</p>"},
                  "introduction": {"body": "<p>Introduction</p>"},
                  "tasks": {"headline": "Tasks", "body": "<p>Native tasks</p>"},
                  "profile": {"body": "<p>Native profile</p>"},
                  "weOffer": {"headline": "Benefits", "body": "<ul><li>Rendered benefit</li><li>Another benefit</li></ul>"},
                  "contact": {"body": "<p>Public contact section</p>"}}, "benefits": [{"name": "Native benefit"}]}
    result.update(overrides)
    return result


def raw(value):
    return json.dumps(value).encode()


class Transport:
    def __init__(self, value, *, robots=None, content_type="application/json"):
        self.value, self.robots, self.content_type, self.calls = value, robots, content_type, []

    def __call__(self, url, *, accept, **kwargs):
        self.calls.append((url, accept))
        if url.endswith("/robots.txt"):
            if self.robots is None:
                raise m.SourceError("source_http_error", http_status=404)
            if isinstance(self.robots, int):
                raise m.SourceError("source_http_error", http_status=self.robots)
            return {"body": self.robots.encode()}
        if isinstance(self.value, Exception):
            raise self.value
        return {"body": raw(self.value), "content_type": self.content_type}


class ReaderTests(unittest.TestCase):
    def test_exact_portal_seeds_and_custom_path(self):
        self.assertEqual(BASE, m.portal(BASE + "/"))
        self.assertEqual(BASE + "/portal/German_2", m.portal(BASE + "/portal/German_2/"))
        for origin in m.CUSTOM_ORIGINS:
            self.assertEqual(origin, m.portal(origin))

    def test_unsafe_or_account_seed_refused_before_network(self):
        for value in [None, "http://example.dvinci-hr.com", BASE + "/de/jobs", BASE + "/jobPublications/",
                      BASE + "/?key=x", BASE + "/#x", "https://api.dvinci-hr.com", "https://static.dvinci-hr.com",
                      "https://example.dvinci-hr.com.evil.test", "https://user@example.dvinci-hr.com",
                      "https://example.dvinci-hr.com:443", "https://127.0.0.1", BASE + "/portal/../admin",
                      BASE + "/portal/a%2fb", BASE + "/portal/x//", " " + BASE, BASE + "\n"]:
            with self.subTest(value=value):
                transport = Transport([])
                with self.assertRaises(m.SourceError):
                    m.read(value, transport=transport)
                self.assertEqual([], transport.calls)

    def test_compact_inventory_is_unfiltered_and_not_body_evidence(self):
        transport = Transport([row()])
        result = m.read(BASE, transport=transport)
        self.assertEqual([(BASE + "/robots.txt", "text/plain"),
                          (BASE + "/jobPublication/list.json?fields=small", "application/json")], transport.calls)
        self.assertEqual(1, result["returned_count"])
        self.assertIsNone(result["source_result_count"])
        self.assertIsNone(result["listings"][0]["description"])
        self.assertFalse(result["listings"][0]["source_body_untruncated"])
        self.assertFalse(result["coverage_complete"])

    def test_full_inventory_uses_documented_default_full_fields(self):
        transport = Transport([row()])
        result = m.read(BASE, include_body=True, transport=transport)
        self.assertEqual(BASE + "/jobPublication/list.json", transport.calls[-1][0])
        self.assertTrue(result["listings"][0]["source_body_untruncated"])

    def test_robots_disallow_stops_before_api(self):
        transport = Transport([], robots="User-agent: *\nDisallow: /jobPublication/\n")
        with self.assertRaisesRegex(m.SourceError, "robots_denied"):
            m.read(BASE, transport=transport)
        self.assertEqual(1, len(transport.calls))

    def test_robots_failure_not_permission_or_empty_inventory(self):
        for code in [401, 403, 429, 500, 503]:
            transport = Transport([], robots=code)
            with self.subTest(code=code), self.assertRaises(m.SourceError) as caught:
                m.read(BASE, transport=transport)
            self.assertEqual(code, caught.exception.http_status)
            self.assertEqual(1, len(transport.calls))

    def test_robots_html_challenge_not_robots_file(self):
        transport = Transport([], robots="<!doctype html><html>Challenge</html>")
        with self.assertRaisesRegex(m.SourceError, "invalid_robots_response"):
            m.read(BASE, transport=transport)
        self.assertEqual(1, len(transport.calls))

    def test_disabled_publication_api_no_xml_or_other_fallback(self):
        transport = Transport(m.SourceError("source_http_error", http_status=403))
        with self.assertRaises(m.SourceError) as caught:
            m.read(BASE, transport=transport)
        self.assertEqual(403, caught.exception.http_status)
        self.assertEqual(2, len(transport.calls))

    def test_custom_portal_robots_origin_and_native_api_path(self):
        transport = Transport([])
        m.read(BASE + "/portal/German", transport=transport)
        self.assertEqual(BASE + "/robots.txt", transport.calls[0][0])
        self.assertEqual(BASE + "/portal/German/jobPublication/list.json?fields=small", transport.calls[1][0])

    def test_complete_array_not_sliced_or_role_filtered(self):
        result = m.parse_inventory(raw([row(i) for i in range(1, 1202)]), BASE)
        self.assertEqual(1201, result["returned_count"])
        self.assertEqual(1201, len(result["listings"]))
        self.assertEqual(BASE + "::1201", result["listings"][-1]["id"])

    def test_literal_empty_array_is_qualified_not_country_coverage(self):
        result = m.parse_inventory(b"[]", BASE)
        self.assertEqual(0, result["returned_count"])
        self.assertTrue(result["native_array_untruncated"])
        self.assertIsNone(result["source_result_count"])
        self.assertFalse(result["coverage_complete"])

    def test_nonarray_response_not_empty_inventory(self):
        for value in [{"error": "denied"}, None, "[]", 0]:
            with self.subTest(value=value), self.assertRaises(m.SourceError):
                m.parse_inventory(raw(value), BASE)

    def test_bad_late_row_refuses_whole_response(self):
        with self.assertRaises(m.SourceError):
            m.parse_inventory(raw([row(), {"id": 11}]), BASE)

    def test_duplicate_publication_not_silently_deduplicated(self):
        with self.assertRaisesRegex(m.SourceError, "duplicate_native_publication_id"):
            m.parse_inventory(raw([row(), row()]), BASE)

    def test_multilingual_publications_for_one_opening_retained(self):
        result = m.parse_inventory(raw([row(10, language="de"), row(11, language="en")]), BASE)
        self.assertEqual(2, result["returned_count"])
        self.assertEqual(["20", "20"], [r["native_job_opening_id"] for r in result["listings"]])
        self.assertEqual(2, len({r["id"] for r in result["listings"]}))

    def test_identical_publication_ids_scoped_by_portal(self):
        first = m.parse_inventory(raw([row()]), BASE)["listings"][0]["id"]
        second = m.parse_inventory(raw([row()]), BASE + "/portal/other")["listings"][0]["id"]
        self.assertNotEqual(first, second)

    def test_external_and_null_native_job_urls_are_not_dropped(self):
        result = m.parse_inventory(raw([row(10), row(11, jobPublicationURL="https://employer.example/jobs/11")]), BASE)
        self.assertEqual(2, result["returned_count"])
        self.assertIsNone(result["listings"][0]["url"])
        self.assertEqual("https://employer.example/jobs/11", result["listings"][1]["url"])

    def test_unsafe_published_links_fail_without_requesting_them(self):
        for value in ["javascript:alert(1)", "file:///tmp/x", "https://a:b@example.test/job", "https://x.test/\njob"]:
            with self.subTest(value=value), self.assertRaises(m.SourceError):
                m.parse_inventory(raw([row(jobPublicationURL=value)]), BASE)

    def test_rendered_benefits_additional_contact_and_raw_closing_preserved(self):
        result = m.parse_inventory(raw([row()]), BASE, include_body=True)["listings"][0]
        for text in ["Rendered benefit Another benefit", "Additional note", "Public contact section", "Extra closing"]:
            self.assertIn(text, result["description"])
        self.assertIsNone(result["native_body_fields"]["raw_sections"]["weOffer"])
        self.assertIsNone(result["visible_description"])
        self.assertFalse(result["full_posting_reviewed"])
        self.assertTrue(result["body_variants_require_reconciliation"])

    def test_all_ten_company_sections_preserved_but_not_assumed_ad_requirements(self):
        value = row()
        value["jobOpening"]["company"].update({"description" + str(i): "Company-only " + str(i) for i in range(1, 11)})
        result = m.parse_inventory(raw([value]), BASE, include_body=True)["listings"][0]
        self.assertEqual(10, len(result["native_body_fields"]["company_description_sections"]))
        self.assertNotIn("Company-only", result["description"])
        self.assertNotIn("costUnit", result["native_job_opening"])
        self.assertNotIn("responsibleUser", result["native_job_opening"])

    def test_body_html_is_inert_with_no_script_or_style_text_promotion(self):
        value = row()
        value["renderedContent"]["tasks"]["body"] += "<script>DO_NOT_EXECUTE</script><style>hidden</style>"
        result = m.parse_inventory(raw([value]), BASE, include_body=True)["listings"][0]
        self.assertIn("DO_NOT_EXECUTE", result["description_html"])
        self.assertNotIn("DO_NOT_EXECUTE", result["description"])
        self.assertNotIn("hidden", result["description"])

    def test_source_clocks_entry_and_mutable_labels_not_promoted(self):
        result = m.parse_inventory(raw([row()]), BASE)["listings"][0]
        self.assertIsNone(result["original_published_at"])
        self.assertEqual("2026-10-01T12:00:00+02:00", result["source_publication_available_since"])
        self.assertEqual("2025-01-01T00:00:00Z", result["native_job_opening_created_at"])
        self.assertEqual("nach Vereinbarung", result["native_earliest_entry_date"])
        self.assertEqual("CUSTOM_TIME", result["native_job_opening"]["workingTimes"][0]["internalName"])
        for key in ["employment_type", "remote", "country_eligible", "student_eligible"]:
            self.assertNotIn(key, result)

    def test_exact_detail_id_distinct_from_opening_and_no_apply_fetch(self):
        transport = Transport(row())
        result = m.read(BASE, job_id="10", transport=transport)
        self.assertEqual(BASE + "/jobPublication/show/10.json", transport.calls[-1][0])
        self.assertEqual("10", result["native_publication_id"])
        self.assertEqual("20", result["native_job_opening_id"])
        self.assertEqual(BASE + "/apply/10", result["application_url"])
        self.assertEqual(2, len(transport.calls))

    def test_wrong_native_detail_id_refused(self):
        with self.assertRaisesRegex(m.SourceError, "identity_mismatch"):
            m.read(BASE, job_id="11", transport=Transport(row()))

    def test_invalid_id_and_detail_body_flag_refused_before_network(self):
        for value in [True, 0, -1, "01", "../10", "10?apply=1", "9007199254740992", {}, 1.5]:
            transport = Transport(row())
            with self.subTest(value=value), self.assertRaises(m.SourceError):
                m.read(BASE, job_id=value, transport=transport)
            self.assertEqual([], transport.calls)
        with self.assertRaises(m.SourceError):
            m.read(BASE, job_id="10", include_body=True, transport=Transport(row()))

    def test_strict_json_duplicate_and_nonfinite_values(self):
        for value in [b'[{"id":1,"id":2}]', b'[NaN]', b'[Infinity]', b'[1e999]', b'bad', b'\xff']:
            with self.subTest(value=value), self.assertRaises(m.SourceError):
                m.parse_inventory(value, BASE)

    def test_bad_rendered_or_missing_complete_body_explicit_limit(self):
        for value in [row(renderedContent=[]), row(renderedContent={"tasks": {"body": 7}}),
                      row(renderedContent={}, **{k: None for k in m.RAW_BODY_FIELDS})]:
            with self.subTest(value=value), self.assertRaises(m.SourceError):
                m.parse_inventory(raw([value]), BASE, include_body=True)

    def test_html_response_not_parsed_as_empty_json(self):
        with self.assertRaisesRegex(m.SourceError, "content_type"):
            m.read(BASE, transport=Transport([], content_type="text/html"))

    def test_request_rejects_whole_oversized_body_and_redirect(self):
        class Response:
            status, headers = 200, {"Content-Type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, size): return b"x" * size
        class Opener:
            def open(self, request, timeout):
                self.request = request
                return Response()
        opener = Opener()
        with self.assertRaisesRegex(m.SourceError, "exceeds_bound"):
            m.request(BASE, accept="application/json", bound=32, opener=opener)
        self.assertNotIn("Authorization", opener.request.headers)
        self.assertNotIn("Cookie", opener.request.headers)
        self.assertIsNone(m.NoRedirect().redirect_request(None, None, 302, "redirect", {}, BASE))

    def test_http_retry_after_is_retained_without_empty_success(self):
        class Opener:
            def open(self, request, timeout):
                raise HTTPError(BASE, 429, "limited", {"Retry-After": "60"}, None)
        with self.assertRaises(m.SourceError) as caught:
            m.request(BASE, accept="application/json", opener=Opener())
        self.assertEqual(429, caught.exception.http_status)
        self.assertEqual("60", caught.exception.retry_after)

    def test_capabilities_are_offline_and_explicit_about_scope(self):
        result = m.capabilities()
        self.assertTrue(result["seed_required"])
        self.assertEqual([], result["acquisition_filters"])
        self.assertFalse(result["coverage_complete"])
        self.assertIn("fields=small", result["inventory_default"])


if __name__ == "__main__":
    unittest.main()
