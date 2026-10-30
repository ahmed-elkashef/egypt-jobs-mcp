import importlib.util
import json
import unittest
from pathlib import Path
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location("onlyfy_reader", Path(__file__).parents[1] / "reader.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE = "https://example.onlyfy.jobs/en"
ORIGIN = "https://example.onlyfy.jobs"
HANDLE = "nativehandle0001"
JOB = BASE + "/job/" + HANDLE
TITLE = "Sekretärin / native student role"


def inventory(page=1, total=23, locale="en"):
    first, last = (page - 1) * 10 + 1, min(page * 10, total)
    cards = "".join(f'<a href="/{locale}/job/nativehandle{i:04d}" aria-label="Sekretärin {i}"><h3>Sekretärin {i}</h3><div>Native city | Employer model</div></a>' for i in range(first, last + 1))
    count = f"{first}-{last} {'out of' if locale == 'en' else 'von'} {total} jobs" if total else "0 jobs found"
    nav = (f'<nav aria-label="pagination"><button aria-current="page">{page}</button><button aria-label="Go to next page"'
           + (' disabled=""' if last >= total else '') + '></button></nav>') if total else ""
    return f'<html><body><p>{count}</p>{cards}{nav}<script>var misleading="1 job found";</script></body></html>'.encode()


def shell(**changes):
    schema = {"@type": "JobPosting", "title": TITLE, "description": "Schema summary. " * 10,
              "datePosted": "2026-09-09", "employmentType": "OTHER", "jobLocationType": "TELECOMMUTE",
              "identifier": {"value": "different-opening-id"}, "applicantLocationRequirements": [{"name": "DE"}]}
    schema.update(changes)
    return ('<html><body><script type="application/ld+json" data-testid="job-posting-json-ld">'
            + json.dumps(schema, ensure_ascii=False) + '</script><a data-testid="print" href="'
            + ORIGIN + '/candidate/job/print/' + HANDLE + '?mode=print&amp;lang=en">Print</a></body></html>').encode()


def full(title=TITLE, extra="Export-only additional variant"):
    return (f'<html><body><div class="job-ad-component"><main class="main-element"><h1>{title}</h1>'
            '<h3>Tasks</h3><p>Complete native tasks and engineering-study requirement.</p>'
            '<h3>Benefits</h3><p>Complete benefits and native contact.</p>'
            f'<a href="/application/apply/{HANDLE}">Apply</a></main>'
            f'<div class="step-stone-job-ad"><h1>{title}</h1><p>{extra}</p></div></div></body></html>').encode()


class Transport:
    def __init__(self, *, listing=None, shell_raw=None, full_raw=None, robots=None):
        self.listing = inventory() if listing is None else listing
        self.shell_raw = shell() if shell_raw is None else shell_raw
        self.full_raw = full() if full_raw is None else full_raw
        self.robots, self.calls = robots, []

    def __call__(self, url, *, accept, **kwargs):
        self.calls.append((url, accept))
        if url.endswith("/robots.txt"):
            if self.robots is None:
                raise m.SourceError("source_http_error", http_status=404)
            if isinstance(self.robots, int):
                raise m.SourceError("source_http_error", http_status=self.robots)
            return {"body": self.robots.encode()}
        if "/job/show/" in url:
            value = self.full_raw
        elif "/en/job/" in url:
            value = self.shell_raw
        else:
            value = self.listing
        if isinstance(value, Exception):
            raise value
        return {"body": value, "content_type": "text/html; charset=UTF-8"}


class ReaderTests(unittest.TestCase):
    def test_exact_verified_vendor_board_only(self):
        self.assertEqual((BASE, ORIGIN, "en"), m.board(BASE))
        self.assertEqual("de", m.board(ORIGIN + "/de")[2])
        for value in [None, "http://example.onlyfy.jobs/en", BASE + "/", BASE + "?query=PR", BASE + "#x",
                      "https://api.onlyfy.jobs/en", "https://a@example.onlyfy.jobs/en", "https://example.onlyfy.jobs:443/en",
                      "https://example.onlyfy.jobs.evil.test/en", "https://example.onlyfy.io/en", ORIGIN + "/application/apply/x"]:
            with self.subTest(value=value), self.assertRaises(m.SourceError):
                m.board(value)

    def test_complete_page_and_native_continuation_preserved(self):
        result = m.parse_inventory(inventory(), BASE)
        self.assertEqual(10, result["returned_count"])
        self.assertEqual(23, result["source_result_count"])
        self.assertEqual(2, result["pagination"]["next_page"])
        self.assertEqual(BASE + "?page=2", result["pagination"]["next_url"])
        self.assertFalse(result["coverage_complete"])

    def test_last_partial_page_and_disabled_next_reconcile(self):
        result = m.parse_inventory(inventory(3), BASE, page=3, first_page_total=23)
        self.assertEqual(3, result["returned_count"])
        self.assertIsNone(result["pagination"]["next_page"])
        self.assertFalse(result["pagination"]["native_next_button_enabled"])

    def test_german_range_and_umlauts_are_not_corrupted(self):
        result = m.parse_inventory(inventory(locale="de"), ORIGIN + "/de")
        self.assertEqual(23, result["source_result_count"])
        self.assertIn("Sekretärin", result["listings"][0]["title"])
        self.assertNotIn("Ã", result["listings"][0]["native_card_text"])

    def test_unknown_date_and_model_facts_remain_unsettled(self):
        row = m.parse_inventory(inventory(), BASE)["listings"][0]
        self.assertIsNone(row["original_published_at"])
        self.assertFalse(row["full_posting_reviewed"])
        self.assertIn("Employer model", row["native_card_text"])
        for key in ["employment_type", "remote", "student_eligible", "worker_countries"]:
            self.assertNotIn(key, row)

    def test_zero_requires_native_empty_signal_not_an_error_or_script_translation(self):
        self.assertEqual(0, m.parse_inventory(inventory(total=0), BASE)["returned_count"])
        for raw in [b'<html><body>Challenge</body></html>', b'<html><body><script>"0 jobs found"</script></body></html>']:
            with self.assertRaises(m.SourceError):
                m.parse_inventory(raw, BASE)

    def test_changed_total_is_not_a_valid_empty_terminal(self):
        with self.assertRaisesRegex(m.SourceError, "total_or_range"):
            m.parse_inventory(inventory(2, total=24), BASE, page=2, first_page_total=23)

    def test_reset_to_first_page_cannot_be_accepted_as_later_page(self):
        with self.assertRaises(m.SourceError):
            m.parse_inventory(inventory(1), BASE, page=2, first_page_total=23)

    def test_wrong_current_page_or_next_state_refused(self):
        for raw in [inventory().replace(b'aria-current="page">1', b'aria-current="page">2'),
                    inventory().replace(b'aria-label="Go to next page"', b'aria-label="Go to next page" disabled=""'),
                    inventory(3).replace(b' disabled=""', b'')]:
            with self.subTest(raw=raw), self.assertRaises(m.SourceError):
                m.parse_inventory(raw, BASE, page=3 if b'21-23' in raw else 1)

    def test_duplicate_missing_or_conflicting_card_does_not_reduce_supply(self):
        original = inventory()
        for raw in [original.replace(b'nativehandle0002', b'nativehandle0001'),
                    original.replace(b'<h3>Sekret\xc3\xa4rin 1</h3>', b'<h3>Different title</h3>'),
                    original.replace(b'1-10 out of 23', b'1-9 out of 23')]:
            with self.subTest(raw=raw), self.assertRaises(m.SourceError):
                m.parse_inventory(raw, BASE)

    def test_source_identity_excludes_locale_and_back_navigation_query(self):
        en = m.native_job_url(JOB + '?career_page_search=page%3D2', BASE)
        de = m.native_job_url(ORIGIN + '/de/job/' + HANDLE, ORIGIN + '/de')
        self.assertEqual(en[-1], de[-1])
        self.assertEqual(en[1], de[1])

    def test_foreign_or_encoded_application_links_cannot_be_job_inputs(self):
        for value in [JOB.replace('example.onlyfy.jobs', 'evil.test'), ORIGIN + '/application/apply/' + HANDLE,
                      JOB + '?token=secret', JOB + '#apply', JOB + '?career_page_search=query%3Dmarketing',
                      BASE + '/job/..%2fapplication']:
            with self.subTest(value=value), self.assertRaises(m.SourceError):
                m.native_job_url(value, BASE)

    def test_full_primary_body_never_uses_schema_summary_or_export_variant_as_requirements(self):
        result = m.parse_detail(shell(), full(), JOB)
        self.assertIn('Complete native tasks', result['description'])
        self.assertNotIn('Schema summary', result['description'])
        self.assertNotIn('Export-only', result['description'])
        self.assertIn('Export-only', result['native_body_variants'][0]['text'])
        self.assertFalse(result['schema_description_used_as_full_body'])
        self.assertFalse(result['native_body_variants'][0]['visible_or_requirement_verified'])
        self.assertIsNone(result['visible_description'])

    def test_full_source_clock_remote_and_opening_identifier_are_not_promoted(self):
        result = m.parse_detail(shell(), full(), JOB)
        self.assertIsNone(result['original_published_at'])
        self.assertEqual('2026-09-09', result['source_schema_date_posted'])
        self.assertEqual('TELECOMMUTE', result['native_job_posting']['jobLocationType'])
        self.assertEqual('different-opening-id', result['native_schema_identifier']['value'])
        self.assertEqual(ORIGIN + '::' + HANDLE, result['id'])
        self.assertFalse(result['full_posting_reviewed'])

    def test_missing_full_primary_body_or_wrong_title_refused(self):
        title_only = ('<html><body><div class="job-ad-component"><main class="main-element"><h1>'
                      + TITLE + '</h1></main></div></body></html>').encode()
        for value in [b'<html><body>Summary only</body></html>', full(title='Other posting'), title_only]:
            with self.subTest(value=value), self.assertRaises(m.SourceError):
                m.parse_detail(shell(), value, JOB)

    def test_native_apply_link_identity_checked_but_never_requested(self):
        with self.assertRaisesRegex(m.SourceError, 'posting_identity'):
            m.parse_detail(shell(), full().replace(('/application/apply/' + HANDLE).encode(), b'/application/apply/otherhandle'), JOB)
        transport = Transport()
        result = m.read(job_url=JOB, transport=transport)
        self.assertEqual(3, len(transport.calls))
        self.assertTrue(all('/application/' not in url and '/print/' not in url for url, _ in transport.calls))
        self.assertFalse(result['print_pdf_requested'])

    def test_summary_alone_never_promoted_to_body(self):
        with self.assertRaises(m.SourceError):
            m.parse_detail(shell(), shell(), JOB)

    def test_missing_or_wrong_print_contract_stops_before_frame_request(self):
        for bad in [shell().replace(b'data-testid="print"', b'data-testid="other"'),
                    shell().replace(('/candidate/job/print/' + HANDLE).encode(), b'/candidate/job/print/otherhandle')]:
            transport = Transport(shell_raw=bad)
            with self.subTest(bad=bad), self.assertRaises(m.SourceError):
                m.read(job_url=JOB, transport=transport)
            self.assertEqual(2, len(transport.calls))

    def test_metadata_first_page_uses_unfiltered_native_url(self):
        transport = Transport()
        m.read(board_url=BASE, transport=transport)
        self.assertEqual(BASE, transport.calls[-1][0])
        self.assertEqual(2, len(transport.calls))

    def test_native_continuation_uses_observed_page_parameter(self):
        transport = Transport(listing=inventory(2))
        m.read(board_url=BASE, page=2, first_page_total=23, transport=transport)
        self.assertEqual(BASE + '?page=2', transport.calls[-1][0])

    def test_missing_initial_total_or_outside_page_refused_before_network(self):
        for options in [dict(page=2), dict(page=4, first_page_total=23), dict(page=True),
                        dict(page=0), dict(first_page_total=True), dict(first_page_total=-1)]:
            transport = Transport()
            with self.subTest(options=options), self.assertRaises(m.SourceError):
                m.read(board_url=BASE, transport=transport, **options)
            self.assertEqual([], transport.calls)

    def test_robots_denied_stops_before_native_source(self):
        transport = Transport(robots='User-agent: *\nDisallow: /en\n')
        with self.assertRaisesRegex(m.SourceError, 'robots_denied'):
            m.read(board_url=BASE, transport=transport)
        self.assertEqual(1, len(transport.calls))

    def test_full_frame_denial_does_not_use_pdf_or_rewrite_viewer(self):
        transport = Transport(robots='User-agent: *\nDisallow: /job/show/\n')
        with self.assertRaisesRegex(m.SourceError, 'robots_denied'):
            m.read(job_url=JOB, transport=transport)
        self.assertEqual(2, len(transport.calls))

    def test_robots_errors_never_become_empty_inventory(self):
        for code in [403, 429, 500, 503]:
            transport = Transport(robots=code)
            with self.subTest(code=code), self.assertRaises(m.SourceError) as error:
                m.read(board_url=BASE, transport=transport)
            self.assertEqual(code, error.exception.http_status)
            self.assertEqual(1, len(transport.calls))

    def test_source_error_has_no_empty_job_fallback(self):
        transport = Transport(listing=m.SourceError('source_http_error', http_status=429, retry_after='30'))
        with self.assertRaises(m.SourceError) as caught:
            m.read(board_url=BASE, transport=transport)
        self.assertEqual('30', caught.exception.retry_after)
        self.assertEqual(2, len(transport.calls))

    def test_html_projection_keeps_unicode_and_does_not_execute_or_expose_script_text(self):
        result = m.parse_detail(shell(), full().replace(b'</main>', b'<script>DO_NOT_EXECUTE</script><style>hidden</style></main>'), JOB)
        self.assertIn('Sekretärin', result['description'])
        self.assertNotIn('DO_NOT_EXECUTE', result['description'])
        self.assertNotIn('hidden', result['description'])

    def test_pdf_bytes_or_invalid_unicode_not_html(self):
        for raw in [b'%PDF-1.4', b'\xff\xfe', b'']:
            with self.subTest(raw=raw), self.assertRaises(m.SourceError):
                m.document(raw)

    def test_strict_native_json_refuses_duplicate_and_nonfinite_values(self):
        for raw in ['{"x":1,"x":2}', '[NaN]', '[Infinity]', '[1e999]']:
            with self.subTest(raw=raw), self.assertRaises(m.SourceError):
                m.load_json(raw)

    def test_complete_http_bound_refuses_sliced_source_and_does_not_send_credentials(self):
        class Response:
            status, headers = 200, {'Content-Type': 'text/html'}
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, size): return b'x' * size
        class Opener:
            def open(self, request, timeout):
                self.request = request
                return Response()
        opener = Opener()
        with self.assertRaisesRegex(m.SourceError, 'exceeds_bound'):
            m.request(BASE, accept='text/html', bound=32, opener=opener)
        self.assertNotIn('Authorization', opener.request.headers)
        self.assertNotIn('Cookie', opener.request.headers)

    def test_http_retry_after_is_preserved(self):
        class Opener:
            def open(self, request, timeout): raise HTTPError(BASE, 429, 'limited', {'Retry-After': '60'}, None)
        with self.assertRaises(m.SourceError) as error:
            m.request(BASE, accept='text/html', opener=Opener())
        self.assertEqual('60', error.exception.retry_after)

    def test_capabilities_are_offline_and_scope_qualified(self):
        result = m.capabilities()
        self.assertTrue(result['seed_required'])
        self.assertEqual([], result['acquisition_filters'])
        self.assertEqual(10, result['native_page_size'])
        self.assertFalse(result['coverage_complete'])


if __name__ == '__main__':
    unittest.main()
