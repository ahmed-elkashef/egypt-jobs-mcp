import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import far_retail as f
from shared.public_http import SourceError as PublicError


def metadata():
    return {"@odata.count": 2, "@odata.context": "public test context", "@search.facets": {},
            "value": [{"jobId": str(n) + "-de_DE", "title": "Synthetic public role " + str(n),
                       "company": f.COMPANY, "country": "Germany", "city": "Frankfurt",
                       "custRecLayout3": "Retail", "custRecLayout4": "Aushilfen"} for n in [1001, 1002]]}


def job():
    return {"jobId": "1001-de_DE", "title": "Synthetic public role 1001", "company": f.COMPANY,
            "location": "FRA", "introduction": "<p>Complete introduction.</p>",
            "tasks": "<ul><li>" + "Full native task. " * 20 + "</li></ul>",
            "profile": "<p>" + "Full native qualification. " * 20 + "</p>",
            "custRecBenefits1": "10001", "custRecBenefits2": "10002",
            "custRecBenefits3": None, "custRecBenefits4": None, "custRecBenefits5": None,
            "custRecDetails6": "override@example.test",
            "recruiter": {"name": "Synthetic recruiter", "phone": "public test phone", "email": "other@example.test"},
            "link": "https://example.test/job_application", "quickApplyLink": "https://example.test/quick-apply"}


def benefits():
    return [{"headline": "Full benefit one", "imageURL": "https://images.example.test/one.svg"},
            {"headline": "Full benefit two", "imageURL": None}]


def texts():
    return {"companyText": "<p>Complete corporate context.</p>",
            "recruiter": "<p>Complete public recruiter contact copy.</p>"}


class Transport:
    def __init__(self, *, robots=b"User-agent: *\nAllow: /", failure=None):
        self.calls = []
        self.robots = robots
        self.failure = failure

    def __call__(self, url, *, payload=None, **kwargs):
        self.calls.append((url, copy.deepcopy(payload)))
        if url.endswith("/robots.txt"):
            if self.failure == "robots":
                raise PublicError("source_http_error", http_status=503)
            return {"body": self.robots, "content_type": "text/plain"}
        if self.failure == "content":
            raise f.FarError("far_native_http_error", http_status=403)
        if url.endswith("/api/jobsearch"):
            value = metadata()
        elif url.endswith("/api/jobdetails"):
            value = job()
        elif payload["asset"] == "benefits":
            value = benefits()
        else:
            value = texts()
        return {"body": json.dumps(value).encode(), "content_type": "application/json",
                "requested_at": "2026-10-30T00:00:00Z", "observed_at": "2026-10-30T00:00:01Z"}


class FarRetailTests(unittest.TestCase):
    def test_exact_public_board_and_advertised_detail_uri(self):
        self.assertEqual(f.BOARD, f.checked_url(f.BOARD, "inventory"))
        self.assertEqual("far_retail::1001-de_DE", f.native_id(f.job_uri("1001-de_DE")))

    def test_application_preview_queries_wrong_hosts_and_encoded_routes_refuse(self):
        for uri, operation in [(f.BOARD + "?keyword=PR", "inventory"),
                               (f.BOARD + "?preview=true", "inventory"),
                               (f.job_uri("1001-de_DE") + "?preview=true", "detail"),
                               (f.job_uri("1001-de_DE").replace("/job/", "/apply/"), "detail"),
                               (f.job_uri("1001-de_DE").replace("/job/", "/%6aob/"), "detail"),
                               (f.job_uri("1001-de_DE").replace("retail.de", "retail.de.evil.test"), "detail")]:
            transport = Transport()
            with self.subTest(uri=uri), self.assertRaises(f.FarError):
                f.read(operation, uri, transport=transport)
            self.assertEqual([], transport.calls)

    def test_only_observed_german_native_id_shape(self):
        for native in ["0-de_DE", "../1001", "1001-en_US", 1001, True, "1001-de_DE?apply=1"]:
            with self.subTest(native=native), self.assertRaises(f.FarError):
                f.job_uri(native)

    def test_whole_metadata_array_preserves_native_experience_without_inventing_model(self):
        native = metadata()
        result = f.inventory(native, f.BOARD)
        self.assertEqual((2, 2), (result["returned_count"], result["source_result_count"]))
        self.assertIsNone(result["pagination"]["next_url"])
        self.assertEqual(native["value"][0], result["listings"][0]["native_job_fields"])
        self.assertIsNone(result["listings"][0]["native_model_label"])
        self.assertIsNone(result["listings"][0]["original_source_date"])

    def test_explicit_native_zero_is_distinct_from_missing_supply(self):
        result = f.inventory({"@odata.count": 0, "value": []}, f.BOARD)
        self.assertEqual(0, result["source_result_count"])
        self.assertFalse(result["coverage_complete"])
        for value in [{}, [], {"value": []}, {"@odata.count": 0}]:
            with self.subTest(value=value), self.assertRaises(f.FarError):
                f.inventory(value, f.BOARD)

    def test_native_total_bool_float_partial_and_capped_arrays_are_rejected(self):
        for count in [True, 2.0, -1, 3, 1000001]:
            native = metadata()
            native["@odata.count"] = count
            with self.subTest(count=count), self.assertRaises(f.FarError):
                f.inventory(native, f.BOARD)

    def test_duplicate_ids_company_drift_and_missing_metadata_refuse(self):
        for mutate in [lambda d: d["value"].__setitem__(1, copy.deepcopy(d["value"][0])),
                       lambda d: d["value"][0].__setitem__("company", "Other employer"),
                       lambda d: d["value"][0].__setitem__("title", ""),
                       lambda d: d["value"][0].__setitem__("city", None),
                       lambda d: d["value"][0].__setitem__("jobId", "apply")]:
            data = metadata()
            mutate(data)
            with self.subTest(mutation=mutate), self.assertRaises(f.FarError):
                f.inventory(data, f.BOARD)

    def test_inventory_read_has_fixed_native_wildcard_and_company_only(self):
        transport = Transport()
        result = f.read("inventory", f.BOARD, transport=transport)
        self.assertEqual(2, result["returned_count"])
        self.assertEqual(2, len(transport.calls))
        self.assertEqual({"locale": "de-DE", "searchTerm": "*", "facets": [{"company": [f.COMPANY]}],
                          "operation": "search"}, transport.calls[1][1])
        self.assertEqual("POST", result["native_response_provenance"][0]["method"])

    def test_benefit_csv_and_recruiter_override_follow_actual_native_client(self):
        benefit_args, text_args = f.cms_arguments(job())
        self.assertEqual("JOB-AD-BENEFIT-10001,JOB-AD-BENEFIT-10002", benefit_args["ids"])
        self.assertEqual("override@example.test", text_args["recruiter"]["email"])
        self.assertEqual("FRA", text_args["location"])
        self.assertEqual("texts", text_args["asset"])

    def test_empty_optional_benefit_ids_and_recruiter_follow_native_defaults(self):
        value = job()
        for n in range(1, 6):
            value["custRecBenefits" + str(n)] = None
        value["recruiter"], value["custRecDetails6"] = None, ""
        b, t = f.cms_arguments(value)
        self.assertEqual("", b["ids"])
        self.assertEqual({"name": "", "phone": "", "email": ""}, t["recruiter"])

    def test_untyped_benefit_ids_and_recruiter_fields_refuse(self):
        for key, value in [("custRecBenefits1", 10001), ("custRecBenefits1", "10001,admin"),
                           ("recruiter", "not an object"), ("custRecDetails6", 123),
                           ("location", None)]:
            data = job()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(f.FarError):
                f.cms_arguments(data)

    def test_complete_core_benefits_company_and_recruiter_remain_separate(self):
        core, benefit, company = job(), benefits(), texts()
        result = f.detail(core, benefit, company, f.job_uri(core["jobId"]))
        self.assertEqual(core, result["native_job_fields"])
        self.assertEqual(benefit, result["native_benefits"])
        self.assertEqual(company, result["native_context_raw"])
        self.assertEqual({"introduction", "tasks", "profile"}, set(result["native_primary_sections"]))
        self.assertIn("Full benefit two", result["native_full_public_text"])
        self.assertIn("Complete corporate context.", result["native_full_public_text"])
        self.assertNotIn("Complete corporate context.", result["description"])

    def test_native_read_flags_never_claim_fit_or_visual_completeness(self):
        result = f.detail(job(), benefits(), texts(), f.job_uri("1001-de_DE"))
        self.assertTrue(result["source_body_untruncated"])
        self.assertTrue(result["native_public_cms_sections_requested"])
        self.assertFalse(result["source_scripts_images_or_application_requested"])
        self.assertFalse(result["hydration_credentials_exported_or_used"])
        self.assertFalse(result["full_posting_reviewed"])
        self.assertIsNone(result["original_published_at"])

    def test_detail_fetches_only_nonpreview_core_and_two_cms_reads(self):
        transport = Transport()
        result = f.read("detail", f.job_uri("1001-de_DE"), transport=transport)
        self.assertEqual(4, len(transport.calls))
        self.assertEqual({"jobId": "1001-de_DE", "preview": False}, transport.calls[1][1])
        self.assertEqual(["benefits", "texts"], [x[1]["asset"] for x in transport.calls[2:]])
        self.assertTrue(all(uri.startswith(f.ORIGIN) for uri, _ in transport.calls))
        self.assertEqual(job()["link"], result["application_links_data_only"]["link"])
        self.assertTrue(all(uri != job()["link"] for uri, _ in transport.calls))

    def test_identity_or_primary_section_conflicts_refuse(self):
        for mutate in [lambda x: x.__setitem__("jobId", "1002-de_DE"),
                       lambda x: x.__setitem__("company", "Other company"),
                       lambda x: x.pop("profile"),
                       lambda x: x.__setitem__("tasks", []),
                       lambda x: x.__setitem__("title", "")]:
            core = job()
            mutate(core)
            with self.subTest(mutation=mutate), self.assertRaises(f.FarError):
                f.detail(core, benefits(), texts(), f.job_uri("1001-de_DE"))

    def test_missing_or_untyped_benefits_are_not_partial_body_success(self):
        for value in [None, {}, [{"headline": ""}], [{"headline": "Full", "imageURL": "javascript:bad()"}]]:
            with self.subTest(value=value), self.assertRaises(f.FarError):
                f.detail(job(), value, texts(), f.job_uri("1001-de_DE"))

    def test_missing_company_or_recruiter_copy_refuses(self):
        for value in [None, {}, {"companyText": ""}, {"companyText": "Text", "recruiter": []}]:
            with self.subTest(value=value), self.assertRaises(f.FarError):
                f.detail(job(), benefits(), value, f.job_uri("1001-de_DE"))

    def test_full_long_primary_and_context_are_not_clipped(self):
        core, context = job(), texts()
        core["profile"] = "<p>" + "Complete requirement. " * 20000 + "LAST REQUIREMENT.</p>"
        context["companyText"] = "<p>" + "Complete company context. " * 10000 + "LAST COMPANY.</p>"
        result = f.detail(core, benefits(), context, f.job_uri("1001-de_DE"))
        self.assertTrue(result["description"].endswith("LAST REQUIREMENT."))
        self.assertTrue(result["native_context_sections"]["companyText"]["text"].endswith("LAST COMPANY."))

    def test_scripts_handlers_and_forms_do_not_survive_safe_text(self):
        section = f.public_section('<p onclick="bad()">Visible</p><script>secret()</script><form>Apply</form><p>Full text</p>')
        self.assertEqual("Visible Full text", section["text"])
        self.assertNotIn("bad()", section["html"])
        self.assertNotIn("secret()", section["html"])

    def test_policy_disallow_stops_before_any_job_resource(self):
        transport = Transport(robots=b"User-agent: *\nDisallow: /api/")
        with self.assertRaises(f.FarError):
            f.read("inventory", f.BOARD, transport=transport)
        self.assertEqual(1, len(transport.calls))

    def test_policy_denial_on_cms_prevents_partial_description(self):
        transport = Transport(robots=b"User-agent: *\nDisallow: /api/contentful")
        with self.assertRaises(f.FarError):
            f.read("detail", f.job_uri("1001-de_DE"), transport=transport)
        self.assertEqual(2, len(transport.calls))

    def test_robot_failure_or_actual_content_denial_never_retries(self):
        for failure, expected in [("robots", 1), ("content", 2)]:
            transport = Transport(failure=failure)
            with self.subTest(failure=failure), self.assertRaises(f.FarError):
                f.read("inventory", f.BOARD, transport=transport)
            self.assertEqual(expected, len(transport.calls))

    def test_public_native_response_cannot_export_credentials(self):
        for data in [{"bearerToken": "never"}, {"nested": [{"apiKey": "never"}]}]:
            with self.subTest(data=data), self.assertRaises(f.FarError):
                f.reject_credentials(data)
        f.reject_credentials({"bearerToken": None, "title": "ordinary source data"})

    def test_arbitrary_post_paths_and_operations_are_rejected_before_transport(self):
        transport = Transport()
        with self.assertRaises(f.FarError):
            f.api("/api/apply", {"candidate": "never"}, None, transport)
        with self.assertRaises(f.FarError):
            f.read("apply", f.job_uri("1001-de_DE"), transport=transport)
        self.assertEqual([], transport.calls)


if __name__ == "__main__":
    unittest.main()
