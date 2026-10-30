"""Synthetic contract cases; no applicant records or live ad corpus."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reader as r


def inventory(total=26, page=1, country=None, *, next_link=True, count=None, title="Example role"):
    start = (page - 1) * 25 + 1
    end = min(page * 25, total)
    size = end - start + 1 if count is None else count
    heading = 'Search results for "' + r.COUNTRIES[country] + '".' if country else "SAP Jobs"
    rows = "".join(
        '<tr class="data-row"><td><a class="jobTitle-link" href="/job/Example/' + str(100000 + i) + '/">' + title
        + '</a><a class="jobTitle-link" href="/job/Example/' + str(100000 + i) + '/">' + title
        + '</a></td><td class="colLocation">Example, DE</td></tr>' for i in range(start, start + size)
    )
    link = ('<ul class="pagination"><li><a href="' + r.inventory_uri(r.BOARD, country=country, page=page + 1)
            + '">Next</a></li></ul>') if next_link and end < total else ""
    return ('<html><head><link rel="canonical" href="' + r.BOARD + '"></head><body><h1>' + heading
            + '</h1>Results ' + str(start) + ' – ' + str(end) + ' of ' + str(total) + ' Page ' + str(page)
            + ' of ' + str((total + 24) // 25) + '<table id="searchresults">' + rows + '</table>' + link
            + '</body></html>').encode()


URL = r.ORIGIN + "/job/Example/123456789/"


def detail(*, identifier="460000", canonical=URL, body=None):
    body = body or ("Complete role tasks and actual requirements. " * 100)
    return ('<html><head><link rel="canonical" href="' + canonical
            + '"></head><body><div class="jobDisplay"><h1>Example role</h1><span class="jobdescription">'
            + body + '</span><span class="joblayouttoken">Requisition ID: ' + identifier
            + '</span><span class="joblayouttoken">Posted Date: Oct 30, 2026</span>'
            + '<span class="joblayouttoken">Career Status: Student</span>'
            + '<span class="joblayouttoken">Employment Type: Limited Full Time</span>'
            + '<script>secret_not_exported</script></div></body></html>').encode()


class NativeInventoryTests(unittest.TestCase):
    def test_full_page_mobile_desktop_duplicates_are_one_native_job(self):
        data = r.parse_inventory(inventory(), r.BOARD)
        self.assertEqual(data["returned_count"], 25)
        self.assertEqual(data["source_result_count"], 26)
        self.assertEqual(data["pagination"]["next_page"], 2)
        self.assertFalse(data["coverage_complete"])

    def test_last_page_reconciles_frozen_count(self):
        data = r.parse_inventory(inventory(page=2), r.BOARD, page=2, first_page_total=26)
        self.assertEqual(data["returned_count"], 1)
        self.assertIsNone(data["pagination"]["next_url"])

    def test_country_native_heading_and_scope_preserved(self):
        for code in r.COUNTRIES:
            data = r.parse_inventory(inventory(total=4, country=code), r.BOARD, country=code)
            self.assertEqual(data["native_country_partition"], code)
            self.assertEqual(data["returned_count"], 4)
            self.assertTrue(all(row["native_country_partition"] == code for row in data["listings"]))

    def test_country_parameter_silently_ignored_is_refused(self):
        with self.assertRaisesRegex(r.SourceError, "country_partition_not_confirmed"):
            r.parse_inventory(inventory(), r.BOARD, country="DE")

    def test_missing_rows_not_successful_partial_page(self):
        with self.assertRaisesRegex(r.SourceError, "row_count_differ"):
            r.parse_inventory(inventory(count=24), r.BOARD)

    def test_unchanged_first_page_returned_as_page2_is_refused(self):
        with self.assertRaisesRegex(r.SourceError, "range_or_total_changed"):
            r.parse_inventory(inventory(), r.BOARD, page=2, first_page_total=26)

    def test_total_changes_stop_frozen_continuation(self):
        with self.assertRaisesRegex(r.SourceError, "range_or_total_changed"):
            r.parse_inventory(inventory(total=27, page=2), r.BOARD, page=2, first_page_total=26)

    def test_continuation_requires_first_page_total(self):
        with self.assertRaisesRegex(r.SourceError, "frozen_first_page_total"):
            r.parse_inventory(inventory(page=2), r.BOARD, page=2)

    def test_next_advertisement_required(self):
        with self.assertRaisesRegex(r.SourceError, "next_page_not_advertised"):
            r.parse_inventory(inventory(next_link=False), r.BOARD)

    def test_pagination_country_change_is_refused(self):
        raw = inventory(country="DE").replace(b"optionsFacetsDD_country=DE", b"optionsFacetsDD_country=EG")
        with self.assertRaisesRegex(r.SourceError, "pagination_partition_changed"):
            r.parse_inventory(raw, r.BOARD, country="DE")

    def test_pagination_sort_change_is_refused(self):
        raw = inventory().replace(b"sortDirection=desc", b"sortDirection=asc")
        with self.assertRaisesRegex(r.SourceError, "pagination_sort_changed"):
            r.parse_inventory(raw, r.BOARD)

    def test_wrong_canonical_is_not_a_native_board(self):
        with self.assertRaisesRegex(r.SourceError, "inventory_canonical"):
            r.parse_inventory(inventory().replace(r.BOARD.encode(), b"https://example.org/"), r.BOARD)

    def test_native_mobile_title_conflict_is_not_collapsed(self):
        raw = inventory().replace(b">Example role</a>", b">Different role</a>", 1)
        with self.assertRaisesRegex(r.SourceError, "reference_conflict"):
            r.parse_inventory(raw, r.BOARD)

    def test_top_jobs_without_a_search_range_not_an_empty_result(self):
        with self.assertRaisesRegex(r.SourceError, "page_range"):
            raw = ('<html><head><link rel="canonical" href="' + r.BOARD
                   + '"></head><body>No jobs match. Top Jobs: recommended roles</body></html>').encode()
            r.parse_inventory(raw, r.BOARD)

    def test_unknown_country_and_board_rejected(self):
        for value in ["https://jobs.sap.com/search/", r.BOARD + "?q=HR", "https://example.org/search/"]:
            with self.assertRaises(r.SourceError):
                r.parse_inventory(inventory(), value)
        with self.assertRaises(r.SourceError):
            r.inventory_uri(r.BOARD, country="ZZ")

    def test_invalid_continuation_values_rejected(self):
        for value in [0, -1, True, "2", 10001]:
            with self.assertRaises(r.SourceError):
                r.inventory_uri(r.BOARD, page=value)
        for value in [True, -1, "25"]:
            with self.assertRaises(r.SourceError):
                r.parse_inventory(inventory(), r.BOARD, first_page_total=value)


class NativeDetailTests(unittest.TestCase):
    def test_complete_source_and_two_distinct_id_types(self):
        data = r.parse_detail(detail(), URL)
        self.assertEqual(data["native_url_site_id"], "123456789")
        self.assertEqual(data["native_requisition_id"], "460000")
        self.assertGreater(len(data["description"]), 3000)
        self.assertNotIn("secret_not_exported", data["native_full_job_display_html"])
        self.assertTrue(data["source_body_untruncated"])

    def test_student_career_status_does_not_erase_full_time_dimension(self):
        data = r.parse_detail(detail(), URL)
        self.assertEqual(data["native_display_fields"]["Career Status"], "Student")
        self.assertEqual(data["native_display_fields"]["Employment Type"], "Limited Full Time")
        self.assertIsNone(data["original_published_at"])
        self.assertNotIn("employment_model", data)
        self.assertFalse(data["full_posting_reviewed"])

    def test_short_preview_is_not_complete_body(self):
        with self.assertRaisesRegex(r.SourceError, "complete_native_rmk_body"):
            r.parse_detail(detail(body="Short preview"), URL)

    def test_missing_requisition_identity_is_not_url_identity(self):
        with self.assertRaisesRegex(r.SourceError, "requisition_id"):
            r.parse_detail(detail().replace(b"Requisition ID:", b"Reference:"), URL)

    def test_conflicting_requisition_ids_refused(self):
        raw = detail(body=("Full source. " * 30) + "Requisition ID: 999999")
        with self.assertRaisesRegex(r.SourceError, "requisition_id"):
            r.parse_detail(raw, URL)

    def test_canonical_mismatch_not_silently_rewritten(self):
        with self.assertRaisesRegex(r.SourceError, "job_structure"):
            r.parse_detail(detail(canonical=r.ORIGIN + "/job/Other/987654321/"), URL)

    def test_applications_and_unverified_origins_refused_before_network(self):
        invalid = ["https://career5.successfactors.eu/career?career_ns=job_application", URL + "?apply=true",
                   URL + "#apply", URL.replace("careers.sap.com", "example.org"),
                   r.ORIGIN + "/job/../123456789/", r.ORIGIN + "/job/a%2fb/123456789/",
                   r.ORIGIN + "/job/a%0ab/123456789/"]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(r.SourceError):
                r.job_uri(value)

    def test_scripts_event_handlers_and_script_links_removed(self):
        raw = detail(body=("Full source. " * 30) + '<a href="javascript:secret()" onclick="secret()" data-token="secret">Policy</a>')
        data = r.parse_detail(raw, URL)
        for marker in ["javascript:", "onclick", "data-token", "secret()"]:
            self.assertNotIn(marker, data["description_html"])


class ReadSafetyTests(unittest.TestCase):
    def test_out_of_range_refused_without_request(self):
        def transport(*args, **kwargs):
            self.fail("must not request an out-of-range or application route")
        with self.assertRaisesRegex(r.SourceError, "outside_frozen_inventory"):
            r.read(board_url=r.BOARD, page=3, first_page_total=26, transport=transport)

    def test_robots_denial_stops_job_read(self):
        calls = []
        def transport(url, **kwargs):
            calls.append(url)
            return {"body": b"User-agent: *\nDisallow: /\n", "content_type": "text/plain"}
        with self.assertRaisesRegex(r.SourceError, "robots_denied"):
            r.read(job_url=URL, transport=transport)
        self.assertEqual(calls, [r.ORIGIN + "/robots.txt"])

    def test_robots404_is_qualified_not_assumed_successful_source(self):
        def transport(url, **kwargs):
            if url.endswith("/robots.txt"):
                raise r.SourceError("source_http_error", http_status=404)
            return {"body": detail(), "content_type": "text/html"}
        data = r.read(job_url=URL, transport=transport)
        self.assertEqual(data["policy"]["robots_status"], 404)
        self.assertEqual(data["provenance"]["method"], "GET")

    def test_error_body_and_wrong_content_type_not_empty_success(self):
        for response in [{"body": b"error", "content_type": "text/html", "http_status": 403},
                         {"body": b"{}", "content_type": "application/json"}]:
            def transport(url, **kwargs):
                return {"body": b"User-agent: *\nAllow: /\n", "content_type": "text/plain"} if url.endswith("/robots.txt") else response
            with self.subTest(response=response), self.assertRaises(r.SourceError):
                r.read(job_url=URL, transport=transport)

    def test_capabilities_do_not_claim_current_sap_front_or_country_coverage(self):
        data = r.capabilities()
        self.assertFalse(data["separate_current_front_implemented"])
        self.assertFalse(data["coverage_complete"])
        self.assertEqual(data["acquisition_role_filters"], [])


if __name__ == "__main__":
    unittest.main()
