import copy
import json
import unittest
from io import BytesIO
from urllib.error import HTTPError

import reader

BASE = "https://example.teamtailor.com"
GUID = "00000000-0000-4000-8000-000000000001"
URL = BASE + "/jobs/1234567-native-student-role"
BODY = "<p>Complete responsibilities.</p><p>All requirements and required documents.</p>"


def payload(value):
    return json.dumps(value).encode()


def manifest(count=1):
    return f'<html><head><link type="application/rss+xml" href="{BASE}/jobs.rss"></head><body><h2>{count} jobs</h2></body></html>'.encode()


def feed():
    return {"version": "https://jsonfeed.org/version/1.1", "feed_url": BASE + "/jobs.json", "home_page_url": BASE + "/jobs",
            "items": [{"id": GUID, "title": "Native student role", "url": URL,
                       "content_html": BODY, "date_published": "2026-10-28T18:26:40+01:00",
                       "_jobposting": {"@type": "JobPosting", "title": "Native student role", "description": BODY,
                                       "datePosted": "2026-10-28T18:26:40+01:00", "jobLocation": [{"address": {"addressCountry": "DE"}}]}}]}


def rss():
    return f'''<rss xmlns:tt="https://teamtailor.com/locations"><channel><link>{BASE}/jobs</link><item>
      <title>Native student role</title><link>{URL}</link><guid>{GUID}</guid>
      <description><![CDATA[{BODY}]]></description><pubDate>Wed, 28 Oct 2026 18:26:40 +0100</pubDate>
      <remoteStatus>none</remoteStatus><tt:department>Communications</tt:department><tt:role>Native role</tt:role>
      <tt:locations><tt:location><tt:name>Native office</tt:name><tt:city>Frankfurt</tt:city><tt:country>Germany</tt:country></tt:location></tt:locations>
      </item></channel></rss>'''.encode()


def catalogue():
    return {"linkset": [{"anchor": BASE + "/jobs", "service-desc": [{"href": BASE + "/jobs.json", "type": "application/feed+json"}]}]}


def transport_fixture(overrides=None):
    seen = []
    records = {"/robots.txt": b"User-agent: *\nDisallow: /account\nDisallow: /jobs/*/applications\n",
               "/jobs": manifest(), "/.well-known/api-catalog": payload(catalogue()),
               "/jobs.json": payload(feed()), "/jobs.rss": rss()}
    records.update(overrides or {})
    def get(url, **kwargs):
        path = url.removeprefix(BASE)
        seen.append((url, kwargs))
        body = records[path]
        if isinstance(body, Exception):
            raise body
        return {"body": body, "link": f'<{BASE}/.well-known/api-catalog>; rel="api-catalog"',
                "requested_at": "2026-10-29T10:00:00Z", "observed_at": "2026-10-29T10:00:01Z"}
    return get, seen


class TeamtailorTests(unittest.TestCase):
    def test_verified_vendor_and_explicit_custom_origins(self):
        for value in [BASE, BASE + "/", *reader.CUSTOM_ORIGINS]:
            self.assertEqual(reader.origin(value), value.rstrip("/"))

    def test_nonverified_account_auth_query_and_ambiguous_origins_stop_before_network(self):
        for value in [None, "http://example.teamtailor.com", "https://api.teamtailor.com", "https://example.teamtailor.com.evil.test",
                      "https://unverified.example", BASE + "/jobs", BASE + "?query=PR", BASE + "#x", " " + BASE,
                      BASE.replace("https://", "https://user:pass@"), BASE + ":443"]:
            with self.subTest(value=value), self.assertRaises(reader.SourceError):
                reader.read(value, transport=lambda *_a, **_kw: self.fail("unexpected network"))

    def test_full_published_protocol_uses_only_exact_public_get_routes(self):
        transport, seen = transport_fixture()
        result = reader.read(BASE, transport=transport)
        self.assertEqual([url for url, _ in seen], [BASE + p for p in ["/robots.txt", "/jobs", "/.well-known/api-catalog", "/jobs.json", "/jobs.rss"]])
        self.assertEqual(seen[0][1]["accept"], "text/plain")
        self.assertEqual(result["returned_count"], 1)
        self.assertTrue(result["native_count_reconciled"])
        self.assertTrue(all(p["method"] == "GET" for p in result["provenance"]))
        self.assertFalse(result["coverage_complete"])

    def test_complete_body_schema_rss_and_source_clock_variants_are_retained(self):
        result = reader.parse_feed(payload(feed()), rss(), manifest(), BASE)
        job = result["listings"][0]
        self.assertEqual(job["description"], "Complete responsibilities. All requirements and required documents.")
        self.assertEqual(job["description_html"], BODY)
        self.assertEqual(job["native_job_posting"]["description"], BODY)
        self.assertEqual(job["native_rss"]["description_html"], BODY)
        self.assertIsNone(job["original_published_at"])
        self.assertEqual(job["source_date_published"], "2026-10-28T18:26:40+01:00")
        self.assertEqual(job["native_rss"]["remote_status_raw"], "none")
        self.assertEqual(job["native_rss"]["locations"][0]["country"], "Germany")
        self.assertNotIn("worker_countries", job)
        self.assertFalse(job["full_posting_reviewed"])

    def test_conflicting_body_representations_are_preserved_not_silently_overwritten(self):
        data = feed()
        data["items"][0]["_jobposting"]["description"] = "<p>A different schema body.</p>"
        job = reader.parse_feed(payload(data), rss(), manifest(), BASE)["listings"][0]
        self.assertTrue(job["body_variants_differ"])
        self.assertEqual(job["description_html"], BODY)
        self.assertEqual(job["native_job_posting"]["description"], "<p>A different schema body.</p>")

    def test_current_count_difference_is_not_partial_success(self):
        for count in [0, 2]:
            with self.subTest(count=count), self.assertRaises(reader.SourceError):
                reader.parse_feed(payload(feed()), rss(), manifest(count), BASE)

    def test_unknown_native_ui_count_remains_unknown_without_inventing_empty_supply(self):
        page = manifest().replace(b"1 jobs", b"Open roles")
        result = reader.parse_feed(payload(feed()), rss(), page, BASE)
        self.assertEqual(result["returned_count"], 1)
        self.assertIsNone(result["source_result_count"])
        self.assertFalse(result["native_count_reconciled"])

    def test_empty_reported_feeds_differ_from_missing_items(self):
        data = feed()
        data["items"] = []
        xml = f"<rss><channel><link>{BASE}/jobs</link></channel></rss>".encode()
        result = reader.parse_feed(payload(data), xml, manifest(0), BASE)
        self.assertEqual(result["returned_count"], 0)
        del data["items"]
        with self.assertRaises(reader.SourceError):
            reader.parse_feed(payload(data), xml, manifest(0), BASE)

    def test_duplicate_source_ids_or_urls_are_not_dropped(self):
        data = feed()
        data["items"].append(copy.deepcopy(data["items"][0]))
        with self.assertRaises(reader.SourceError):
            reader.parse_feed(payload(data), rss(), manifest(2), BASE)

    def test_source_guid_title_schema_and_rss_identity_must_reconcile(self):
        for update in [{"id": "not-a-guid"}, {"title": "Wrong source title"}, {"_jobposting": {"@type": "NewsArticle"}},
                       {"url": "https://evil.test/jobs/1234567-native-student-role"}]:
            data = feed()
            data["items"][0].update(update)
            with self.subTest(update=update), self.assertRaises(reader.SourceError):
                reader.parse_feed(payload(data), rss(), manifest(), BASE)

    def test_unverified_native_continuation_is_refused_without_guessing_routes(self):
        data = feed()
        data["next_url"] = BASE + "/jobs.json?page=2"
        with self.assertRaises(reader.SourceError):
            reader.parse_feed(payload(data), rss(), manifest(), BASE)

    def test_exact_guid_detail_uses_full_feeds_and_does_not_request_an_apply_or_job_url(self):
        transport, seen = transport_fixture()
        result = reader.read(BASE, job_id=GUID, transport=transport)
        self.assertEqual(result["kind"], "teamtailor_native_detail")
        self.assertEqual(result["id"], BASE + "::" + GUID)
        self.assertEqual(result["description_html"], BODY)
        self.assertEqual(len(seen), 5)
        self.assertFalse(any("/jobs/" in url for url, _ in seen))

    def test_missing_guid_is_a_limitation_not_a_fabricated_posting(self):
        transport, _ = transport_fixture()
        with self.assertRaises(reader.SourceError):
            reader.read(BASE, job_id=GUID[:-1] + "2", transport=transport)

    def test_bad_detail_guid_is_refused_before_policy(self):
        with self.assertRaises(reader.SourceError):
            reader.read(BASE, job_id="/applications/new", transport=lambda *_a, **_kw: self.fail("unexpected network"))

    def test_unadvertised_catalogue_stops_before_machine_feed_requests(self):
        transport, seen = transport_fixture()
        def without_link(url, **kwargs):
            result = transport(url, **kwargs)
            result["link"] = ""
            return result
        with self.assertRaises(reader.SourceError):
            reader.read(BASE, transport=without_link)
        self.assertEqual(len(seen), 2)

    def test_wrong_anchor_or_foreign_feed_catalogue_is_refused(self):
        for change in ["anchor", "foreign"]:
            cat = catalogue()
            if change == "anchor":
                cat["linkset"][0]["anchor"] = BASE + "/account"
            else:
                cat["linkset"][0]["service-desc"][0]["href"] = "https://evil.test/jobs.json"
            transport, seen = transport_fixture({"/.well-known/api-catalog": payload(cat)})
            with self.subTest(change=change), self.assertRaises(reader.SourceError):
                reader.read(BASE, transport=transport)
            self.assertEqual(len(seen), 3)

    def test_unadvertised_rss_is_not_guessed_from_a_url_convention(self):
        transport, seen = transport_fixture({"/jobs": b"<html><body>1 jobs</body></html>"})
        with self.assertRaises(reader.SourceError):
            reader.read(BASE, transport=transport)
        self.assertEqual(len(seen), 3)

    def test_robots_denial_stops_before_site_or_feed_request(self):
        transport, seen = transport_fixture({"/robots.txt": b"User-agent: *\nDisallow: /jobs\n"})
        with self.assertRaises(reader.SourceError):
            reader.read(BASE, transport=transport)
        self.assertEqual(len(seen), 1)

    def test_missing_policy_differs_from_forbidden_or_unavailable_policy(self):
        for status in [404, 410, 403, 429, 503]:
            transport, seen = transport_fixture({"/robots.txt": reader.SourceError("native_http", http_status=status)})
            if status in [404, 410]:
                self.assertEqual(reader.read(BASE, transport=transport)["returned_count"], 1)
            else:
                with self.assertRaises(reader.SourceError):
                    reader.read(BASE, transport=transport)
                self.assertEqual(len(seen), 1)

    def test_challenge_policy_and_xml_entities_are_not_executed_or_accepted(self):
        transport, _ = transport_fixture({"/robots.txt": b"<!doctype html><html>Challenge</html>"})
        with self.assertRaises(reader.SourceError):
            reader.read(BASE, transport=transport)
        with self.assertRaises(reader.SourceError):
            reader.rss_items(b'<!DOCTYPE rss [<!ENTITY external SYSTEM "file:///etc/passwd">]><rss/>', BASE)

    def test_duplicate_nonfinite_and_malformed_json_are_not_silently_parsed(self):
        for raw in [b'{"items":[],"items":[]}', b'{"n":NaN}', b'not JSON', b'[]']:
            with self.subTest(raw=raw), self.assertRaises(reader.SourceError):
                reader.load_json(raw)

    def test_encoded_apply_and_foreign_links_fail_before_becoming_candidate_urls(self):
        for url in [URL + "/applications/new", URL + "?apply=1", URL + "#form", URL + "%2fapplications%2fnew",
                    URL + "%252fapplications", "https://elsewhere.test/jobs/123-role"]:
            with self.subTest(url=url), self.assertRaises(reader.SourceError):
                reader.native_job_url(url, BASE)

    def test_transport_keeps_http_limits_without_cookies_credentials_or_redirects(self):
        class Opener:
            def open(self, req, timeout):
                self.req = req
                raise HTTPError(req.full_url, 429, "limited", {"Retry-After": "60"}, BytesIO())
        opener = Opener()
        with self.assertRaises(reader.SourceError) as failure:
            reader.request(BASE + "/jobs.json", accept="application/feed+json", opener=opener)
        self.assertEqual(failure.exception.http_status, 429)
        self.assertEqual(failure.exception.retry_after, "60")
        self.assertEqual(opener.req.method if hasattr(opener.req, "method") else opener.req.get_method(), "GET")
        self.assertNotIn("Cookie", opener.req.headers)
        self.assertNotIn("Authorization", opener.req.headers)
        self.assertIsNone(reader.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test"))

    def test_incomplete_markup_and_oversized_transport_never_become_truncated_success(self):
        with self.assertRaises(reader.SourceError):
            reader.native_manifest(b"", BASE)
        class Response:
            status = 200
            headers = {}
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
            reader.request(BASE + "/jobs.json", accept="application/feed+json", bound=10, opener=Opener())


if __name__ == "__main__":
    unittest.main()
