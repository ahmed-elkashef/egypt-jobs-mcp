import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sap_flight as flight
import sap_modern as s
from shared.public_http import SourceError as PublicError

URI = s.ORIGIN + "/en/jobs/744000000000001/synthetic-role/"


def model(country=None, page=1, total=14):
    criteria = {"page": page, "pagesize": 12, "orderby": 1, "includeFilters": True}
    if country:
        criteria["country"] = ["Germany"]
    jobs = []
    for number in range((page - 1) * 12, min(page * 12, total)):
        identity = str(744000000000001 + number)
        jobs.append({"id": identity, "title": "Synthetic public role", "url": "/en/jobs/" + identity + "/synthetic-role/",
                     "locations": "Synthetic city, Germany", "contractType": "Part-time", "workPattern": "Hybrid",
                     "displayDate": "2026-10-29T09:00:00Z", "teams": "Synthetic category"})
    return {"jobs": jobs, "currentPage": page, "pageSize": 12, "totalJobs": total, "totalPages": max(1, (total + 11) // 12),
            "locale": "en", "matcherSearchCriteria": criteria, "jobMatcherEnabled": False, "profileEditingEnabled": False,
            "filterMetadata": {"sortOptions": [{"value": 1, "kind": "DisplayDate", "isDefault": True}]}, "displayMetadata": {}}


def stream(value):
    return ("2e:" + json.dumps(value, ensure_ascii=False) + "\n").encode()


def cached_stream(value):
    data = b"#" + stream(value)
    middle = len(data) // 2
    parts = [data[:middle], data[middle:]]
    return b"19:R\n" + b"".join(b"19:o" + format(len(p), "x").encode() + b"," + p for p in parts) + b"19:C\n"


def page(value, cached=None):
    data = stream(value) + (cached_stream(cached) if cached is not None else b"")
    return ("<html><script>self.__next_f.push(" + json.dumps([1, data.decode()], ensure_ascii=False) + ")</script></html>").encode()


def body(schema_patch=None, primary=None):
    description = primary if primary is not None else "<p>Complete source requirements and responsibilities. </p>" * 12
    schema = {"@type": "JobPosting", "title": "Synthetic public role", "description": "<p>Short schema summary.</p>",
              "url": URI, "mainEntityOfPage": URI, "identifier": {"value": "REF123M"},
              "hiringOrganization": {"name": "SAP Careers", "url": s.ORIGIN},
              "datePosted": "2026-10-29", "employmentType": "PART_TIME"}
    schema.update(schema_patch or {})
    return ("<html><h1>Synthetic public role</h1><div class='max-w-3xl mx-auto space-y-6'><h2>The Role</h2>" + description
            + "</div><div class='prose'>Separate generic company context.</div><script type='application/ld+json'>"
            + json.dumps(schema) + "</script></html>").encode()


class Transport:
    def __init__(self, response=None, failure=None, robots=b"User-agent: *\nAllow: /\n"):
        self.response = response or page(model())
        self.failure, self.robots, self.calls = failure, robots, []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/robots.txt"):
            return {"body": self.robots, "content_type": "text/plain"}
        if self.failure:
            raise self.failure
        return {"body": self.response, "content_type": "text/html", "requested_at": "synthetic-start", "observed_at": "synthetic-end"}


class SapNativeFrames(unittest.TestCase):
    def test_independent_record_namespaces_and_repeated_binary_chunks_resolve_one_agreeing_model(self):
        value = model()
        result = s.inventory(page(value, value), s.BOARD)
        self.assertEqual((2, 2, 12, 14), (result["native_frame_count"], result["native_job_model_count"], result["returned_count"], result["source_result_count"]))

    def test_conflicting_cached_and_inline_job_arrays_never_choose_one_silently(self):
        value, other = model(), model()
        other["jobs"][0]["title"] = "Different cached title"
        with self.assertRaisesRegex(s.SapModernError, "conflicting"):
            s.inventory(page(value, other), s.BOARD)

    def test_utf8_text_lengths_and_binary_payload_boundaries_preserve_record_identity(self):
        text = "ä✈".encode()
        records, nested = flight.frame_records(b"a:T" + format(len(text), "x").encode() + b"," + text + b"\nb:42\n")
        self.assertEqual({"a": "ä✈", "b": 42}, records)
        self.assertEqual([], nested)

    def test_truncated_binary_chunks_and_unclosed_streams_refuse(self):
        for data in (b"19:R\n19:o20,short", b"19:R\n19:o1,#", b"19:C\n"):
            with self.subTest(data=data), self.assertRaises(flight.SapFlightError):
                flight.frame_records(data)

    def test_conflicting_json_ids_remain_invalid_within_one_namespace(self):
        with self.assertRaisesRegex(flight.SapFlightError, "conflicting_native_json_record"):
            flight.frame_records(b"a:1\na:2\n")

    def test_plain_json_duplicates_and_nonfinite_values_are_not_native_metadata(self):
        for data in ('{"x":1,"x":2}', '{"x":NaN}'):
            with self.subTest(data=data), self.assertRaises(flight.SapFlightError):
                flight.strict_json(data)

    def test_inline_push_is_json_data_not_a_website_evaluator(self):
        for data in (b"<script>self.__next_f.push([1,executeWebsiteCode()])</script>",
                     b"<script>self.__next_f.push([1,\"x\"]);window.location='/apply'</script>"):
            with self.subTest(data=data), self.assertRaises(flight.SapFlightError):
                flight.data_frames(data)

    def test_country_reference_resolves_only_in_its_own_record_frame(self):
        value = model("DE")
        value["matcherSearchCriteria"]["country"] = "$a:country"
        data = b'a:{"country":["Germany"]}\n' + stream(value)
        raw = ("<script>self.__next_f.push(" + json.dumps([1, data.decode()]) + ")</script>").encode()
        result = s.inventory(raw, s.inventory_uri("DE"))
        self.assertEqual(["Germany"], result["native_search_criteria"]["country"])


class SapModern(unittest.TestCase):
    def test_native_first_and_terminal_pages_reconcile_exact_ranges(self):
        for number, count, more in [(1, 12, True), (2, 2, False)]:
            result = s.inventory(page(model(page=number)), s.inventory_uri(page=number))
            self.assertEqual(count, result["returned_count"])
            self.assertIs(more, result["pagination"]["has_more"])
            self.assertFalse(result["coverage_complete"])

    def test_country_and_default_sort_echo_are_necessary_not_just_a_query_label(self):
        for patch in ({"country": ["France"]}, {"search": "marketing"}, {"orderby": 2}, {"candidateNumber": "not-public"}):
            value = model("DE")
            value["matcherSearchCriteria"].update(patch)
            with self.subTest(patch=patch), self.assertRaises(s.SapModernError):
                s.inventory(page(value), s.inventory_uri("DE"))

    def test_count_cap_partial_rows_duplicates_and_page_reset_are_not_empty_success(self):
        mutations = [lambda v: v.__setitem__("totalJobs", True), lambda v: v["jobs"].pop(),
                     lambda v: v["jobs"].__setitem__(1, copy.deepcopy(v["jobs"][0])),
                     lambda v: v.__setitem__("currentPage", 2), lambda v: v.__setitem__("totalPages", 1)]
        for mutate in mutations:
            value = model()
            mutate(value)
            with self.subTest(mutation=mutate), self.assertRaises(s.SapModernError):
                s.inventory(page(value), s.BOARD)

    def test_role_department_hours_and_application_routes_reject_before_transport(self):
        for uri, operation in [(s.BOARD + "?search=communications", "inventory"), (s.BOARD + "?team=Marketing", "inventory"),
                               (s.BOARD + "?pageSize=100", "inventory"), (s.BOARD + "?country=France", "inventory"),
                               (URI + "?apply=true", "detail"), (s.ORIGIN + "/api/auth", "detail")]:
            transport = Transport()
            with self.subTest(uri=uri), self.assertRaises(s.SapModernError):
                s.read(operation, uri, transport=transport)
            self.assertEqual([], transport.calls)

    def test_foreign_posting_identity_is_not_a_native_row(self):
        value = model()
        value["jobs"][0]["url"] = "https://other.invalid/en/jobs/744000000000001/synthetic-role/"
        with self.assertRaises(s.SapModernError):
            s.inventory(page(value), s.BOARD)

    def test_real_native_zero_array_is_distinct_from_unknown_or_partial_supply(self):
        result = s.inventory(page(model(total=0)), s.BOARD)
        self.assertEqual((0, 0), (result["returned_count"], result["source_result_count"]))
        self.assertIsNone(result["pagination"]["next_url"])

    def test_full_primary_is_preserved_separately_from_a_short_schema_summary(self):
        result = s.detail(body(), URI)
        self.assertGreater(len(result["description"]), len(result["native_schema_description_section"]["text"]))
        self.assertEqual("REF123M", result["native_requisition_reference"])
        self.assertEqual("744000000000001", result["native_job_id"])
        self.assertFalse(result["schema_description_used_as_full_body"])
        self.assertFalse(result["full_posting_reviewed"])
        self.assertIsNone(result["original_published_at"])
        self.assertEqual("PART_TIME", result["native_job_posting"]["employmentType"])

    def test_schema_scope_title_and_requisition_conflicts_never_export_a_partial_body(self):
        for patch in ({"url": "https://other.invalid/"}, {"title": "Different title"}, {"identifier": {}},
                      {"hiringOrganization": {"name": "Other employer", "url": s.ORIGIN}}):
            with self.subTest(patch=patch), self.assertRaises(s.SapModernError):
                s.detail(body(patch), URI)

    def test_missing_short_or_ambiguous_primary_body_refuses(self):
        for raw in (body(primary="<p>Short.</p>"), body().replace(b"The Role", b"Unqualified block"),
                    body().replace(b"</html>", b"<div class='max-w-3xl'><h2>The Role</h2>Ambiguous.</div></html>")):
            with self.subTest(raw=raw[:35]), self.assertRaises(s.SapModernError):
                s.detail(raw, URI)

    def test_unsafe_html_is_data_and_generic_context_is_not_primary_requirements(self):
        source = "<p onclick='unsafe()'>" + "Full actual requirement. " * 20 + "</p><script>unsafe()</script><a href='javascript:unsafe()'>Label</a>"
        result = s.detail(body(primary=source), URI)
        self.assertNotIn("unsafe", result["description_html"])
        self.assertNotIn("Separate generic company", result["description"])
        self.assertIn("Separate generic company", result["native_page_context_sections"][0]["text"])

    def test_read_requests_only_robots_and_exact_public_html_with_wire_hash(self):
        transport = Transport()
        result = s.read("inventory", s.BOARD, transport=transport)
        self.assertEqual([s.ORIGIN + "/robots.txt", s.BOARD], [u for u, _ in transport.calls])
        self.assertEqual(64, len(result["provenance"]["sha256"]))
        self.assertFalse(result["hydration_credentials_exported_or_used"])
        self.assertFalse(result["source_scripts_images_or_application_requested"])

    def test_policy_denial_stops_before_public_job_request(self):
        transport = Transport(robots=b"User-agent: *\nDisallow: /en/jobs/\n")
        with self.assertRaisesRegex(s.SapModernError, "robots_denied"):
            s.read("inventory", s.BOARD, transport=transport)
        self.assertEqual(1, len(transport.calls))

    def test_access_failure_retains_status_and_retry_after_without_fake_zero_count(self):
        transport = Transport(failure=PublicError("source_http_error", http_status=429, retry_after="60"))
        with self.assertRaises(s.SapModernError) as captured:
            s.read("inventory", s.BOARD, transport=transport)
        self.assertEqual((429, "60"), (captured.exception.http_status, captured.exception.retry_after))


if __name__ == "__main__":
    unittest.main()
