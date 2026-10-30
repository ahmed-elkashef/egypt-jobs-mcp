"""Synthetic protocol and safety tests; never a live source or coverage receipt."""
import copy
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.robotparser import RobotFileParser

import gulp_jobs as source


def row(number=1):
    identifier = f"C{number:08}"
    return {"id": identifier, "idInIndex": identifier, "type": "TEMP_JOB", "title": "Synthetic role",
            "location": "Synthetic location", "url": source.FRONT + identifier, "description": "Preview...",
            "skills": ["Synthetic qualification"], "isRemoteWorkPossible": False}


def page(total=21, numbers=range(1, 21)):
    return {"totalCount": total, "projects": [row(n) for n in numbers]}


def detail():
    return {**row(), "description": "Whole public role introduction.", "responsibilities": "<p>Whole responsibilities.</p>",
            "skills": "<p>Whole qualifications.</p>", "benefits": "<p>Published benefits and <b>part-time wording</b>.</p>",
            "salary": "Published salary", "schedule": "FULL_TIME", "metaJobPosting": '{"@type":"JobPosting"}'}


class FakeClient:
    def __init__(self, data, content_type="application/json"):
        self.raw = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.calls, self.content_type = [], content_type

    def post(self, payload):
        self.calls.append(payload)
        return {"body": self.raw, "content_type": self.content_type}

    def get(self, url):
        self.calls.append(url)
        return {"body": self.raw, "content_type": self.content_type}


class GulpTests(unittest.TestCase):
    def test_initial_page_preserves_every_raw_record_and_native_next(self):
        data = page()
        result = source.parse_inventory(data)
        self.assertEqual(result["returned_count"], 20)
        self.assertEqual(result["source_result_count"], 21)
        self.assertEqual([r["native_metadata"] for r in result["records"]], data["projects"])
        self.assertEqual(result["next_request"]["arguments"], {"page": 1, "first_page_total": 21})
        self.assertFalse(result["records"][0]["description_is_full_primary"])
        self.assertFalse(result["coverage_complete"])

    def test_native_terminal_partial_page_is_not_whole_source_coverage(self):
        result = source.parse_inventory(page(numbers=[21]), page=1, first_page_total=21)
        self.assertEqual(result["returned_count"], 1)
        self.assertTrue(result["native_terminal_page"])
        self.assertIsNone(result["next_request"])
        self.assertFalse(result["coverage_complete"])

    def test_genuine_empty_native_source_is_counted_without_coverage_claim(self):
        result = source.parse_inventory(page(0, []))
        self.assertEqual(result["returned_count"], 0)
        self.assertEqual(result["source_result_count"], 0)
        self.assertFalse(result["reviewed_by_model"])

    def test_count_drift_refuses_instead_of_truncating_or_resetting(self):
        with self.assertRaisesRegex(source.SourceError, "counter_changed"):
            source.parse_inventory(page(22, [21, 22]), page=1, first_page_total=21)

    def test_short_middle_and_oversized_pages_refuse(self):
        for numbers in (range(1, 20), range(1, 22)):
            with self.subTest(numbers=numbers), self.assertRaises(source.SourceError):
                source.parse_inventory(page(numbers=numbers))

    def test_counter_requires_bounded_native_integer(self):
        for total in (True, None, -1, 1.5, 10_000_001):
            with self.subTest(total=total), self.assertRaises(source.SourceError):
                source.parse_inventory(page(total))

    def test_page_and_continuation_state_refuse_before_any_request(self):
        for kwargs in ({"page": True}, {"page": -1}, {"page": 0, "first_page_total": 21},
                       {"page": 1}, {"page": 2, "first_page_total": 21}, {"page": 1, "first_page_total": True}):
            client = FakeClient(page())
            with self.subTest(kwargs=kwargs), self.assertRaises(source.SourceError):
                source.read("inventory", client=client, **kwargs)
            self.assertEqual(client.calls, [])

    def test_duplicate_native_id_is_never_silently_deduplicated(self):
        data = page()
        data["projects"][1] = copy.deepcopy(data["projects"][0])
        with self.assertRaisesRegex(source.SourceError, "duplicate_native_identity"):
            source.parse_inventory(data)

    def test_identity_alias_mismatch_refuses(self):
        data = page()
        data["projects"][0]["idInIndex"] = "C00000099"
        with self.assertRaisesRegex(source.SourceError, "identity_disagrees"):
            source.parse_inventory(data)

    def test_unknown_contract_type_cannot_become_student_model(self):
        for kind in ("INTERNSHIP", None, []):
            data = page()
            data["projects"][0]["type"] = kind
            with self.subTest(kind=kind), self.assertRaises(source.SourceError):
                source.parse_inventory(data)

    def test_malformed_preview_skills_and_remote_metadata_refuse(self):
        for key, value in (("description", None), ("skills", [None]), ("skills", "text"), ("isRemoteWorkPossible", None)):
            data = page()
            data["projects"][0][key] = value
            with self.subTest(key=key), self.assertRaises(source.SourceError):
                source.parse_inventory(data)

    def test_nonempty_account_state_is_never_exported(self):
        for field in source.ACCOUNT_FIELDS:
            data = detail()
            data[field] = "unexpected personalized value"
            with self.subTest(field=field), self.assertRaisesRegex(source.SourceError, "personalized"):
                source.parse_detail(data, url=row()["url"])

    def test_complete_primary_retains_all_fields_and_conflicting_schedule(self):
        data = detail()
        result = source.parse_detail(data, url=row()["url"])
        self.assertEqual(result["native_detail"], data)
        self.assertIn("part-time wording", result["full_description"])
        self.assertEqual(result["native_schedule"], "FULL_TIME")
        self.assertTrue(result["full_description_acquired"])
        self.assertFalse(result["full_posting_reviewed"])
        self.assertFalse(result["native_contract_type_is_student_model_proof"])

    def test_requested_and_returned_primary_ids_must_match(self):
        with self.assertRaisesRegex(source.SourceError, "identity_disagree"):
            source.parse_detail(detail(), url=row(2)["url"])

    def test_missing_or_empty_full_role_fields_are_not_a_primary(self):
        for key in ("responsibilities", "skills", "benefits", "schedule", "salary"):
            data = detail()
            data.pop(key)
            with self.subTest(key=key), self.assertRaises(source.SourceError):
                source.parse_detail(data, url=row()["url"])
        data = detail()
        data["responsibilities"] = ""
        with self.assertRaises(source.SourceError):
            source.parse_detail(data, url=row()["url"])

    def test_malformed_published_schema_is_preserved_without_repair(self):
        data = detail()
        data["metaJobPosting"] = '{"broken": '
        result = source.parse_detail(data, url=row()["url"])
        self.assertIsNone(result["published_job_posting"])
        self.assertEqual(result["published_job_posting_parse_error"], "invalid_native_json")
        self.assertEqual(result["native_detail"]["metaJobPosting"], data["metaJobPosting"])

    def test_text_projection_preserves_unicode_and_omits_controls_and_programs(self):
        self.assertEqual(source.text_only('<p>Grüße &amp; Büros</p><script>do_evil()</script><form>Apply</form><p>Role</p>'),
                         'Grüße & Büros\nRole')

    def test_fixed_search_payload_has_no_private_or_career_filters(self):
        client = FakeClient(page())
        source.read("inventory", client=client)
        self.assertEqual(client.calls, [{"query": None, "page": 0, "limit": 20, "language": "DE"}])

    def test_detail_uses_only_exact_public_read_api(self):
        client = FakeClient(detail())
        source.read("detail", url=row()["url"], client=client)
        self.assertEqual(client.calls, [source.DETAIL + "C00000001?language=DE"])

    def test_arbitrary_hosts_encoded_paths_queries_and_application_routes_refuse(self):
        client = FakeClient(detail())
        url = row()["url"]
        for target in (url + "\n", url + "?x=1", url + "/bewerbung-ohne-profil", url.replace("www.gulp.de", "evil.invalid"), url.replace("/C", "/%43")):
            with self.subTest(target=target), self.assertRaises(source.SourceError):
                source.read("detail", url=target, client=client)
        self.assertEqual(client.calls, [])

    def test_content_type_is_not_sniffed_or_repaired(self):
        with self.assertRaisesRegex(source.SourceError, "not_JSON"):
            source.read("inventory", client=FakeClient(page(), "text/html"))

    def test_native_utf8_must_be_exact(self):
        with self.assertRaisesRegex(source.SourceError, "strict_UTF8"):
            source.read("inventory", client=FakeClient(b'{"bad":"\xff"}'))

    def test_duplicate_json_keys_refuse(self):
        with self.assertRaisesRegex(source.SourceError, "invalid_native_json"):
            source.read("inventory", client=FakeClient(b'{"totalCount":0,"totalCount":1,"projects":[]}'))

    def test_only_qualified_routes_and_methods_can_reach_transport(self):
        for target, method in ((source.SEARCH, "GET"), (source.FRONT + "C00000001", "GET"),
                               (source.DETAIL + "C00000001?language=EN", "GET"), (source.SEARCH + "/apply", "POST")):
            with self.subTest(target=target), self.assertRaises(source.SourceError):
                source.checked_read_route(target, method)

    def test_post_payload_guard_rejects_extra_or_restrictive_fields_before_policy(self):
        def no_read(*args, **kwargs):
            self.fail("Invalid search payload must never fetch policy or API")
        client = source.Client(transport=no_read)
        native = {"query": None, "page": 0, "limit": 20, "language": "DE"}
        for data in ({**native, "query": "marketing"}, {**native, "remote": True}, {**native, "page": True}, {**native, "limit": 1}):
            with self.subTest(data=data), self.assertRaises(source.SourceError):
                client.post(data)

    def test_robots_denial_stops_before_read_api(self):
        calls = []
        def policy(url, **kwargs):
            calls.append(url)
            return {"body": b"User-agent: *\nDisallow: /gulp2/rest/\n"}
        client = source.Client(transport=policy)
        with self.assertRaisesRegex(source.SourceError, "robots_denies"):
            client.guard(source.SEARCH, "POST")
        self.assertEqual(calls, [source.ORIGIN + "/robots.txt"])

    def test_wildcard_policy_cannot_be_bypassed_by_stdlib_literal_matching(self):
        client = source.Client()
        client.policy = {"robots_status": 200}
        client.rules = RobotFileParser()
        client.rules.parse(["User-agent: *", "Disallow: /gulp2/*/projects/*"])
        with self.assertRaisesRegex(source.SourceError, "denies"):
            client.guard(source.SEARCH, "POST")

    def test_actual_HTTP_search_is_fixed_read_POST_without_auth_or_cookies(self):
        calls = []
        class Response(io.BytesIO):
            status = 200
            headers = {"Content-Type": "application/json"}
        class Opener:
            def open(self, req, **kwargs):
                calls.append(req)
                return Response(b'{}')
        client = source.Client(opener=Opener())
        client.policy = {"robots_status": 200}
        client.post({"query": None, "page": 0, "limit": 20, "language": "DE"})
        self.assertEqual(len(calls), 1)
        req = calls[0]
        self.assertEqual(req.full_url, source.SEARCH)
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data), {"query": None, "page": 0, "limit": 20, "language": "DE"})
        self.assertIsNone(req.get_header("Authorization"))
        self.assertIsNone(req.get_header("Cookie"))

    def test_over_bound_native_response_is_never_parsed_or_truncated(self):
        class Response(io.BytesIO):
            status = 200
            headers = {"Content-Type": "application/json"}
        class Opener:
            def open(self, req, **kwargs):
                return Response(b'a' * 17)
        client = source.Client(opener=Opener())
        client.policy = {"robots_status": 200}
        with patch.object(source, "MAX_BYTES", 16), self.assertRaisesRegex(source.SourceError, "exceeds_bound"):
            client.post({"query": None, "page": 0, "limit": 20, "language": "DE"})

    def test_pacing_directive_refuses_uncoordinated_source_requests(self):
        client = source.Client()
        client.policy = {"robots_status": 200}
        client.rules = RobotFileParser()
        client.rules.parse(["User-agent: *", "Crawl-delay: 10"])
        with self.assertRaisesRegex(source.SourceError, "pacing_requires"):
            client.guard(source.SEARCH, "POST")

    def test_redirect_throttle_and_server_error_are_preserved_without_retry(self):
        for status in (302, 403, 429, 503):
            class Opener:
                def open(self, req, **kwargs):
                    raise HTTPError(req.full_url, status, "Synthetic source limit", {"Retry-After": "60"}, io.BytesIO())
            client = source.Client(opener=Opener())
            client.policy = {"robots_status": 200}
            with self.subTest(status=status), self.assertRaises(source.SourceError) as caught:
                client.post({"query": None, "page": 0, "limit": 20, "language": "DE"})
            self.assertEqual(caught.exception.http_status, status)
            self.assertEqual(caught.exception.retry_after, "60")


if __name__ == "__main__":
    unittest.main()
