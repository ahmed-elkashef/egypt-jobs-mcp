import json
import unittest
from io import BytesIO
from urllib.error import HTTPError

import reader

BOARD = "https://example.wd3.myworkdayjobs.com/en-US/External"
PATH = "/job/City/Role_REQ-12"


def raw(value):
    return json.dumps(value).encode()


def card(path=PATH):
    return {"title": "Student internship", "externalPath": path, "locationsText": "2 Locations",
            "postedOn": "Posted 30+ Days Ago", "bulletFields": ["REQ-12"], "remoteType": "Remote"}


def page(rows=None, total=3):
    return {"total": total, "jobPostings": [card()] if rows is None else rows, "userAuthenticated": False,
            "facets": [{"descriptor": "Germany", "id": "country-id"}]}


def body():
    return {"userAuthenticated": False, "jobPostingInfo": {
        "id": "native-posting-id", "title": "Student internship", "jobReqId": "REQ-12",
        "jobDescription": "<p>Responsibilities</p><ul><li>First item</li><li>Second item</li></ul><p>Separate instructions and required documents.</p>",
        "externalUrl": "https://example.wd3.myworkdayjobs.com/External" + PATH,
        "country": {"descriptor": "Germany", "id": "country-id"}, "location": "Frankfurt",
        "postedOn": "Posted Today", "startDate": "2026-10-29", "timeType": "Full time",
        "questionnaireId": "not-job-content", "canApply": True,
    }, "similarJobs": [{"title": "Not the requested posting"}]}


class ReaderTests(unittest.TestCase):
    def test_explicit_native_board_variants(self):
        self.assertEqual(reader.board(BOARD)["tenant"], "example")
        self.assertEqual(reader.board(BOARD + "/")["board_url"], BOARD)
        self.assertEqual(reader.board(BOARD.replace("en-US/", ""))["site"], "External")
        self.assertEqual(reader.board(BOARD.replace("wd3", "wd103"))["tenant"], "example")

    def test_non_provider_auth_query_and_route_inputs_fail_before_network(self):
        for value in [None, "http://example.wd3.myworkdayjobs.com/External", "https://example.wd3.myworkdayjobs.com.evil.test/External",
                      BOARD + "?query=PR", BOARD + "#x", BOARD + "/job/role", BOARD.replace("https://", "https://user:pass@"),
                      BOARD.replace("wd3.myworkdayjobs.com", "wd3.myworkdayjobs.com:443"), "https://[broken/External"]:
            with self.subTest(value=value), self.assertRaises(reader.SourceError):
                reader.read(value, transport=lambda *_a, **_k: self.fail("unexpected network"))

    def test_exact_native_unicode_path_is_safe_and_idempotent(self):
        path = "/job/Köln/Praktikum_REQ-12"
        encoded = reader.external_path(path)
        self.assertIn("K%C3%B6ln", encoded)
        self.assertEqual(reader.external_path(encoded), encoded)

    def test_application_and_traversal_paths_are_refused(self):
        for value in [None, "/apply/12", "/job/City/Role/apply", "/job/../account", "/job/%2e%2e/account",
                      "/job/A%2fB/Role", "/job/City/Role?apply=1", "/job/City/Role#x", "/job/City/%252e%252e", "/job/City/Role\n"]:
            with self.subTest(value=value), self.assertRaises(reader.SourceError):
                reader.external_path(value)

    def test_whole_page_and_native_continuation_preserve_ambiguity(self):
        result = reader.inventory(raw(page()), BOARD)
        self.assertEqual(result["source_result_count"], 3)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["continuation"], {"board_url": BOARD, "offset": 1, "limit": 20, "first_page_total": 3})
        self.assertIsNone(result["jobs"][0]["country"])
        self.assertIsNone(result["jobs"][0]["original_published_at"])
        self.assertEqual(result["jobs"][0]["posted_on_raw"], "Posted 30+ Days Ago")
        self.assertIsNone(result["native_pagination"]["server_offset_echo"])
        self.assertFalse(result["coverage_complete"])

    def test_requisition_id_is_not_a_unique_posting_identity(self):
        data = page([card(), card(PATH + "-2")], 2)
        result = reader.inventory(raw(data), BOARD)
        self.assertEqual(len({r["source_id"] for r in result["jobs"]}), 2)
        self.assertIsNone(result["continuation"])

    def test_reported_empty_is_distinct_from_inconsistent_empty(self):
        result = reader.inventory(raw(page([], 0)), BOARD)
        self.assertEqual(result["count"], 0)
        self.assertIsNone(result["continuation"])
        with self.assertRaises(reader.SourceError):
            reader.inventory(raw(page([], 3)), BOARD)

    def test_out_of_range_offset_is_refused_before_native_page_one_reset(self):
        with self.assertRaises(reader.SourceError):
            reader.read(BOARD, offset=3, first_page_total=3,
                        transport=lambda *_a, **_kw: self.fail("unexpected network"))

    def test_duplicate_and_malformed_cards_are_not_silently_dropped(self):
        for rows in [[card(), card()], [card(), None], [card(), {}]]:
            with self.subTest(rows=rows), self.assertRaises(reader.SourceError):
                reader.inventory(raw(page(rows, 3)), BOARD)

    def test_count_limit_and_offset_inconsistencies_fail_closed(self):
        for data, args in [(page(total=True), {}), (page(total=-1), {}), (page([card(), card(PATH + "-2")], 2), {"limit": 1}),
                           (page(total=1), {"offset": 1}), (page(), {"offset": True}), (page(), {"limit": 21})]:
            with self.subTest(args=args), self.assertRaises(reader.SourceError):
                reader.inventory(raw(data), BOARD, **args)

    def test_authentication_and_nonfinite_json_never_become_empty(self):
        for value in [raw({"userAuthenticated": True}), raw({"total": 0}), b'{"userAuthenticated":false,"total":NaN}',
                      b'{"userAuthenticated":false,"userAuthenticated":false}', b'not JSON', b'[]']:
            with self.subTest(value=value), self.assertRaises(reader.SourceError):
                reader.inventory(value, BOARD)

    def test_complete_source_body_and_native_metadata_are_separate_from_clocks_and_fit(self):
        result = reader.detail(raw(body()), BOARD, PATH)
        self.assertEqual(result["source_description"], "Responsibilities First item Second item Separate instructions and required documents.")
        self.assertEqual(result["source_description_html"], body()["jobPostingInfo"]["jobDescription"])
        self.assertEqual(result["native_job_posting_id"], "native-posting-id")
        self.assertEqual(result["source_id"], BOARD.replace("en-US/", "") + PATH)
        self.assertEqual(result["source_start_date_raw"], "2026-10-29")
        self.assertIsNone(result["original_published_at"])
        self.assertIsNone(result["visible_description"])
        self.assertEqual(result["native_fields"]["timeType"], "Full time")
        self.assertNotIn("questionnaireId", result["native_fields"])
        self.assertNotIn("similarJobs", result)

    def test_wrong_tenant_site_and_posting_fail_identity_check(self):
        for url in ["https://other.wd3.myworkdayjobs.com/External" + PATH, BOARD.replace("External", "Internal") + PATH,
                    BOARD + PATH + "-2", BOARD + PATH + "?apply=1", None, 4, "https://[broken/External" + PATH]:
            data = body()
            data["jobPostingInfo"]["externalUrl"] = url
            with self.subTest(url=url), self.assertRaises(reader.SourceError):
                reader.detail(raw(data), BOARD, PATH)

    def test_empty_body_and_placeholder_detail_are_refused(self):
        for change in [{"jobDescription": ""}, {"jobDescription": "<script>not a description</script>"}, {"id": ""}, {"title": None}]:
            data = body()
            data["jobPostingInfo"].update(change)
            with self.subTest(change=change), self.assertRaises(reader.SourceError):
                reader.detail(raw(data), BOARD, PATH)

    def test_native_search_post_is_fixed_empty_filter_and_keyword(self):
        seen = []
        result = reader.read(BOARD, offset=20, first_page_total=30, transport=lambda url, **kw: (seen.append((url, kw)) or (b"User-agent: *\n" if url.endswith("robots.txt") else raw(page(total=30)))))
        self.assertEqual(len(seen), 2)
        self.assertEqual(json.loads(seen[1][1]["payload"]), {"appliedFacets": {}, "limit": 20, "offset": 20, "searchText": ""})
        self.assertEqual(result["request_method"], "POST")
        self.assertEqual(result["request_url"], "https://example.wd3.myworkdayjobs.com/wday/cxs/example/External/jobs")
        self.assertEqual(seen[0][1]["accept"], "text/plain")

    def test_native_zero_total_nonempty_offset_page_continues_without_invented_count(self):
        result = reader.inventory(raw(page(total=0)), BOARD, offset=20, first_page_total=30)
        self.assertEqual(result["count"], 1)
        self.assertIsNone(result["source_result_count"])
        self.assertEqual(result["native_pagination"]["reported_total_raw"], 0)
        self.assertEqual(result["continuation"]["offset"], 21)
        with self.assertRaises(reader.SourceError):
            reader.inventory(raw(page(total=0)), BOARD)

    def test_final_nonempty_page_stops_at_initial_total_without_an_empty_probe(self):
        result = reader.inventory(raw(page([card(), card(PATH + "-2")], total=0)), BOARD,
                                  offset=920, first_page_total=922)
        self.assertEqual(result["count"], 2)
        self.assertIsNone(result["continuation"])
        self.assertTrue(result["native_pagination"]["initial_total_bound_reached"])
        self.assertIsNone(result["source_result_count"])
        self.assertFalse(result["coverage_complete"])

    def test_initial_total_change_and_missing_context_are_limits(self):
        for total, offset, initial in [(31, 20, 30), (3, 0, 4), (0, 20, None)]:
            with self.subTest(total=total, offset=offset), self.assertRaises(reader.SourceError):
                reader.inventory(raw(page(total=total)), BOARD, offset=offset, first_page_total=initial)

    def test_external_path_identity_is_tenant_and_site_scoped_not_locale_scoped(self):
        first = reader.inventory(raw(page()), BOARD)["jobs"][0]["source_id"]
        other_tenant = reader.inventory(raw(page()), BOARD.replace("example.", "another."))["jobs"][0]["source_id"]
        other_site = reader.inventory(raw(page()), BOARD.replace("External", "Careers"))["jobs"][0]["source_id"]
        other_locale = reader.inventory(raw(page()), BOARD.replace("en-US/", "de-DE/"))["jobs"][0]["source_id"]
        self.assertNotEqual(first, other_tenant)
        self.assertNotEqual(first, other_site)
        self.assertEqual(first, other_locale)

    def test_detail_only_gets_exact_native_job_endpoint(self):
        seen = []
        def transport(url, **kwargs):
            seen.append((url, kwargs))
            return b"User-agent: *\n" if url.endswith("robots.txt") else raw(body())
        result = reader.read(BOARD, path=PATH, transport=transport)
        self.assertIsNone(seen[1][1]["payload"])
        self.assertEqual(result["request_method"], "GET")
        self.assertTrue(result["request_url"].endswith("/External" + PATH))

    def test_policy_denial_stops_before_source_request(self):
        seen = []
        def transport(url, **kwargs):
            seen.append(url)
            return b"User-agent: *\nDisallow: /wday/cxs/\n"
        with self.assertRaises(reader.SourceError):
            reader.read(BOARD, transport=transport)
        self.assertEqual(len(seen), 1)

    def test_robots_missing_is_not_denial_but_forbidden_and_server_errors_are(self):
        for status in [404, 410, 403, 429, 503]:
            seen = []
            def transport(url, **kwargs):
                seen.append(url)
                if url.endswith("robots.txt"):
                    raise reader.SourceError("source_http_error", http_status=status)
                return raw(page())
            if status in [404, 410]:
                self.assertTrue(reader.read(BOARD, transport=transport)["policy"]["robots_allowed"])
                self.assertEqual(len(seen), 2)
            else:
                with self.assertRaises(reader.SourceError):
                    reader.read(BOARD, transport=transport)
                self.assertEqual(len(seen), 1)

    def test_html_robot_challenge_is_not_an_allow_policy(self):
        with self.assertRaises(reader.SourceError):
            reader.read(BOARD, transport=lambda *_a, **_k: b"<!doctype html><html>Challenge</html>")

    def test_invalid_detail_pagination_and_paths_stop_before_policy(self):
        for args in [{"path": PATH, "offset": 20}, {"path": "/apply/12"}, {"limit": True}]:
            with self.subTest(args=args), self.assertRaises(reader.SourceError):
                reader.read(BOARD, transport=lambda *_a, **_k: self.fail("unexpected network"), **args)

    def test_transport_does_not_follow_redirects_and_preserves_retry_after(self):
        class Opener:
            def open(self, req, timeout):
                self.req = req
                raise HTTPError(req.full_url, 429, "limited", {"Retry-After": "60"}, BytesIO())
        opener = Opener()
        with self.assertRaises(reader.SourceError) as failure:
            reader.request("https://example.wd3.myworkdayjobs.com/x", payload=b"{}", opener=opener)
        self.assertEqual(failure.exception.http_status, 429)
        self.assertEqual(failure.exception.retry_after, "60")
        self.assertEqual(opener.req.method, "POST")
        self.assertNotIn("Authorization", opener.req.headers)
        self.assertNotIn("Cookie", opener.req.headers)
        self.assertIsNone(reader.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test"))

    def test_response_bound_never_slices_source_into_success(self):
        class Response:
            status = 200
            def read(self, limit):
                return b"x" * limit
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                pass
        class Opener:
            def open(self, *_args, **_kwargs):
                return Response()
        with self.assertRaises(reader.SourceError):
            reader.request("https://example.wd3.myworkdayjobs.com/x", bound=10, opener=Opener())


if __name__ == "__main__":
    unittest.main()
