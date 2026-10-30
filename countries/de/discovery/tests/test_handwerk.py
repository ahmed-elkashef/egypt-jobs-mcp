"""Synthetic source/security contracts, with no provider data or network."""

import unittest
from unittest.mock import patch

import handwerk as h
from network import Client, Response, SourceError
from network import checked_url as default_guard


def page(number=1, count=1, final=3, *, duplicate_switch=False, scope="internships"):
    fields = {"search-switchtype": "", "page": str(number), "search-fromsearchform": "1",
              h.SCOPES[scope]: "1", "search-job": "", "search-plz": "12345", "search-radius": "25"}
    inputs = "".join(f'<input name="{key}" value="{value}">' for key, value in fields.items())
    if duplicate_switch:
        inputs += '<input name="search-switchtype" value="">'
    model = "Praktikum" if scope == "internships" else "Lehrstelle"
    rows, bodies = [], []
    for index in range(1, count + 1):
        rows.append(f'<a data-resultid="44_{index}"><p class="list-group-item-heading">Role {index}</p>'
                    f'<p>1 {model} immediately</p></a>')
        bodies.append(f'<div id="detail_44_{index}"><h2>Role {index}</h2><p>Complete native role fields.</p>'
                      f'<a href="https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id={index}"> Details</a>'
                      '<script>DO_NOT_EXPORT_SCRIPT_STATE</script><form>DO_NOT_EXPORT_APPLICATION</form></div>')
    controls = (f'<a data-page="{number - 1}">Back</a>' if number > 1 else "")
    controls += f'<a data-page="{number + 1}">Next</a>' if number < final else ""
    return ('<!DOCTYPE html><html><body><main><h1>Native Radar</h1><form id="resultSearch" method="get">'
            + inputs + '<div id="lsrresultlist">' + "".join(rows) + '</div>'
            + f'Seite {number} von {final}' + controls + '</form>' + "".join(bodies) + '</main></body></html>').encode()


def primary():
    return (b'<html><head><link rel="canonical" href="https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1">'
            b'<meta property="og:url" content="https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1"></head>'
            b'<body><main><h1>Role 1 Praktikum in Vollzeit</h1><p>Complete primary requirement absent from inline fields.</p>'
            b'<h2>Related other jobs</h2><p>Other role, not a requirement.</p><img alt="Company logo" src="never-request.png">'
            b'<script>DO_NOT_EXPORT_SCRIPT_STATE</script><form>DO_NOT_EXPORT_APPLICATION</form></main></body></html>')


class Fake:
    def __init__(self, raw):
        self.raw, self.calls = raw, []

    def get(self, uri):
        self.calls.append(uri)
        return Response(200, self.raw, "text/html; charset=utf-8")


class HandwerkContracts(unittest.TestCase):
    def test_initial_and_continuation_native_requests_keep_the_same_scope(self):
        initial = h.inventory_uri("internships", "12345")
        continued = h.inventory_uri("internships", "12345", 25, 2)
        self.assertIn("search-pr=1", initial)
        self.assertIn("send=Suchen", initial)
        self.assertIn("page=2", continued)
        self.assertNotIn("send=", continued)
        self.assertEqual(h.checked_url(initial), initial)
        self.assertEqual(h.checked_url(continued), continued)

    def test_only_explicit_offer_models_and_typed_geo_arguments_are_accepted(self):
        for args in [("working_student", "12345", 25, 1), ("atlas", "12345", 25, 1),
                     ([], "12345", 25, 1), ("internships", 12345, 25, 1),
                     ("internships", "12345", True, 1), ("internships", "12345", 25, True)]:
            with self.subTest(args=args), self.assertRaises(SourceError):
                h.inventory_uri(*args)

    def test_unknown_role_company_or_duplicate_query_fields_are_refused(self):
        uri = h.inventory_uri("internships", "12345")
        for altered in [uri + "&query=PR", uri + "&search-atlas=1", uri.replace("search-job=", "search-job=PR"),
                        uri + "&search-pr=1", uri.replace("12345", "012345"), h.LIST]:
            with self.subTest(uri=altered), self.assertRaises(SourceError):
                h.checked_url(altered)

    def test_scripts_application_contacts_and_unknown_origins_are_not_routes(self):
        for uri in [h.ORIGIN + "/scripts/5100/5100.js", h.ORIGIN + "/apply", "https://example.invalid/robots.txt",
                    "https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1&apply=true"]:
            with self.subTest(uri=uri), self.assertRaises(SourceError):
                h.checked_url(uri)
        with self.assertRaises(SourceError):
            h.checked_url(h.inventory_uri("internships", "12345"), "POST")

    def test_internal_guard_injection_does_not_expand_the_old_default_transport(self):
        uri = h.inventory_uri("internships", "12345")
        with self.assertRaises(SourceError):
            default_guard(uri)
        client = Client(url_check=h.checked_url)
        with patch.object(client, "_policy") as policy, patch.object(client, "_raw", return_value=Response(200, b"", "text/html")):
            client.get(uri)
            policy.assert_called_once_with(uri)

    def test_actual_native_rows_and_inline_fields_survive_without_primary_or_total_claim(self):
        result = h.parse_inventory(page(count=2), "internships", "12345")
        self.assertEqual(result["returned_count"], 2)
        self.assertIsNone(result["source_result_count"])
        self.assertFalse(result["exact_native_total_verified"])
        self.assertFalse(result["native_fixed_page_size_verified"])
        self.assertTrue(result["metadata"][0]["inline_fields_are_not_verified_complete_primary"])
        self.assertFalse(result["full_posting_reviewed"])
        self.assertIsNone(result["original_published_at"])

    def test_variable_row_counts_do_not_become_an_assumed_page_size(self):
        for number, count in [(1, 1), (2, 2), (3, 3)]:
            result = h.parse_inventory(page(number, count), "internships", "12345", page=number)
            self.assertEqual(result["returned_count"], count)
            self.assertIsNone(result["source_result_count"])

    def test_exact_native_continuation_carries_the_initial_page_ceiling(self):
        result = h.parse_inventory(page(), "internships", "12345")
        args = result["next_request"]["arguments"]
        self.assertEqual(args["first_native_pages"], 3)
        self.assertEqual(args["page"], 2)
        self.assertEqual(args["postal_code"], "12345")
        with self.assertRaisesRegex(SourceError, "ceiling changed"):
            h.parse_inventory(page(2), "internships", "12345", page=2, first_native_pages=4)

    def test_known_identical_duplicate_switch_input_is_preserved(self):
        result = h.parse_inventory(page(2, duplicate_switch=True), "internships", "12345", page=2)
        switches = [x for x in result["native_form_field_occurrences"] if x["name"] == "search-switchtype"]
        self.assertEqual(len(switches), 2)
        self.assertTrue(all(x["value"] == "" for x in switches))

    def test_conflicting_duplicate_switch_and_other_duplicate_filters_fail(self):
        for altered in [page(2, duplicate_switch=True).replace(b'name="search-switchtype" value=""',
                                                             b'name="search-switchtype" value="2"', 1),
                        page().replace(b'</form>', b'<input name="search-pr" value="1"></form>')]:
            with self.assertRaises(SourceError):
                h.parse_inventory(altered, "internships", "12345", page=2 if b'Seite 2' in altered else 1)

    def test_truncated_document_and_missing_native_pagination_or_scope_fail(self):
        for raw in [page()[:-7], page().replace(b'Seite 1 von 3', b'Unknown'),
                    page().replace(b'value="12345"', b'value="54321"'),
                    page().replace(b'data-page="2"', b'data-page="3"')]:
            with self.assertRaises(SourceError):
                h.parse_inventory(raw, "internships", "12345")

    def test_duplicate_or_unmatched_native_record_identity_fails(self):
        for raw in [page(count=2).replace(b'44_2', b'44_1'), page().replace(b'id="detail_44_1"', b'id="detail_44_2"')]:
            with self.assertRaises(SourceError):
                h.parse_inventory(raw, "internships", "12345")

    def test_inline_script_forms_media_and_attributes_are_never_exported(self):
        result = h.parse_inventory(page(), "internships", "12345")
        body = result["metadata"][0]["native_inline_html"]
        self.assertNotIn("DO_NOT_EXPORT", body)
        self.assertNotIn("<form", body)
        self.assertNotIn("href=", body)

    def test_unqualified_external_primary_is_retained_without_following(self):
        raw = page().replace(b'https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1',
                             b'https://example.invalid/redirect?c=native-public-offer-id')
        result = h.parse_inventory(raw, "internships", "12345")
        self.assertFalse(result["metadata"][0]["standalone_primary_route_qualified"])
        self.assertIn("example.invalid", result["metadata"][0]["native_primary_reference"])

    def test_use_acknowledgement_and_continuation_ceiling_refuse_before_network(self):
        client = Fake(page())
        with self.assertRaises(SourceError):
            h.inventory("internships", "12345", client=client)
        with self.assertRaises(SourceError):
            h.inventory("internships", "12345", page=2, personal_noncommercial_use=True, client=client)
        self.assertEqual(client.calls, [])

    def test_noncommercial_complete_native_read_has_no_other_request(self):
        client = Fake(page())
        result = h.inventory("internships", "12345", personal_noncommercial_use=True, client=client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result["returned_count"], 1)

    def test_standalone_primary_retains_extra_header_and_separate_context_warning(self):
        result = h.parse_detail(primary(), "https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1")
        self.assertIn("Vollzeit", result["native_header_text"])
        self.assertIn("absent from inline", result["description"])
        self.assertTrue(result["related_job_and_firm_context_is_not_this_roles_requirements"])
        self.assertNotIn("DO_NOT_EXPORT", result["description_html"])
        self.assertFalse(result["nontext_media_requirements_verified"])
        self.assertFalse(result["full_posting_reviewed"])

    def test_primary_origin_model_or_full_document_must_be_qualified(self):
        with self.assertRaises(SourceError):
            h.detail("https://example.invalid/job/1", personal_noncommercial_use=True, client=Fake(primary()))
        for raw in [primary()[:-7], primary().replace(b'Praktikum', b'Role'), primary().replace(b'<main>', b'<article>')]:
            with self.assertRaises(SourceError):
                h.parse_detail(raw, "https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1")

    def test_genuine_native_empty_scope_is_retained_without_zero_country_claim(self):
        raw = page(count=0, final=1).replace(b'Seite 1 von 1', b'Leider ergab die Suche keine Treffer.')
        result = h.parse_inventory(raw, "internships", "12345")
        self.assertEqual(result["returned_count"], 0)
        self.assertTrue(result["native_empty_scoped_result"])
        self.assertIsNone(result["source_result_count"])
        self.assertIsNone(result["native_pages"])
        self.assertFalse(result["coverage_complete"])

    def test_generic_or_changed_empty_result_cannot_replace_a_native_scope(self):
        for raw in [page(count=0), page(count=0, final=1).replace(b'Seite 1 von 1', b'Login required'),
                    page(count=0, final=1).replace(b'Seite 1 von 1', b'<script>Leider ergab die Suche keine Treffer.</script>')]:
            with self.assertRaises(SourceError):
                h.parse_inventory(raw, "internships", "12345")

    def test_primary_canonical_ID_must_match_its_independent_native_reference(self):
        raw = primary().replace(b'id=1', b'id=2', 1)
        with self.assertRaisesRegex(SourceError, "canonical/OpenGraph"):
            h.parse_detail(raw, "https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1")

    def test_primary_open_graph_uri_cannot_be_missing_or_point_to_another_offer(self):
        for raw in [primary().replace(b'property="og:url"', b'property="other"'),
                    primary().replace(b'content="https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1"',
                                      b'content="https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=2"')]:
            with self.assertRaisesRegex(SourceError, "canonical/OpenGraph"):
                h.parse_detail(raw, "https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1")


if __name__ == "__main__":
    unittest.main()
