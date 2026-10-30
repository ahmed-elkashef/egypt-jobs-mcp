"""Original source-shape, complete-body, credential and redirect regressions."""
import importlib.util
import json
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "reader.py"
spec = importlib.util.spec_from_file_location("original_jobshop_reader", P)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
U = "f885a1e6-8c10-427d-965c-966aa30d34d4"
CANONICAL = r.ORIGIN + "/jobs/native-student-role/" + U
LEGACY = r.ORIGIN + "/offer-redirect/?offerApiId=MTAwNDY=&showApplicationForm=false"
VENDOR = r.VENDOR + "/api/offer/v1/offer/offer-redirect?externalId=10046&jobshopVanity=fraport-professionals&offerApiId=MTAwNDY=&showApplicationForm=false"
FINAL = CANONICAL + "?offerApiId=MTAwNDY%3D"
TITLE = "Studentische Aushilfe Öffentlichkeitsarbeit"
SECRET = "SYNTHETIC_SECRET_NEVER_PROPAGATE"


def envelope(data):
    table = [["ShallowReactive", 1], {"data": 2}, ["ShallowReactive", 3], {}]
    def add(value):
        index = len(table)
        table.append(None)
        if isinstance(value, dict):
            table[index] = {key: add(item) for key, item in value.items()}
        elif isinstance(value, list):
            table[index] = [add(item) for item in value]
        else:
            table[index] = value
        return index
    table[3].update({key: add(value) for key, value in data.items()})
    return '<script id="__NUXT_DATA__" type="application/json">' + json.dumps(table) + '</script>'


def page(rows=None, total=None, *, home=False):
    rows = rows if rows is not None else [{"url": CANONICAL, "title": TITLE}, {"url": LEGACY, "title": "Native legacy role"}]
    total = len(rows) if total is None else total
    payload = {"typesenseApiKey-tenant": SECRET}
    payload.update({"typesenseJobCounts": {"count": total, "categories": {}}} if home else {"ssrJobLinks-tenant-search": rows})
    anchors = '' if home else ''.join('<a href="' + row["url"].replace('&', '&amp;') + '">' + row["title"] + '</a>' for row in rows)
    return ('<html><body>' + anchors + envelope(payload) + '</body></html>').encode()


def detail(*, description="", primary=True, uuid=U, title=TITLE, external="10046"):
    native = {"offer_uuid": uuid, "title": title, "description": description, "external_id": external,
              "career_level": ["Werkstudententätigkeit"], "work_mode": [], "create_date": "2026-10-05",
              "start_date": "2026-10-08", "title_embed": [0.1] * 384, "settings": {"api_key": SECRET}}
    data = envelope({"typesenseApiKey-tenant": SECRET, "jobData-" + uuid: native})
    schema = {"@context": "https://schema.org", "@graph": [{"@type": "JobPosting", "title": title,
              "identifier": {"value": uuid}, "educationRequirements": "Werkstudententätigkeit",
              "datePosted": "2026-10-05", "jobStartDate": "2026-10-08", "validThrough": "2036-10-08"}]}
    section = '<section class="job-data-section"><h2>Aufgaben und Profil</h2><p>Vollständige Tätigkeiten, Anforderungen und überraschendes spätes Pflichtkriterium.</p></section>' if primary else ''
    main = '<main class="main-container"><section class="hero-section"><h1>' + title + '</h1></section><section class="text-section">Company introduction</section>' + section + '<section class="gallery-section">Other person testimonial, not a requirement.</section><form><label>Documents max5MB</label><input type="hidden" value="' + SECRET + '"></form><script>secret="' + SECRET + '"</script><style>not body</style></main>'
    return ('<html><body>' + main + '<script type="application/ld+json">' + json.dumps(schema) + '</script>' + data + '</body></html>').encode()


def response(raw, **kwargs):
    return {"body": raw, "content_type": "text/html", **kwargs}


class NativeJobshopTests(unittest.TestCase):
    def test_all_ssr_rows_anchor_titles_and_independent_count_reconcile(self):
        result = r.parse_inventory(page(home=True), page())
        self.assertEqual(2, result["returned_count"])
        self.assertEqual(2, result["source_result_count"])
        self.assertIsNone(result["pagination"]["next_url"])
        self.assertEqual([CANONICAL, LEGACY], [row["url"] for row in result["listings"]])
        self.assertTrue(all(row["original_published_at"] is None for row in result["listings"]))

    def test_native_keys_vectors_and_unused_credential_configuration_never_export(self):
        values = [r.parse_inventory(page(home=True), page()), r.parse_detail(detail(), LEGACY, FINAL)]
        for value in values:
            encoded = json.dumps(value)
            self.assertNotIn(SECRET, encoded)
            self.assertNotIn('title_embed', encoded)
            self.assertNotIn('typesenseApiKey', encoded)
        self.assertEqual(["Documents max5MB"], values[1]["native_application_form_text_data_only"])

    def test_missing_schema_description_still_retains_complete_primary_cms_and_context(self):
        value = r.parse_detail(detail(), LEGACY, FINAL)
        self.assertNotIn("description", value["native_job_posting"])
        self.assertIn("spätes Pflichtkriterium", value["description"])
        self.assertIn("Other person testimonial", value["native_full_main_text"])
        self.assertNotIn("Other person testimonial", value["description"])
        self.assertTrue(value["source_body_untruncated"])
        self.assertIsNone(value["visible_description"])
        self.assertFalse(value["full_posting_reviewed"])

    def test_native_fields_and_raw_clocks_do_not_become_deadline_original_or_eligibility(self):
        value = r.parse_detail(detail(), LEGACY, FINAL)
        self.assertEqual("2036-10-08", value["native_schema_valid_through"])
        self.assertEqual("2026-10-08", value["native_schema_start_date"])
        self.assertEqual("Werkstudententätigkeit", value["native_job_posting"]["educationRequirements"])
        self.assertIsNone(value["original_published_at"])
        self.assertNotIn("worker_countries", value)
        self.assertNotIn("models", value)

    def test_canonical_uuid_and_opaque_legacy_publication_references_remain_distinct(self):
        self.assertNotEqual(r.job_uri(CANONICAL)[1], r.job_uri(LEGACY)[1])
        value = r.parse_detail(detail(), LEGACY, FINAL)
        self.assertEqual(r.job_uri(LEGACY)[1], value["id"])
        self.assertEqual(U, value["native_offer_uuid"])

    def test_partial_ssr_cannot_match_the_complete_board_total(self):
        with self.assertRaises(r.SourceError):
            r.parse_inventory(page(total=3, home=True), page())

    def test_anchor_mismatch_is_not_silently_replaced_by_payload(self):
        for change in [page().replace(TITLE.encode(), b"Wrong", 1), page().replace(b'<a href=', b'<span href=', 1)]:
            with self.subTest(change=change), self.assertRaises(r.SourceError):
                r.parse_inventory(page(home=True), change)

    def test_duplicate_native_rows_are_refused(self):
        rows = [{"url": CANONICAL, "title": TITLE}] * 2
        with self.assertRaises(r.SourceError):
            r.parse_inventory(page(rows, home=True), page(rows))

    def test_explicit_independent_zero_works_but_translation_or_error_page_does_not(self):
        self.assertEqual(0, r.parse_inventory(page([], home=True), page([]))["returned_count"])
        with self.assertRaises(r.SourceError):
            r.parse_inventory(page([], home=True), b'<p>Keine passenden Jobs gefunden.</p>')

    def test_wrong_total_boolean_is_not_native_one(self):
        with self.assertRaises(r.SourceError):
            r.parse_inventory(page(total=True, home=True), page())

    def test_missing_primary_section_is_not_completed_by_schema_or_company_context(self):
        with self.assertRaises(r.SourceError):
            r.parse_detail(detail(primary=False), LEGACY, FINAL)

    def test_source_title_double_space_matches_rendered_whitespace_without_rewriting_raw_title(self):
        raw_title = "Studentische Aushilfe  Öffentlichkeitsarbeit"
        value = r.parse_detail(detail(title=raw_title), LEGACY, FINAL)
        self.assertEqual(raw_title, value["title"])
        self.assertEqual(raw_title, value["native_job_fields"]["title"])
        self.assertIn("spätes Pflichtkriterium", value["description"])

    def test_source_title_or_final_uuid_change_refuses(self):
        for final in [CANONICAL.replace(U, "00000000-0000-4000-8000-000000000001"), CANONICAL]:
            with self.subTest(final=final), self.assertRaises(r.SourceError):
                r.parse_detail(detail(), LEGACY, final)
        with self.assertRaises(r.SourceError):
            r.parse_detail(detail().replace(TITLE.encode(), b"Wrong", 1), LEGACY, FINAL)

    def test_non_html_and_non_utf8_are_not_partial_bodies(self):
        for raw in [b'%PDF-1.4', b'\xff']:
            with self.subTest(raw=raw), self.assertRaises(r.SourceError):
                r.document(raw)

    def test_duplicate_json_keys_and_nonfinite_table_numbers_are_refused(self):
        for source in [b'{"a":1,"a":2}', b'[NaN]', b'[1e999]']:
            with self.subTest(source=source), self.assertRaises(r.SourceError):
                r.load_json(source)

    def test_unsupported_index_or_cycle_is_explicit(self):
        t = r.NativeTable(r.document(page()))
        for index in [-7, True, len(t.table)]:
            with self.subTest(index=index), self.assertRaises(r.SourceError):
                t.at(index)
        t.table.append([len(t.table)])
        with self.assertRaises(r.SourceError):
            t.resolve(len(t.table) - 1)

    def test_unknown_native_sentinel_is_preserved_without_invented_semantics(self):
        t = r.NativeTable(r.document(page()))
        self.assertEqual({"native_unresolved_reference": -7}, t.resolve(-7))

    def test_projection_budget_refuses_whole_output_without_clipping(self):
        t = r.NativeTable(r.document(page()))
        t.steps = 200000
        with self.assertRaises(r.SourceError):
            t.resolve(0)

    def test_unverified_origin_role_queries_and_application_paths_never_request(self):
        calls = []
        def transport(url, **kwargs):
            calls.append(url)
            raise AssertionError("Must refuse before network")
        for args in [{"career_origin": "https://unknown.job-shop.com"}, {"job_url": r.ORIGIN + '/apply'},
                     {"job_url": CANONICAL + '?q=marketing'}, {"job_url": LEGACY.replace('false', 'true')}]:
            with self.subTest(args=args), self.assertRaises(r.SourceError):
                r.read(**args, transport=transport)
        self.assertEqual([], calls)

    def test_native_inventory_requests_only_robots_home_and_whole_search(self):
        calls = []
        def transport(url, **kwargs):
            calls.append(url)
            if url.endswith('robots.txt'):
                return {"body": b'User-agent: *\nAllow: /', "content_type": "text/plain"}
            return response(page(home=url.endswith('/')))
        result = r.read(career_origin=r.ORIGIN, transport=transport)
        self.assertEqual(2, result["returned_count"])
        self.assertEqual([r.ORIGIN+'/robots.txt', r.ORIGIN+'/', r.ORIGIN+'/search'], calls)

    def test_native_two_redirect_chain_checks_each_policy_without_auth_or_guessing(self):
        calls = []
        def transport(url, **kwargs):
            calls.append(url)
            if url.endswith('robots.txt'):
                if url.startswith(r.VENDOR):
                    raise r.SourceError('not_found', http_status=404)
                return {"body": b'User-agent: *\nAllow: /', "content_type": "text/plain"}
            if url == LEGACY:
                return response(b'', http_status=301, location=VENDOR)
            if url == VENDOR:
                return response(b'', http_status=301, location=FINAL)
            self.assertEqual(FINAL, url)
            return response(detail())
        value = r.read(job_url=LEGACY, transport=transport)
        self.assertEqual(3, len(value["provenance"]))
        self.assertEqual(5, len(calls))
        self.assertTrue(value["source_body_untruncated"])

    def test_robots403_or_policy_disallow_stops_without_asset_account_or_fallback(self):
        for failure in ['403', 'disallow', 'redirect']:
            calls = []
            def transport(url, **kwargs):
                calls.append(url)
                if failure == '403':
                    raise r.SourceError('denied', http_status=403)
                if failure == 'redirect':
                    return response(b'', http_status=301, location='https://elsewhere.example/')
                return {"body": b'User-agent: *\nDisallow: /search', "content_type": "text/plain"} if url.endswith('robots.txt') else response(page(home=True))
            with self.subTest(failure=failure), self.assertRaises(r.SourceError):
                r.read(career_origin=r.ORIGIN, transport=transport)
            self.assertNotIn(r.ORIGIN+'/search', calls)

    def test_arbitrary_vendor_redirect_or_apply_target_never_requested(self):
        for target in [VENDOR.replace('fraport-professionals', 'other'), VENDOR.replace('MTAwNDY=', 'wrong'),
                       r.ORIGIN+'/application/apply', 'https://attacker.example/jobs/native/'+U]:
            calls = []
            def transport(url, **kwargs):
                calls.append(url)
                return {"body": b'User-agent: *\nAllow: /'} if url.endswith('robots.txt') else response(b'', http_status=301, location=target)
            with self.subTest(target=target), self.assertRaises(r.SourceError):
                r.read(job_url=LEGACY, transport=transport)
            self.assertNotIn(target, calls)

    def test_vendor_external_reference_change_refuses_before_claiming_complete_body(self):
        def transport(url, **kwargs):
            if url.endswith('robots.txt'):
                return {"body": b'User-agent: *\nAllow: /'}
            if url == LEGACY:
                return response(b'', http_status=301, location=VENDOR)
            return response(b'', http_status=301, location=FINAL) if url == VENDOR else response(detail(external='20000'))
        with self.assertRaises(r.SourceError):
            r.read(job_url=LEGACY, transport=transport)

    def test_source429_retry_after_survives_without_empty_supply(self):
        def transport(url, **kwargs):
            if url.endswith('robots.txt'):
                return {"body": b'User-agent: *\nAllow: /'}
            raise r.SourceError('limited', http_status=429, retry_after='90')
        with self.assertRaises(r.SourceError) as caught:
            r.read(career_origin=r.ORIGIN, transport=transport)
        self.assertEqual(429, caught.exception.http_status)
        self.assertEqual('90', caught.exception.retry_after)

    def test_redirect_cycle_and_too_many_hops_do_not_create_empty_page(self):
        def transport(url, **kwargs):
            return {"body": b'User-agent: *\nAllow: /'} if url.endswith('robots.txt') else response(b'', http_status=301, location=LEGACY)
        with self.assertRaises(r.SourceError):
            r.read(job_url=LEGACY, transport=transport)

    def test_unexpected_pdf_content_type_refuses(self):
        def transport(url, **kwargs):
            return {"body": b'User-agent: *\nAllow: /'} if url.endswith('robots.txt') else response(b'%PDF', content_type='application/pdf')
        with self.assertRaises(r.SourceError):
            r.read(job_url=CANONICAL, transport=transport)

    def test_explicit_redirect_metadata_returns_only_header_and_never_follows(self):
        from urllib.error import HTTPError
        class Opener:
            def __init__(self):
                self.calls = 0
            def open(inner, req, timeout):
                inner.calls += 1
                self.assertEqual(10, timeout)
                self.assertNotIn("Authorization", req.headers)
                self.assertNotIn("Cookie", req.headers)
                raise HTTPError(LEGACY, 301, "Moved", {"Location": VENDOR}, None)
        opener = Opener()
        value = r.request(LEGACY, accept="text/html", opener=opener, timeout=10, redirect_metadata=True)
        self.assertEqual(301, value["http_status"])
        self.assertEqual(VENDOR, value["location"])
        self.assertEqual(b"", value["body"])
        self.assertEqual(1, opener.calls)

    def test_default_common_request_still_refuses_redirects_for_existing_readers(self):
        from urllib.error import HTTPError
        class Opener:
            def open(inner, req, timeout):
                raise HTTPError(LEGACY, 301, "Moved", {"Location": VENDOR}, None)
        with self.assertRaises(r.SourceError) as caught:
            r.request(LEGACY, accept="text/html", opener=Opener())
        self.assertEqual(301, caught.exception.http_status)

    def test_offline_capabilities_use_no_profile_or_candidate_fact(self):
        value = r.capabilities()
        self.assertEqual([r.ORIGIN], value["independently_verified_origins"])
        self.assertFalse(value["coverage_complete"])
        self.assertEqual([], value["acquisition_filters"])


if __name__ == '__main__':
    unittest.main()
