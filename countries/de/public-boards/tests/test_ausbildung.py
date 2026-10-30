"""Synthetic original native protocol tests; no real applicant or website program fixtures."""
import copy
import json
import sys
from pathlib import Path
from unittest import TestCase

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ausbildung as a
from native_flight import FlightError, records_from_stream


def row(number=1):
    identity = f"00000000-0000-4000-8000-{number:012d}"
    return {"vacancyPublicId": identity, "jobPostingPublicId": "11111111-1111-4111-8111-111111111111",
            "slug": "synthetic-internship-" + identity, "title": "University internship", "cityName": "Leipzig",
            "internshipKinds": ["Freiwilliges Praktikum"], "vacancyCount": 3, "relatedBranchesCount": 2,
            "educationDirections": [], "durationMin": 6, "durationMax": 6}


def page(total=41, numbers=range(1, 21)):
    return {"hits": {"primary": [row(n) for n in numbers], "extended": []},
            "meta": {"resultsCount": total, "vacanciesCount": total * 3, "countryEntryCode": "DE",
                     "countryEntryPoint": "Germany", "cityName": "Frankfurt am Main", "sessionLocation": False}}


def document(data=None, **overrides):
    props = {"searchType": "student", "searchResults": page() if data is None else data,
             "searchParams": {}, "countryEntryCode": "DE", "initialState": {"what": None, "where": None, "radius": None},
             "favoriteVacancyPublicIds": [], "jobletterSubscribed": False, **overrides}
    stream = "1:" + json.dumps([["$", "$L99", None, props]]) + "\n"
    literal = json.dumps([1, stream]).replace("<", r"\u003c")
    return ('<html><script src="' + a.REFERENCE_ASSET + '"></script><script>self.__next_f.push('
            + literal + ");</script></html>").encode()


def action(data=None, status="200"):
    return ('0:{"a":"$@1","q":"","i":false,"b":"synthetic"}\n1:'
            + json.dumps({"data": page() if data is None else data, "meta": {"message": "OK"}, "statusCode": status})
            + "\n").encode()


def binding():
    return a.parse_inventory(page())["native_binding"]


def advert(schema='{"@type":"JobPosting","description":"Published university placement"}'):
    url = a.CATALOGUE + row()["slug"] + "/"
    body = ('<html><head><link rel="canonical" href="' + url + '"><script type="application/ld+json">'
            + schema + '</script></head><main><h1>University internship</h1><h2>Das Praktikum auf einen Blick</h2>'
            '<p>Currently enrolled university student required.</p><h2>Die Aufgaben im Praktikum</h2>'
            '<p>Six months, communications. Very good German and English.</p><h2>So läuft die Bewerbung ab</h2>'
            '<form><label>CV required</label></form>'
            '<a href="https://employer.invalid/offer/synthetic">Apply</a><img src="/synthetic.png" alt="Unreviewed visual">'
            '<script>must_not_execute()</script></main></html>').encode()
    return url, body


class AusbildungTests(TestCase):
    def test_initial_whole_native_view_preserves_all_rows_and_both_counters(self):
        data = page()
        value = a.parse_inventory(a.initial_data(document(data)))
        self.assertEqual(value["returned_count"], 20)
        self.assertEqual((value["source_result_count"], value["source_vacancy_place_count"]), (41, 123))
        self.assertEqual([r["native_metadata"] for r in value["records"]], data["hits"]["primary"])
        self.assertEqual(value["native_search_parameters"], {})
        self.assertFalse(value["coverage_complete"])
        self.assertFalse(value["portal_school_section_is_school_only_model_proof"])

    def test_native_from_twenty_uses_qualified_action_and_acquired_binding(self):
        value = a.parse_inventory(a.continuation_data(action(page(numbers=range(21, 41)))), offset=20, binding=binding())
        self.assertEqual(value["returned_count"], 20)
        self.assertEqual(value["next_request"]["arguments"]["from"], 40)
        self.assertEqual(value["native_search_parameters"], {"from": 20})

    def test_terminal_short_view_is_not_whole_source_or_week_coverage(self):
        value = a.parse_inventory(page(numbers=[41]), offset=40, binding=binding())
        self.assertTrue(value["native_terminal_page"])
        self.assertIsNone(value["next_request"])
        self.assertFalse(value["coverage_complete"])
        self.assertFalse(value["original_publication_clock_verified"])

    def test_genuine_empty_native_catalogue_is_separate_from_failure(self):
        value = a.parse_inventory(page(total=0, numbers=[]))
        self.assertEqual(value["returned_count"], 0)
        self.assertTrue(value["native_terminal_page"])
        self.assertFalse(value["coverage_complete"])

    def test_either_native_counter_drift_refuses_instead_of_resetting(self):
        for field in ("resultsCount", "vacanciesCount"):
            data = page(numbers=range(21, 41))
            data["meta"][field] += 1
            with self.subTest(field=field), self.assertRaisesRegex(a.SourceError, "drift"):
                a.parse_inventory(data, offset=20, binding=binding())

    def test_short_oversized_and_duplicate_views_are_not_silently_clipped(self):
        for numbers in (range(1, 20), range(1, 22), [1] * 20):
            with self.subTest(numbers=numbers), self.assertRaises(a.SourceError):
                a.parse_inventory(page(numbers=numbers))

    def test_counts_require_bounded_native_integers(self):
        for field in ("resultsCount", "vacanciesCount"):
            for bad in (True, None, -1, 1.5, 10000001):
                data = page()
                data["meta"][field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(a.SourceError):
                    a.parse_inventory(data)

    def test_native_identity_is_vacancy_uuid_and_slug_not_parent_posting_id(self):
        data = page()
        value = a.parse_inventory(data)
        self.assertNotEqual(value["records"][0]["native_vacancy_id"], value["records"][0]["native_job_posting_id"])
        data["hits"]["primary"][0]["vacancyPublicId"] = row(99)["vacancyPublicId"]
        with self.assertRaisesRegex(a.SourceError, "identity_disagree"):
            a.parse_inventory(data)

    def test_extended_recommendations_are_not_mixed_into_unfiltered_primary(self):
        data = page()
        data["hits"]["extended"] = [row(99)]
        with self.assertRaisesRegex(a.SourceError, "extended"):
            a.parse_inventory(data)

    def test_source_default_city_does_not_become_a_personal_geo_filter(self):
        value = a.parse_inventory(page())
        self.assertEqual(value["native_search_meta"]["cityName"], "Frankfurt am Main")
        self.assertEqual(value["records"][0]["location_raw"], "Leipzig")
        self.assertFalse(value["role_model_or_geography_filters_applied"])
        self.assertFalse(value["source_country_is_job_worksite_proof"])

    def test_unqualified_country_session_and_internship_metadata_refuse(self):
        for mutate in [lambda d: d["meta"].update(countryEntryCode="AT"),
                       lambda d: d["meta"].update(sessionLocation=True),
                       lambda d: d["hits"]["primary"][0].update(internshipKinds="Mandatory")]:
            data = page()
            mutate(data)
            with self.assertRaises(a.SourceError):
                a.parse_inventory(data)

    def test_active_career_geo_and_other_filters_cannot_restrict_initial_supply(self):
        for override in ({"searchParams": {"what": "marketing"}}, {"initialState": {"where": "Frankfurt"}},
                         {"initialState": {"duration": ["six_months"]}}, {"countryEntryCode": "AT"}):
            with self.subTest(override=override), self.assertRaises(a.SourceError):
                a.initial_data(document(**override))

    def test_personalized_account_state_is_never_returned(self):
        for override in ({"favoriteVacancyPublicIds": ["private"]}, {"jobletterSubscribed": True}):
            with self.subTest(override=override), self.assertRaisesRegex(a.SourceError, "personalized"):
                a.initial_data(document(**override))

    def test_protocol_deployment_change_requires_qualification_no_script_fetch(self):
        raw = document().replace(a.REFERENCE_ASSET.encode(), b"/different-build.js")
        with self.assertRaisesRegex(a.SourceError, "deployment_changed"):
            a.initial_data(raw)

    def test_native_action_uses_actual_string_status_and_failure_is_not_zero_supply(self):
        for bad in (200, 200.0, True, None, "403", "500"):
            with self.subTest(bad=bad), self.assertRaises(a.SourceError):
                a.continuation_data(action(status=bad))
        self.assertEqual(a.continuation_data(action()), page())

    def test_malformed_action_envelope_is_not_a_result_collection(self):
        for raw in (b'0:{"a":"$@2"}\n1:{}\n', b'0:{"a":"$@1"}\n1:{"data":{}}\n'):
            with self.assertRaises(a.SourceError):
                a.continuation_data(raw)

    def test_resume_input_rejects_null_coercion_wrong_revision_and_arbitrary_operation(self):
        bad_bindings = [None, {}, {**binding(), "protocol_sha256": "0" * 64},
                        {**binding(), "resultsCount": True}, {**binding(), "query": "marketing"}]
        for bad in bad_bindings:
            with self.subTest(bad=bad), self.assertRaises(a.SourceError):
                a.check_request(20, bad)
        for offset in (None, True, -20, 1, 20.5, 60):
            with self.subTest(offset=offset), self.assertRaises(a.SourceError):
                a.check_request(offset, binding())
        with self.assertRaises(a.SourceError):
            a.check_request(0, binding())

    def test_bad_read_input_and_action_cannot_request_any_provider(self):
        class NoCalls:
            def __getattr__(self, name):
                raise AssertionError("provider was invoked: " + name)
        for kwargs in ({"offset": 1}, {"offset": 20}, {"offset": 0, "binding": binding()}):
            with self.subTest(kwargs=kwargs), self.assertRaises(a.SourceError):
                a.read("inventory", client=NoCalls(), **kwargs)
        with self.assertRaises(a.SourceError):
            a.read("apply", client=NoCalls())

    def test_complete_portal_body_preserves_form_requirements_without_actions(self):
        url, raw = advert()
        value = a.parse_detail(raw, url=url)
        self.assertIn("Currently enrolled", value["full_description"])
        self.assertIn("CV required", value["full_description"])
        self.assertNotIn("must_not_execute", value["full_description"])
        self.assertEqual(value["native_links"][0]["url"], "https://employer.invalid/offer/synthetic")
        self.assertEqual(len(value["native_media"]), 1)
        self.assertTrue(value["full_description_acquired"])
        self.assertFalse(value["employer_original_status_verified"])
        self.assertFalse(value["full_posting_reviewed"])
        self.assertEqual(" ".join("".join(value["native_main_text_nodes"]).split()), " ".join(value["full_description"].split()))
        self.assertIn("Die Aufgaben im Praktikum", value["native_section_headings"])
        self.assertFalse(value["portal_education_direction_pay_is_role_salary_proof"])
        self.assertFalse(value["portal_school_class_is_university_eligibility_proof"])

    def test_malformed_published_schema_retains_body_and_raw_diagnostic_without_repair(self):
        url, raw = advert('{"duplicate":1,"duplicate":2}')
        value = a.parse_detail(raw, url=url)
        self.assertTrue(value["full_description_acquired"])
        self.assertEqual(value["published_structured_data"], [])
        self.assertEqual(value["published_structured_data_raw"], ['{"duplicate":1,"duplicate":2}'])
        self.assertEqual(value["published_structured_data_parse_errors"][0]["error"], "invalid_native_json")

    def test_bad_canonical_header_and_utf8_refuse_complete_primary_claim(self):
        url, raw = advert()
        for bad in (raw.replace(url.encode(), b"https://other.invalid/"), raw.replace(b"h1", b"h3"), raw + b"\xff"):
            with self.assertRaises(ValueError):
                a.parse_detail(bad, url=url)

    def test_challenge_or_generic_page_is_not_promoted_to_a_complete_advert(self):
        url, raw = advert()
        with self.assertRaisesRegex(a.SourceError, "sections_missing"):
            a.parse_detail(raw.replace(b"Die Aufgaben im Praktikum", b"Security challenge"), url=url)

    def test_exact_advert_routes_reject_applications_queries_fragments_and_host_aliases(self):
        url, _ = advert()
        for bad in (url + "bewerben/", url + "?from=20", url + "#apply", url + "\n", url.replace(".de/", ".de.evil.invalid/")):
            with self.subTest(bad=bad), self.assertRaises(a.SourceError):
                a.advert_id(bad)

    def test_every_client_route_method_and_noninitial_read_is_guarded_before_policy(self):
        client = a.Client(transport=lambda *args, **kwargs: self.fail("provider called"))
        for url, method in ((a.CATALOGUE, "DELETE"), (a.ORIGIN + "/bewerben/", "POST"), ("https://evil.invalid/", "GET")):
            with self.subTest(url=url, method=method), self.assertRaises(a.SourceError):
                client.guard(url, method)
        for offset in (0, -20, True, 1):
            with self.assertRaises(a.SourceError):
                client.search(offset)
        self.assertEqual(sum(client.request_attempts.values()), 0)

    def test_native_json_duplicate_nonfinite_trailing_and_utf8_corruption_are_not_silently_lost(self):
        for raw in (b'1:{"hits":1,"hits":2}\n', b'1:{"number":NaN}\n',
                    b'1:{"number":1e999}\n', b'1:{"ok":true}trailing\n', b'1:{"text":"\xff"}\n'):
            with self.subTest(raw=raw), self.assertRaises((FlightError, UnicodeError)):
                records_from_stream(raw)

    def test_invalid_native_mutation_leaves_input_evidence_intact(self):
        data = page()
        original = copy.deepcopy(data)
        a.parse_inventory(data)
        self.assertEqual(data, original)

    def test_robots_denial_and_pacing_stop_before_data_read(self):
        for text in ("User-agent: *\nDisallow: /schuelerpraktikum/\n",
                     "User-agent: *\nDisallow: /schuelerpraktikum/*\n",
                     "User-agent: *\nAllow: /\nCrawl-delay: 1\n"):
            calls = []
            def transport(url, **kwargs):
                calls.append(url)
                return {"body": text.encode()}
            client = a.Client(transport=transport)
            with self.subTest(policy=text), self.assertRaises(a.SourceError):
                a.read("inventory", client=client)
            self.assertEqual(calls, [a.ORIGIN + "/robots.txt"])
            self.assertEqual(client.request_attempts["catalogue_GET"], 0)

    def test_unavailable_policy_never_reads_or_zeroes_the_catalogue(self):
        calls = []
        def transport(url, **kwargs):
            calls.append(url)
            raise a.SourceError("source_http_error", http_status=403)
        client = a.Client(transport=transport)
        with self.assertRaises(a.SourceError):
            a.read("inventory", client=client)
        self.assertEqual(calls, [a.ORIGIN + "/robots.txt"])
        self.assertEqual(client.request_attempts["catalogue_GET"], 0)

    def test_actual_native_search_transport_has_only_fixed_anonymous_read_parameters(self):
        calls = []
        class Response:
            status = 200
            headers = {"Content-Type": "text/x-component;charset=utf-8"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, bound):
                return action(page(numbers=range(21, 41)))
        class Opener:
            def open(self, req, **kwargs):
                calls.append(req)
                return Response()
        client = a.Client(transport=lambda *args, **kwargs: {"body": b"User-agent: *\nAllow: /\n"}, opener=Opener())
        value = a.read("inventory", offset=20, binding=binding(), client=client)
        self.assertEqual(len(calls), 1)
        req = calls[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, a.CATALOGUE)
        self.assertEqual(json.loads(req.data), [{"from": 20}])
        headers = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(headers["next-action"], a.SEARCH_REFERENCE)
        self.assertEqual(headers["user-agent"], a.AGENT)
        self.assertNotIn("cookie", headers)
        self.assertNotIn("authorization", headers)
        self.assertEqual(value["returned_count"], 20)
        self.assertEqual(client.request_attempts, {"policy_GET": 1, "catalogue_GET": 0, "search_read_POST": 1, "detail_GET": 0})

    def test_http_failure_redirect_and_throttle_stop_without_retry(self):
        for status in (302, 403, 429, 503):
            calls = []
            class Opener:
                def open(self, req, **kwargs):
                    calls.append(req)
                    raise a.HTTPError(req.full_url, status, "native stop", {"Retry-After": "60"}, None)
            client = a.Client(transport=lambda *args, **kwargs: {"body": b"User-agent: *\nAllow: /\n"}, opener=Opener())
            with self.subTest(status=status), self.assertRaises(a.SourceError) as caught:
                a.read("inventory", offset=20, binding=binding(), client=client)
            self.assertEqual(caught.exception.http_status, status)
            self.assertEqual(caught.exception.retry_after, "60")
            self.assertEqual(len(calls), 1)

    def test_html_challenge_instead_of_flight_is_rejected_before_parsing(self):
        class Response:
            status = 200
            headers = {"Content-Type": "text/html"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, bound):
                return b"<html>Security challenge</html>"
        class Opener:
            def open(self, req, **kwargs):
                return Response()
        client = a.Client(transport=lambda *args, **kwargs: {"body": b"User-agent: *\nAllow: /\n"}, opener=Opener())
        with self.assertRaisesRegex(a.SourceError, "content_type"):
            a.read("inventory", offset=20, binding=binding(), client=client)
