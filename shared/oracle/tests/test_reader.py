import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reader
from public_http import SourceError


def encoded(item, **changes):
    return json.dumps({"items": [item], "count": 1, "hasMore": False,
                       "limit": 200, "offset": 0, **changes}).encode()


def inventory(total=30, offset=0, country=None):
    return {
        "SiteNumber": reader.SITE, "Facets": "NONE", "LocationId": reader.COUNTRIES.get(country),
        "TotalJobsCount": total, "Limit": 25, "Offset": offset, "SortBy": "RELEVANCY",
        "Keyword": None, "CandidateNumber": None,
        "requisitionList": [
            {"Id": str(210000000 + n), "Title": f"Synthetic posting {n}", "PrimaryLocation": "Example",
             "PrimaryLocationCountry": "DE", "secondaryLocations": [], "PostedDate": "2026-10-29",
             "JobSchedule": None, "JobType": None}
            for n in range(offset, min(offset + 25, total))
        ],
    }


def detail():
    return {
        "Id": "210000001", "Title": "Synthetic student posting", "RequisitionId": 300000001,
        "ExternalDescriptionStr": "<p>" + "Complete public primary description. " * 10 + "</p>",
        "ExternalResponsibilitiesStr": "<p>Full responsibilities.</p>",
        "ExternalQualificationsStr": "<p>Full qualifications.</p>",
        "CorporateDescriptionStr": "<p>Full employer context.</p>",
        "OrganizationDescriptionStr": "",
        "InternalQualificationsStr": "Private internal text must not be exported.",
        "InternalResponsibilitiesStr": "Internal responsibilities must not be exported.",
        "HiringManager": "Not a public description field",
        "ApplyWhenNotPostedFlag": True,
        "ExternalPostedStartDate": "2026-09-30T23:00:00+00:00",
        "JobSchedule": "Part time", "RequisitionType": "Campus",
        "secondaryLocations": [{"Name": "Additional location"}],
    }


class OracleReaderTests(unittest.TestCase):
    def test_capabilities_are_offline_and_scope_specific(self):
        result = reader.capabilities()
        self.assertEqual(result["independently_verified_boards"], [reader.BOARD])
        self.assertEqual(result["acquisition_role_filters"], [])
        self.assertFalse(result["coverage_complete"])

    def test_outer_one_search_container_is_not_one_job(self):
        result = reader.parse_inventory(encoded(inventory()), reader.BOARD)
        self.assertEqual(result["source_result_count"], 30)
        self.assertEqual(result["returned_count"], 25)
        self.assertTrue(result["has_more"])
        self.assertEqual(result["next_page"], 2)
        self.assertIn("offset%3D25", result["next_uri"])

    def test_native_country_partition_and_raw_metadata_survive(self):
        source = inventory(country="DE")
        result = reader.parse_inventory(encoded(source), reader.BOARD, country="DE")
        self.assertEqual(result["native_search_fields"]["LocationId"], "300000000289216")
        self.assertEqual(result["listings"][0]["native_row"], source["requisitionList"][0])
        self.assertIsNone(result["listings"][0]["original_published_at"])
        self.assertFalse(result["listings"][0]["full_posting_reviewed"])

    def test_final_native_page_reconciles_without_outer_pagination(self):
        result = reader.parse_inventory(encoded(inventory(offset=25)), reader.BOARD,
                                        page=2, first_page_total=30)
        self.assertEqual(result["returned_count"], 5)
        self.assertFalse(result["has_more"])
        self.assertIsNone(result["next_uri"])

    def test_empty_wrapper_is_unknown_not_zero_supply(self):
        for value in [{}, [], {"items": [], "count": 0, "hasMore": False}]:
            with self.subTest(value=value), self.assertRaises(SourceError):
                reader.parse_inventory(json.dumps(value).encode(), reader.BOARD)

    def test_explicit_zero_native_search_is_a_qualified_zero(self):
        result = reader.parse_inventory(encoded(inventory(total=0)), reader.BOARD)
        self.assertEqual(result["returned_count"], 0)
        self.assertEqual(result["source_result_count"], 0)
        self.assertFalse(result["has_more"])
        self.assertFalse(result["coverage_complete"])

    def test_missing_rows_and_duplicate_identities_refuse_whole_page(self):
        for mutate in [
            lambda x: x["requisitionList"].pop(),
            lambda x: x["requisitionList"].__setitem__(1, copy.deepcopy(x["requisitionList"][0])),
            lambda x: x["requisitionList"][0].__setitem__("Id", "../apply"),
            lambda x: x["requisitionList"][0].__setitem__("Title", ""),
        ]:
            item = inventory()
            mutate(item)
            with self.subTest(mutate=mutate), self.assertRaises(SourceError):
                reader.parse_inventory(encoded(item), reader.BOARD)

    def test_scope_echo_prevents_ignored_or_changed_filters(self):
        for key, value in [("SiteNumber", "CX_1002"), ("LocationId", "wrong"),
                           ("Offset", 25), ("Limit", 50), ("SortBy", "OTHER"), ("Facets", "OTHER")]:
            item = inventory()
            item[key] = value
            with self.subTest(key=key), self.assertRaises(SourceError):
                reader.parse_inventory(encoded(item), reader.BOARD)

    def test_role_date_facet_and_candidate_contamination_are_rejected(self):
        for key in ["Keyword", "CandidateNumber", "SelectedTitlesFacet", "SelectedCategoriesFacet",
                    "SelectedPostingDatesFacet", "SelectedLocationsFacet", "JobFamilyId",
                    "PostingStartDate", "RequisitionId", "SelectedOrganizationsFacet",
                    "WorkLocationCountryCode", "HotJobFlag", "SelectedWorkplaceTypesFacet",
                    "Location", "Latitude", "Longitude", "WorkplaceType", "Radius"]:
            item = inventory()
            item[key] = "unexpected"
            with self.subTest(key=key), self.assertRaises(SourceError):
                reader.parse_inventory(encoded(item), reader.BOARD)

    def test_frozen_total_continuation_and_outside_bounds(self):
        for args in [{"page": 2}, {"page": 2, "first_page_total": 31},
                     {"page": 3, "first_page_total": 30}]:
            with self.subTest(args=args), self.assertRaises(SourceError):
                reader.parse_inventory(encoded(inventory(offset=25)), reader.BOARD, **args)

    def test_bool_float_negative_and_oversized_numeric_arguments(self):
        for key in ["page", "first_page_total"]:
            for value in [True, 1.5, -1, 10000001]:
                with self.subTest(key=key, value=value), self.assertRaises(SourceError):
                    reader.inventory_uri(reader.BOARD, **{key: value})
        for key in ["TotalJobsCount", "Limit", "Offset"]:
            item = inventory()
            item[key] = True
            with self.subTest(key=key), self.assertRaises(SourceError):
                reader.parse_inventory(encoded(item), reader.BOARD)
        for value in [True, 1.0, 0, 2]:
            with self.subTest(wrapper_count=value), self.assertRaises(SourceError):
                reader.parse_inventory(encoded(inventory(), count=value), reader.BOARD)

    def test_unknown_sites_and_application_urls_are_pre_network_errors(self):
        for value in [reader.BOARD + "?keyword=PR", reader.BOARD.replace("CX_1001", "CX_1002"),
                      "https://example.com/jobs"]:
            with self.subTest(value=value), self.assertRaises(SourceError):
                reader.read(board_url=value, transport=lambda *a, **kw: self.fail("network"))
        for value in [reader.job_uri("210000001") + "?apply=true",
                      reader.job_uri("210000001").replace("/job/", "/apply/"),
                      reader.job_uri("210000001").replace("jpmc.fa", "elsewhere.fa"),
                      reader.job_uri("210000001") + "#apply",
                      reader.job_uri("210000001").replace("/job/", "/%6aob/")]:
            with self.subTest(value=value), self.assertRaises(SourceError):
                reader.read(job_url=value, transport=lambda *a, **kw: self.fail("network"))

    def test_all_public_sections_and_distinct_ids_survive(self):
        source = detail()
        result = reader.parse_detail(encoded(source), reader.job_uri("210000001"))
        self.assertEqual(result["native_requisition_id"], 300000001)
        self.assertEqual(result["native_job_id"], "210000001")
        self.assertEqual(set(result["native_public_sections"]), set(reader.SECTIONS))
        self.assertEqual(result["native_public_fields"]["ExternalDescriptionStr"], source["ExternalDescriptionStr"])
        self.assertEqual(result["native_public_fields"]["JobSchedule"], "Part time")
        self.assertIsNone(result["original_published_at"])
        self.assertFalse(result["full_posting_reviewed"])
        self.assertTrue(result["source_body_untruncated"])

    def test_internal_and_application_controls_are_not_exported(self):
        result = reader.parse_detail(encoded(detail()), reader.job_uri("210000001"))
        for key in ["InternalQualificationsStr", "InternalResponsibilitiesStr", "HiringManager", "ApplyWhenNotPostedFlag"]:
            self.assertNotIn(key, result["native_public_fields"])
            self.assertIn(key, result["omitted_internal_or_nonpublic_field_names"])
        self.assertNotIn("Private internal text", json.dumps(result))

    def test_long_source_sections_are_not_summarised_or_cut(self):
        source = detail()
        source["ExternalDescriptionStr"] = "<p>" + "Complete source. " * 20000 + "FINAL SENTENCE.</p>"
        result = reader.parse_detail(encoded(source), reader.job_uri("210000001"))
        self.assertTrue(result["description"].endswith("FINAL SENTENCE."))
        self.assertGreater(result["native_description_characters"], 300000)

    def test_missing_sections_identity_drift_and_short_primary_refuse(self):
        for mutate in [lambda x: x.pop("CorporateDescriptionStr"),
                       lambda x: x.__setitem__("Id", "210000002"),
                       lambda x: x.__setitem__("ExternalDescriptionStr", "<p>Short</p>"),
                       lambda x: x.__setitem__("ExternalQualificationsStr", []),
                       lambda x: x.__setitem__("RequisitionId", True)]:
            source = detail()
            mutate(source)
            with self.subTest(mutate=mutate), self.assertRaises(SourceError):
                reader.parse_detail(encoded(source), reader.job_uri("210000001"))

    def test_script_and_event_handlers_do_not_survive_safe_html(self):
        result = reader.section('<p onclick="bad()">Visible words</p><script>bad()</script><a href="javascript:bad()">Link</a>')
        self.assertEqual(result["text"], "Visible words Link")
        self.assertNotIn("bad()", result["html"])

    def test_qualified_unavailable_robot_is_distinct_from_content_denial(self):
        calls = []
        def transport(url, **kwargs):
            calls.append(url)
            if url.endswith("/robots.txt"):
                raise SourceError("source_http_error", http_status=403)
            return {"body": encoded(inventory()), "content_type": "application/json"}
        result = reader.read(board_url=reader.BOARD, transport=transport)
        self.assertEqual(result["policy"]["robots_status"], 403)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["source_result_count"], 30)

    def test_actual_api_denial_is_never_retried_or_bypassed(self):
        calls = []
        def transport(url, **kwargs):
            calls.append(url)
            if url.endswith("/robots.txt"):
                raise SourceError("source_http_error", http_status=403)
            raise SourceError("source_http_error", http_status=403)
        with self.assertRaises(SourceError) as error:
            reader.read(board_url=reader.BOARD, transport=transport)
        self.assertEqual(error.exception.http_status, 403)
        self.assertEqual(len(calls), 2)

    def test_robot_throttling_or_server_failure_stops_before_jobs(self):
        for status, retry in [(429, "60"), (503, None), (401, None), (403, "30")]:
            calls = []
            def transport(url, **kwargs):
                calls.append(url)
                raise SourceError("source_http_error", http_status=status, retry_after=retry)
            with self.subTest(status=status), self.assertRaises(SourceError):
                reader.read(board_url=reader.BOARD, transport=transport)
            self.assertEqual(len(calls), 1)

    def test_robot_disallow_and_html_challenge_stop_before_jobs(self):
        for body in [b"User-agent: *\nDisallow: /hcmRestApi/", b"<html>Challenge</html>"]:
            calls = []
            def transport(url, **kwargs):
                calls.append(url)
                return {"body": body, "content_type": "text/plain"}
            with self.subTest(body=body), self.assertRaises(SourceError):
                reader.read(board_url=reader.BOARD, transport=transport)
            self.assertEqual(len(calls), 1)

    def test_html_or_partial_json_content_cannot_be_zero_supply(self):
        for content_type, body in [("text/html", b"<html>challenge</html>"),
                                   ("application/json", b'{"items":')]:
            def transport(url, **kwargs):
                if url.endswith("/robots.txt"):
                    return {"body": b"User-agent: *\nAllow: /", "content_type": "text/plain"}
                return {"body": body, "content_type": content_type}
            with self.subTest(content_type=content_type), self.assertRaises(SourceError):
                reader.read(board_url=reader.BOARD, transport=transport)

    def test_duplicate_json_keys_are_not_accepted(self):
        with self.assertRaises(SourceError):
            reader.parse_inventory(b'{"count":1,"count":0}', reader.BOARD)


if __name__ == "__main__":
    unittest.main()
