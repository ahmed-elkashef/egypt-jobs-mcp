"""Synthetic semantic/security regressions; no real source data, tokens or HTTP."""

import csv
import io
import json
import unittest
from unittest.mock import patch

from lxml import html

import meinpraktikum as market
import organisations as org
from network import (
    GVP_FILTER,
    GVP_PAGE,
    HRK_DOWNLOAD,
    HRK_PAGE,
    MEIN,
    MEIN_SEARCH,
    Client,
    Response,
    SourceError,
    checked_url,
)


def identifier(number):
    return f"00000000-0000-4000-8000-{number:012d}"


def vacancy(number, city="Frankfurt am Main"):
    return {"id": identifier(number), "slug": "student-role-2023-" + identifier(number), "city": city, "amount": 1}


def search(total=11, page=1):
    rows = []
    for number in range((page - 1) * 10 + 1, min(page * 10, total) + 1):
        rows.append({"_source": {
            "id": identifier(number), "title": "Working Student 2027", "companyDisplayName": "Example employer",
            "createdAt": "2023-01-01T00:00:00Z", "updatedAt": "2026-10-01T00:00:00Z",
            "description": "Complete native role fields", "internship_type_value": "internship",
            "vacancies": [vacancy(number + 1000), vacancy(number + 2000, "Berlin")],
            "vacancies_country": ["Deutschland", "Deutschland"], "vacancies_state": ["Hessen", "Berlin"],
        }})
    return {"statusCode": 200, "body": {"hits": {"total": {"value": total, "relation": "eq"}, "hits": rows}}}


def advert():
    child = vacancy(101)
    title = "Working Student 2027"
    job = {
        "id": identifier(1), "name": title, "description": "Full role paragraph after comment",
        "vacancies": [child, vacancy(102, "Berlin")], "created_at": "2023-01-01", "updated_at": "2026-10-01",
        "education_condition": {"internship_type": "internship"},
        "portal": {"customer": {"name": "Example", "access_token": "DO_NOT_EXPORT_NESTED_TOKEN"}},
    }
    state = {"page": "/stellen/[vacancySlug]", "props": {"pageProps": {
        "result": {"vacancyId": child["id"], "vacancySlug": child["slug"], "jobPosting": job},
        "user": {"access_token": "DO_NOT_EXPORT_USER_TOKEN"},
    }}}
    markup = f'''<html><body><header>Not the advert</header><div class="sc-fa19c2e8-1 layout">
    <h1>{title}</h1><p onclick="private()">Full role<!-- omitted --> paragraph after comment</p>
    <img src="https://example.invalid/logo.png" alt="Example logo"><script>DO_NOT_EXPORT_SCRIPT</script>
    <form><input value="DO_NOT_EXPORT_FORM"></form><a id="t-link-online-application" href="/apply">Apply</a>
    <button>Save</button></div><footer class="sc-fa19c2e8-1">Unrelated footer</footer>
    <script id="__NEXT_DATA__" type="application/json">{json.dumps(state)}</script>
    <script type="application/ld+json">{json.dumps({"@type": "JobPosting", "title": title, "datePosted": "2023-01-01"})}</script>
    </body></html>'''
    return markup.encode(), MEIN + "/stellen/" + child["slug"], state


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url):
        self.calls.append(("GET", url))
        return self.responses.pop(0)

    def post(self, url, body, content_type="application/json", public_nonce=None):
        self.calls.append(("POST", url, body, content_type, public_nonce))
        return self.responses.pop(0)


class MarketTests(unittest.TestCase):
    def test_all_location_children_survive_group_metadata(self):
        result = market.parse_inventory(search(), "internships", 1)
        first = result["metadata"][0]
        self.assertEqual(len(first["native_location_vacancies"]), 2)
        self.assertIn("Hessen", first["source_data"]["vacancies_state"])
        self.assertNotEqual(first["native_job_group_id"], first["native_location_vacancies"][0]["native_record"]["id"])
        self.assertIn("2023", first["native_location_vacancies"][0]["url"])
        self.assertIn("2027", first["title"])
        self.assertIsNone(first["original_published_at"])
        self.assertTrue(first["native_type_requires_full_role_reconciliation"])
        self.assertFalse(first["full_posting_reviewed"])

    def test_first_next_and_final_page_semantics(self):
        for page, count, more in [(1, 10, True), (2, 10, True), (3, 1, False)]:
            with self.subTest(page=page):
                result = market.parse_inventory(search(21, page), "working_student", page)
                self.assertEqual(result["returned_count"], count)
                self.assertEqual(result["has_more"], more)
                self.assertEqual(result["next_page"], page + 1 if more else None)
                self.assertFalse(result["coverage_complete"])

    def test_empty_native_scope_is_distinct_from_missing_rows(self):
        result = market.parse_inventory(search(0), "internships", 1)
        self.assertEqual(result["returned_count"], 0)
        self.assertFalse(result["has_more"])
        bad = search()
        bad["body"]["hits"]["hits"].pop()
        with self.assertRaises(SourceError):
            market.parse_inventory(bad, "internships", 1)

    def test_unqualified_total_relation_never_becomes_exact(self):
        native = search()
        native["body"]["hits"]["total"]["relation"] = "gte"
        with self.assertRaises(SourceError):
            market.parse_inventory(native, "internships", 1)

    def test_out_of_range_is_not_market_empty(self):
        with self.assertRaises(SourceError):
            market.parse_inventory(search(11, 3), "internships", 3)

    def test_HTTP201_read_success_and_whole_native_filters(self):
        client = FakeClient([Response(201, json.dumps(search()).encode())])
        result = market.inventory("internships", personal_noncommercial_use=True, client=client)
        self.assertEqual(result["native_HTTP_status"], 201)
        payload = json.loads(client.calls[0][2])
        self.assertEqual(payload["portal_type"], "mp")
        self.assertEqual(payload["what"], "")
        self.assertEqual(payload["sectors"], [])
        self.assertIsNone(payload["lat"])
        self.assertIn("Schülerpraktikum", payload["internship_types"])
        self.assertFalse(result["role_interest_query_filters"])

    def test_personal_use_guard_precedes_any_request(self):
        for value in [False, None, "true", 1]:
            client = FakeClient([])
            with self.subTest(value=value), self.assertRaises(SourceError):
                market.inventory("internships", personal_noncommercial_use=value, client=client)
            self.assertEqual(client.calls, [])

    def test_cross_source_and_application_URLs_refuse_before_HTTP(self):
        _, url, _ = advert()
        for bad in [GVP_PAGE, url + "/apply", url + "?apply=1", url.replace("https:", "http:"),
                    url.replace("www.meinpraktikum.de", "www.meinpraktikum.de.evil.invalid"),
                    url.replace("www.meinpraktikum.de", "u:p@www.meinpraktikum.de"),
                    url.replace("/stellen/", "/stellen/%2F"), url.replace("/stellen/", "/stellen/%0A"), url + "#form"]:
            client = FakeClient([])
            with self.subTest(url=bad), self.assertRaises(SourceError):
                market.detail(bad, personal_noncommercial_use=True, client=client)
            self.assertEqual(client.calls, [])

    def test_complete_advert_and_identity_without_state_or_controls(self):
        raw, url, _ = advert()
        result = market.parse_detail(raw, url)
        self.assertIn("paragraph after comment", result["source_primary_text"])
        self.assertIn("Full role", result["native_role_markdown"])
        self.assertNotEqual(result["native_job_group_id"], result["native_selected_vacancy_id"])
        encoded = json.dumps(result)
        for absent in ["DO_NOT_EXPORT", "onclick", "<script", "<form", "Unrelated footer", ">Apply<"]:
            self.assertNotIn(absent, encoded)
        self.assertEqual(result["native_nontext_media_count"], 1)
        self.assertFalse(result["nontext_media_requirements_verified"])
        self.assertFalse(result["full_posting_reviewed"])
        self.assertIsNone(result["original_published_at"])

    def test_primary_boundary_change_has_no_whole_page_fallback(self):
        raw, url, _ = advert()
        with self.assertRaises(SourceError):
            market.parse_detail(raw.replace(b"sc-fa19c2e8-1", b"new-template"), url)

    def test_visible_title_conflict_refuses(self):
        raw, url, _ = advert()
        with self.assertRaises(SourceError):
            market.parse_detail(raw.replace(b"<h1>Working Student 2027", b"<h1>Different role"), url)

    def test_selected_vacancy_group_membership_required(self):
        raw, url, state = advert()
        tree = html.fromstring(raw)
        state["props"]["pageProps"]["result"]["jobPosting"]["vacancies"] = [vacancy(999)]
        tree.xpath('//script[@id="__NEXT_DATA__"]')[0].text = json.dumps(state)
        with self.assertRaises(SourceError):
            market.parse_detail(html.tostring(tree), url)

    def test_bad_location_slug_is_retained_as_an_issue_not_dropped(self):
        native = search()
        native["body"]["hits"]["hits"][0]["_source"]["vacancies"][0]["slug"] = "wrong-id"
        result = market.parse_inventory(native, "internships", 1)
        locations = result["metadata"][0]["native_location_vacancies"]
        self.assertEqual(len(locations), 2)
        self.assertIsNone(locations[0]["url"])
        self.assertTrue(locations[0]["native_route_issue"])


def staff(total=11, page=1):
    cards = []
    for number in range((page - 1) * 10 + 1, min(page * 10, total) + 1):
        cards.append(f'<div class="accordion__entry memberlist__entry" data-company-id="{number}"><h4>Example {number} - City (12345)</h4></div>')
    return json.dumps(json.dumps({"data": "".join(cards), "total_count": total, "current_count": len(cards)})).encode()


def university_tsv():
    fields = org.COLUMNS + ["Extra field " + str(i) for i in range(14)]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t")
    writer.writeheader()
    for number, state in [(1, "Hessen"), (2, "Berlin")]:
        row = {field: "" for field in fields}
        row.update({"Hs-Nr.": str(number), "Hochschulname": f"Öffentliche Hochschule {number}",
                    "Bundesland": state, "Home Page": "www.example.invalid", "Extra field 1": "Unprojected contact"})
        writer.writerow(row)
    return output.getvalue().encode("cp1252")


class OrganisationTests(unittest.TestCase):
    def test_university_file_preserves_main_state_and_unverified_homepage(self):
        result = org.parse_higher_education(university_tsv())
        self.assertEqual(result["returned_count"], 2)
        self.assertEqual(result["Hessen_main_address_rows"], 1)
        self.assertEqual(result["organisations"][0]["native_organisation_fields"]["Home Page"], "www.example.invalid")
        self.assertNotIn("Unprojected contact", json.dumps(result))
        self.assertFalse(result["coverage_complete"])
        self.assertFalse(result["public_dataset_redistribution_permitted"])
        self.assertTrue(result["personal_use_only"])

    def test_university_duplicate_ids_refuse(self):
        raw = university_tsv().replace(b"\r\n2\t", b"\r\n1\t", 1)
        with self.assertRaises(SourceError):
            org.parse_higher_education(raw)

    def test_changed_university_header_refuses(self):
        with self.assertRaises(SourceError):
            org.parse_higher_education(b"name\turl\nExample\thttps://example.invalid")

    def test_university_source_download_and_terms_must_remain_advertised(self):
        client = FakeClient([Response(200, b"<html>Changed page</html>")])
        with self.assertRaises(SourceError):
            org.higher_education(personal_noncommercial_use=True, client=client)
        self.assertEqual(client.calls, [("GET", HRK_PAGE)])

    def test_university_known_download_with_personal_use_scope(self):
        page = ('<html>ausschließlich für den persönlichen Gebrauch kostenfrei<a href="' + HRK_DOWNLOAD + '">TXT</a></html>').encode()
        client = FakeClient([Response(200, page), Response(200, university_tsv())])
        result = org.higher_education(personal_noncommercial_use=True, client=client)
        self.assertEqual(result["returned_count"], 2)
        self.assertEqual(client.calls, [("GET", HRK_PAGE), ("GET", HRK_DOWNLOAD)])

    def test_file_pagination_and_unknown_directory_refuse_before_HTTP(self):
        for name, page in [("higher_education", 2), ("unknown", 1), ("staffing_members", True)]:
            client = FakeClient([])
            with self.subTest(name=name), self.assertRaises(SourceError):
                org.directory(name, page, personal_noncommercial_use=True, client=client)
            self.assertEqual(client.calls, [])

    def test_native_double_encoded_GVP_pagination_counts(self):
        for page, count, more in [(1, 10, True), (2, 1, False)]:
            result = org.parse_staffing(staff(11, page), page)
            self.assertEqual(result["returned_count"], count)
            self.assertEqual(result["has_more"], more)
            self.assertTrue(all(row["homepage_url"] is None for row in result["organisations"]))
            self.assertFalse(result["protected_detail_or_challenge_endpoints_requested_or_solved"])
            self.assertFalse(result["coverage_complete"])

    def test_GVP_metadata_nonce_is_in_memory_only_and_no_detail_challenge(self):
        nonce = "ExampleNonce12"
        page = ('<script>const gvp_config = {rest_url: "https://personaldienstleister.de/wp-json/", nonce: "' + nonce + '"}</script>').encode()
        client = FakeClient([Response(200, page), Response(200, staff())])
        result = org.staffing(personal_noncommercial_use=True, client=client)
        self.assertEqual(client.calls[0], ("GET", GVP_PAGE))
        self.assertEqual(client.calls[1][1], GVP_FILTER)
        self.assertEqual(client.calls[1][4], nonce)
        self.assertNotIn(nonce, json.dumps(result))
        self.assertFalse(result["nonce_exported"])

    def test_GVP_unqualified_bootstrap_origin_never_posts(self):
        page = b'<script>const gvp_config = {rest_url: "https://evil.invalid/", nonce: "ExampleNonce12"}</script>'
        client = FakeClient([Response(200, page)])
        with self.assertRaises(SourceError):
            org.staffing(personal_noncommercial_use=True, client=client)
        self.assertEqual(len(client.calls), 1)

    def test_GVP_error_count_conflict_or_controls_never_empty_success(self):
        native = json.loads(json.loads(staff()))
        for bad in [{"error": "rate_limited"}, {**native, "current_count": 0}, {**native, "data": '<form>Unlock</form>'}]:
            with self.subTest(bad=bad), self.assertRaises(SourceError):
                org.parse_staffing(json.dumps(bad).encode(), 1)


class TransportTests(unittest.TestCase):
    def test_protected_and_write_routes_are_never_allowed(self):
        for url, method in [(GVP_FILTER.replace("filter", "challenge"), "POST"),
                            (GVP_FILTER.replace("filter", "detail"), "POST"),
                            (MEIN_SEARCH.replace("/read/", "/write/"), "POST"),
                            (HRK_DOWNLOAD + "?token=x", "GET"), (GVP_PAGE, "POST")]:
            with self.subTest(url=url), self.assertRaises(SourceError):
                checked_url(url, method)

    def test_qualified_API_robots404_is_not_denial(self):
        client = Client()
        calls = []
        def raw(url, method="GET", body=None, headers=None):
            calls.append(url)
            if url.endswith("robots.txt"):
                raise SourceError("HTTP404", http_status=404)
            return Response(201, b"{}")
        with patch.object(client, "_raw", side_effect=raw):
            client.post(MEIN_SEARCH, b"{}")
        self.assertEqual(len(calls), 2)

    def test_real_robots_denial_stops_read_POST(self):
        client = Client()
        calls = []
        def raw(url, *args, **kwargs):
            calls.append(url)
            return Response(200, b"User-agent: *\nDisallow: /api/\n")
        with patch.object(client, "_raw", side_effect=raw), self.assertRaises(SourceError):
            client.post(MEIN_SEARCH, b"{}")
        self.assertEqual(len(calls), 1)

    def test_unqualified_robots_status_never_becomes_empty(self):
        for status in [403, 429, 503]:
            client = Client()
            with patch.object(client, "_raw", side_effect=SourceError("HTTP", http_status=status)), self.assertRaises(SourceError):
                client.post(MEIN_SEARCH, b"{}")


if __name__ == "__main__":
    unittest.main()
