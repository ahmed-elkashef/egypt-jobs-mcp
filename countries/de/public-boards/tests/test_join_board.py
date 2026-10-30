"""Synthetic protocol regressions; no copied employer advertisements or applicant data."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import join_board as reader  # noqa: E402

COMPANY = "example-company"
BOARD = reader.inventory_uri(COMPANY)
PRIMARY = "<h2>The role</h2><p>Complete source duties and requirements.</p>"


def company():
    return {
        "id": 11,
        "domain": COMPANY,
        "name": "Synthetic employer",
        "isPublic": True,
        "desc": "Separate company context",
        "preference": {"isSpontaneousApplicationEnabled": True},
    }


def listing(number):
    return {
        "id": number + 100,
        "idParam": str(number + 200) + "-synthetic-role",
        "title": "Synthetic role " + str(number),
        "createdAt": "2025-01-02T10:00:00Z",
        "country": {"iso3166": "DE"},
        "city": {"cityName": "Berlin"},
        "employmentType": {"name": "Employee"},
        "workplaceType": "HYBRID",
        "remoteType": None,
    }


def document(state, query, route, variant="pageData", primary="", schema=None, canonical=None):
    payload = {
        "props": {"pageProps": {"isOnline": True, variant: state}},
        "query": query,
        "page": route,
    }
    anchors = "".join(
        '<a href="' + reader.job_uri(COMPANY, r["idParam"]) + '">job</a>'
        for r in (state.get("jobs") or {}).get("items", [])
    )
    extras = '<link rel="canonical" href="' + canonical + '">' if canonical else ""
    if schema is not None:
        extras += '<script type="application/ld+json">' + json.dumps(schema) + "</script>"
    return (
        "<html><head>"
        + extras
        + "</head><body>"
        + anchors
        + primary
        + '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload).replace("<", "\\u003c")
        + "</script></body></html>"
    ).encode()


def inventory_state(total=5, page=1, native_page=None, enabled=True):
    real_total = total - int(enabled)
    real_pages = (real_total + 4) // 5
    native_page = native_page or (max(1, real_pages) if page > real_pages else page)
    count = max(0, min(5, real_total - (native_page - 1) * 5))
    return {
        "company": {**company(), "preference": {"isSpontaneousApplicationEnabled": enabled}},
        "currentUser": {"token": "SYNTHETIC_DO_NOT_EXPORT"},
        "jobs": {
            "items": [
                listing(i) for i in range((native_page - 1) * 5, (native_page - 1) * 5 + count)
            ],
            "filters": {},
            "pagination": {
                "page": native_page,
                "pageCount": (total + 4) // 5,
                "pageSize": 5,
                "perPage": 5,
                "total": total,
            },
        },
    }


def parse_inventory(state=None, page=1, variant="pageData", query=None):
    state = state or inventory_state()
    query = query or {"companySlug": COMPANY, **({"page": str(page)} if page > 1 else {})}
    raw = document(
        state, query, "/companies/[companySlug]" + ("/_dynamic" if page > 1 else ""), variant
    )
    return reader.inventory(raw, reader.inventory_uri(COMPANY, page))


def job_state(nested=False):
    corp = company()
    job = {
        "id": 100,
        "idParam": "200-synthetic-role",
        "title": "Synthetic role",
        "companyId": 11,
        "company": corp,
        "description": PRIMARY,
        "companyDesc": "Separate job company context",
        "status": "ONLINE",
        "createdAt": "2025-01-02T10:00:00Z",
        "updatedAt": "2026-10-29T10:00:00Z",
        "employmentTerms": {"weeklyWorkingHours": 40},
        "country": {"iso3166": "DE"},
    }
    return {
        "company": None if nested else corp,
        "job": job,
        "currentUser": {"token": "SYNTHETIC_DO_NOT_EXPORT"},
    }


def detail_bytes(
    state=None, primary=PRIMARY, schema_changes=None, canonical=None, variant="pageData"
):
    state = state or job_state()
    url = reader.job_uri(COMPANY, state["job"]["idParam"])
    schema = {
        "@type": "JobPosting",
        "url": url,
        "title": state["job"]["title"],
        "description": "Only a summary",
    }
    schema.update(schema_changes or {})
    return document(
        state,
        {"companySlug": COMPANY, "id": state["job"]["idParam"]},
        "/companies/[companySlug]/[id]",
        variant,
        primary,
        schema,
        canonical or url,
    ), url


class JoinBoardTests(unittest.TestCase):
    def test_both_native_ssr_variants_preserve_all_vacancies_and_general_context(self):
        for variant in ["initialState", "pageData"]:
            data = parse_inventory(variant=variant)
            self.assertEqual((data["returned_count"], data["source_result_count"]), (4, 4))
            self.assertEqual(data["native_total_including_general_context"], 5)
            self.assertEqual(len(data["native_general_contexts"]), 1)
            self.assertFalse(data["native_general_contexts"][0]["vacancy"])

    def test_virtual_last_page_keeps_cached_rows_without_recounting_them(self):
        data = parse_inventory(inventory_state(total=11, page=3), page=3)
        self.assertEqual(data["source_result_count"], 10)
        self.assertEqual(data["listings"], [])
        self.assertEqual(len(data["native_cached_noncurrent_rows"]), 5)
        self.assertEqual(data["pagination"]["native_source_page"], 2)
        self.assertTrue(data["pagination"]["virtual_context_page"])
        self.assertIsNone(data["pagination"]["next_url"])

    def test_normal_later_page_has_exact_native_continuation(self):
        data = parse_inventory(inventory_state(total=16, page=2), page=2)
        self.assertEqual(data["returned_count"], 5)
        self.assertEqual(data["pagination"]["next_url"], BOARD + "?page=3")
        self.assertEqual(data["native_general_contexts"], [])

    def test_disabled_general_context_does_not_subtract_a_vacancy(self):
        data = parse_inventory(inventory_state(total=5, enabled=False))
        self.assertEqual(data["source_result_count"], 5)
        self.assertEqual(data["native_general_contexts"], [])

    def test_distinct_internal_and_public_ids_and_native_clocks_remain_distinct(self):
        row = parse_inventory()["listings"][0]
        self.assertEqual(row["native_job_id"], 100)
        self.assertEqual(row["native_url_posting_id"], 200)
        self.assertEqual(row["id"], "join::example-company::100")
        self.assertIsNone(row["original_published_at"])
        self.assertEqual(row["native_created_at"], "2025-01-02T10:00:00Z")
        self.assertIsNone(row["native_model_label"])

    def test_missing_rows_and_boolean_or_changed_page_size_refuse(self):
        cases = []
        state = inventory_state()
        state["jobs"]["items"].pop()
        cases.append(state)
        for key, value in [("total", True), ("pageSize", 10), ("perPage", 10), ("pageCount", 2)]:
            state = inventory_state()
            state["jobs"]["pagination"][key] = value
            cases.append(state)
        for state in cases:
            with self.assertRaises(reader.SourceError):
                parse_inventory(state)

    def test_hidden_role_filters_and_missing_spontaneous_flag_refuse(self):
        state = inventory_state()
        state["jobs"]["filters"] = {"categoryIds": [4]}
        with self.assertRaises(reader.SourceError):
            parse_inventory(state)
        state = inventory_state()
        state["company"]["preference"] = {}
        with self.assertRaises(reader.SourceError):
            parse_inventory(state)

    def test_wrong_company_duplicate_ids_and_missing_rendered_anchor_refuse(self):
        state = inventory_state()
        state["company"]["domain"] = "other-employer"
        with self.assertRaises(reader.SourceError):
            parse_inventory(state)
        state = inventory_state()
        state["jobs"]["items"][1]["id"] = state["jobs"]["items"][0]["id"]
        with self.assertRaises(reader.SourceError):
            parse_inventory(state)
        raw = document(inventory_state(), {"companySlug": COMPANY}, "/companies/[companySlug]")
        with self.assertRaises(reader.SourceError):
            reader.inventory(raw.replace(b"<a href=", b"<span data-url="), BOARD)

    def test_nonvirtual_page_reset_refuses(self):
        state = inventory_state(total=16, page=2)
        state["jobs"]["pagination"]["page"] = 1
        with self.assertRaises(reader.SourceError):
            parse_inventory(state, page=2)

    def test_account_general_application_role_filters_and_external_origins_refuse(self):
        for url, operation in [
            (ORIGIN + "/auth/login/candidate", "detail"),
            (BOARD + "/spontaneous-application", "detail"),
            (BOARD + "?categoryIds=1", "inventory"),
            (BOARD + "?page=1", "inventory"),
            (BOARD + "?page=02", "inventory"),
            (BOARD + "?page=2&page=3", "inventory"),
            (BOARD.replace("join.com", "join.com.evil.example"), "inventory"),
            (BOARD.replace("https://", "https://user@"), "inventory"),
        ]:
            with self.assertRaises(reader.SourceError):
                reader.checked_url(url, operation)

    def test_primary_full_html_is_separate_from_schema_and_company_context(self):
        raw, url = detail_bytes()
        data = reader.detail(raw, url)
        self.assertEqual(data["raw_primary_description"], PRIMARY)
        self.assertIn("Complete source duties", data["visible_description"])
        self.assertEqual(data["schema_description"], "Only a summary")
        self.assertEqual(len(data["native_context_sections"]), 2)
        self.assertNotIn("Separate company context", data["description"])
        self.assertFalse(data["schema_description_used_as_full_body"])
        self.assertTrue(data["source_body_untruncated"])

    def test_nested_native_company_variant_is_supported_without_invented_company(self):
        raw, url = detail_bytes(job_state(nested=True))
        data = reader.detail(raw, url)
        self.assertEqual(data["native_company_id"], 11)
        self.assertEqual(data["native_company_name"], "Synthetic employer")

    def test_native_full_description_must_actually_be_rendered(self):
        raw, url = detail_bytes(primary="<p>Only a summary</p>")
        with self.assertRaises(reader.SourceError):
            reader.detail(raw, url)

    def test_schema_summary_never_substitutes_for_missing_primary(self):
        state = job_state()
        state["job"]["description"] = ""
        raw, url = detail_bytes(state)
        with self.assertRaises(reader.SourceError):
            reader.detail(raw, url)

    def test_wrong_canonical_schema_or_native_identity_refuse(self):
        for changes in [{"title": "Another role"}, {"url": BOARD + "/201-other-role"}]:
            raw, url = detail_bytes(schema_changes=changes)
            with self.assertRaises(reader.SourceError):
                reader.detail(raw, url)
        raw, url = detail_bytes(canonical=BOARD + "/201-other-role")
        with self.assertRaises(reader.SourceError):
            reader.detail(raw, url)
        state = job_state()
        state["job"]["companyId"] = 12
        raw, url = detail_bytes(state)
        with self.assertRaises(reader.SourceError):
            reader.detail(raw, url)

    def test_no_original_clock_student_eligibility_or_hydration_credentials_invented(self):
        raw, url = detail_bytes()
        data = reader.detail(raw, url)
        self.assertIsNone(data["original_published_at"])
        self.assertEqual(data["native_job_facts"]["employmentTerms"]["weeklyWorkingHours"], 40)
        self.assertFalse(data["full_posting_reviewed"])
        self.assertNotIn("SYNTHETIC_DO_NOT_EXPORT", json.dumps(data))
        self.assertNotIn("SYNTHETIC_DO_NOT_EXPORT", json.dumps(parse_inventory()))

    def test_hidden_native_query_category_cannot_be_registered_as_whole_supply(self):
        with self.assertRaises(reader.SourceError):
            parse_inventory(query={"companySlug": COMPANY, "categoryIds": "7"})

    def test_two_competing_ssr_state_objects_refuse(self):
        raw = document(inventory_state(), {"companySlug": COMPANY}, "/companies/[companySlug]")
        marker = b'"isOnline": true, '
        raw = raw.replace(marker, marker + b'"initialState": {}, ', 1)
        with self.assertRaises(reader.SourceError):
            reader.inventory(raw, BOARD)

    def test_detail_alias_requires_connected_same_company_redirect_evidence(self):
        raw, url = detail_bytes()
        for requested, hops in [
            (BOARD + "/190-previous-role", []),
            (
                BOARD + "/190-previous-role",
                [{"from": BOARD + "/191-other-role", "to": url, "http_status": 301}],
            ),
            (target_company_url(), [{"from": target_company_url(), "to": url, "http_status": 301}]),
        ]:
            with self.assertRaises(reader.SourceError):
                reader.detail(raw, url, requested_url=requested, redirects=hops)

    def test_primary_unsafe_resources_are_data_without_executable_output(self):
        state = job_state()
        state["job"]["description"] = (
            PRIMARY + '<script>DO_NOT_EXECUTE</script><img src="https://example.invalid/image">'
        )
        raw, url = detail_bytes(state, primary=state["job"]["description"])
        data = reader.detail(raw, url)
        self.assertNotIn("DO_NOT_EXECUTE", data["description"])
        self.assertNotIn("<img", data["description"])
        self.assertIn("DO_NOT_EXECUTE", data["raw_primary_description"])

    def test_transport_source_limit_keeps_http_and_retry_evidence(self):
        def transport(url, **kwargs):
            if url.endswith("/robots.txt"):
                return {"body": b"User-agent: *\n"}
            raise reader.SourceError("source_http_error", http_status=429, retry_after="60")

        with self.assertRaises(reader.SourceError) as raised:
            reader.read("inventory", BOARD, transport=transport)
        self.assertEqual(raised.exception.http_status, 429)
        self.assertEqual(raised.exception.retry_after, "60")

    def test_ambiguous_or_missing_next_data_is_not_empty_supply(self):
        for raw in [
            b"<html>No public data</html>",
            document(
                inventory_state(), {"companySlug": COMPANY}, "/companies/[companySlug]"
            ).replace(b'id="__NEXT_DATA__"', b'id="OTHER_DATA"'),
        ]:
            with self.assertRaises(reader.SourceError):
                reader.inventory(raw, BOARD)

    def test_source_closed_status_is_preserved_separately(self):
        state = job_state()
        state["job"]["status"] = "OFFLINE"
        raw, url = detail_bytes(state)
        data = reader.detail(raw, url)
        self.assertTrue(data["source_explicit_closed"])
        self.assertEqual(data["native_status"], "OFFLINE")

    def test_no_provider_request_for_invalid_or_policy_denied_route(self):
        calls = []

        def transport(url, **kwargs):
            calls.append(url)
            return {"body": b"User-agent: *\nDisallow: /companies/\n"}

        with self.assertRaises(reader.SourceError):
            reader.read("detail", BOARD + "/spontaneous-application", transport=transport)
        self.assertEqual(calls, [])
        with self.assertRaises(reader.SourceError):
            reader.read("inventory", BOARD, transport=transport)
        self.assertEqual(calls, [reader.ORIGIN + "/robots.txt"])

    def test_native_same_company_redirect_and_complete_body_are_preserved(self):
        raw, target = detail_bytes()
        old = BOARD + "/190-previous-role"
        calls = []

        def transport(url, **kwargs):
            calls.append(url)
            if url.endswith("/robots.txt"):
                return {"body": b"User-agent: *\nDisallow: /auth/\n"}
            if url == old:
                return {"body": b"", "http_status": 301, "location": target}
            return {"body": raw}

        data = reader.read("detail", old, transport=transport)
        self.assertEqual(calls, [reader.ORIGIN + "/robots.txt", old, target])
        self.assertEqual(data["requested_url"], old)
        self.assertEqual(data["canonical_url"], target)
        self.assertEqual(data["id"], "join::example-company::100")
        self.assertEqual(len(data["native_redirects"]), 1)

    def test_changed_company_or_account_redirect_is_not_requested(self):
        for location in [
            BOARD + "/spontaneous-application",
            reader.ORIGIN + "/auth/login/candidate",
            target_company_url(),
        ]:
            calls = []

            def transport(url, **kwargs):
                calls.append(url)
                return (
                    {"body": b"User-agent: *\n"}
                    if url.endswith("/robots.txt")
                    else {"body": b"", "http_status": 302, "location": location}
                )

            with self.assertRaises(reader.SourceError):
                reader.read("detail", BOARD + "/190-previous-role", transport=transport)
            self.assertEqual(len(calls), 2)


def target_company_url():
    return reader.ORIGIN + "/companies/another-company/200-synthetic-role"


ORIGIN = reader.ORIGIN
if __name__ == "__main__":
    unittest.main()
