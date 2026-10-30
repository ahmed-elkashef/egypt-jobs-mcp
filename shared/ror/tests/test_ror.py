"""Synthetic source contracts; no provider reads or copied source implementation."""
import copy
import hashlib
import io
import json
import tempfile
import unittest
import zipfile

import ror

RID = "23500708"
STEM = "v2.0-2026-01-01-ror-data"


def record(suffix, countries, status="active", types=None):
    return {"id": "https://ror.org/01234567" + suffix, "admin": {"created": {"date": "2020-01-01"}},
            "domains": [], "established": None, "external_ids": [], "links": [{"type": "website", "value": "https://example.org/"}],
            "locations": [{"geonames_id": i, "geonames_details": {"country_code": code, "country_name": code, "lat": 1.5, "lng": 2.5}} for i, code in enumerate(countries)],
            "names": [{"lang": "de", "types": ["ror_display"], "value": "Synthetic Öffentlich"}, {"lang": None, "types": ["alias"], "value": "Historical name"}],
            "relationships": [{"type": "Related", "id": "https://ror.org/123456789", "label": "Source relation"}], "status": status, "types": types or ["education"]}


def data():
    return [record("8", ["DE"]), record("9", ["EG"], "inactive", ["company", "nonprofit"]),
            record("a", ["DE", "EG"], "withdrawn", ["government"]), record("b", ["US"])]


def archive(rows=None, *, extra=False, duplicate=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(STEM + ".json", json.dumps(rows if rows is not None else data(), ensure_ascii=False))
        z.writestr(STEM + ".csv", "id,name\nsynthetic,fixture\n")
        if extra:
            z.writestr("../unsafe", "no")
        if duplicate:
            z.writestr(STEM + ".json", "[]")
    return buffer.getvalue()


def page(raw, *, count=4, rid=RID):
    url = ror.record_url(rid)
    return (f'<!doctype html><html><head><title>ROR Data | Zenodo</title><link rel="canonical" href="{url}"><meta property="og:url" content="{url}"></head>'
            f'<body><main><h1>ROR Data</h1><p>Release v2.0 contains ROR IDs and metadata for {count} research organizations</p>'
            f'<p>md5:{hashlib.md5(raw).hexdigest()}</p><a href="{url}/files/{STEM}.zip?download=1">Download</a>'
            '<a href="https://creativecommons.org/publicdomain/zero/1.0">CC0</a>'
            '<a href="https://creativecommons.org/licenses/by/4.0">GeoNames attribution</a>'
            '<script>hidden nonce</script><form><input value="token"><button>Action</button></form>'
            '</main></body></html>').encode()


class FakeClient:
    def __init__(self, raw=None, response=None):
        self.raw, self.get_count, self.urls, self.response = raw or archive(), 0, [], response

    def get(self, url, **kwargs):
        self.get_count += 1
        self.urls.append((url, kwargs))
        if self.response is not None:
            return self.response
        return {"body": self.raw if kwargs.get("archive") else page(self.raw),
                "content_type": "application/octet-stream" if kwargs.get("archive") else "text/html; charset=utf-8"}


class RorContracts(unittest.TestCase):
    def setUp(self):
        self.raw = archive()
        self.meta = ror.metadata(page(self.raw), RID)

    def test_complete_native_metadata_and_attribution(self):
        self.assertEqual((self.meta["version"], self.meta["declared_dataset_records"]), ("2.0", 4))
        self.assertIn("https://creativecommons.org/licenses/by/4.0", self.meta["native_license_references"])
        self.assertNotIn("hidden nonce", self.meta["native_public_record_text"])
        self.assertFalse(self.meta["coverage_complete"])

    def test_explicit_utf8_before_html_preserves_unicode(self):
        raw = page(self.raw).replace(b"ROR Data</h1>", "ROR Data Öffentlich</h1>".encode())
        self.assertIn("Öffentlich", ror.metadata(raw, RID)["native_public_record_text"])
        with self.assertRaises(ror.SourceError):
            ror.metadata(raw.replace("Ö".encode(), b"\xff"), RID)

    def test_incomplete_or_unqualified_encoding_refused(self):
        for raw, content in [(page(self.raw)[:-8], "text/html; charset=utf-8"), (page(self.raw), "text/html"), (page(self.raw), "application/json")]:
            with self.subTest(content=content), self.assertRaises(ror.SourceError):
                ror.metadata(raw, RID, content)

    def test_canonical_and_og_must_reconcile_exact_record(self):
        for old in [b'rel="canonical"', b'property="og:url"']:
            with self.subTest(old=old), self.assertRaises(ror.SourceError):
                ror.metadata(page(self.raw).replace(old, b'property="other"'), RID)

    def test_archive_file_record_and_version_must_match(self):
        for old, new in [(b"/files/v2.0", b"/files/v3.0"), (b"/records/23500708/files/", b"/records/23500709/files/")]:
            with self.subTest(new=new), self.assertRaises(ror.SourceError):
                ror.metadata(page(self.raw).replace(old, new), RID)

    def test_ambiguous_checksum_or_release_count_refused(self):
        for addition in ["md5:" + "0" * 32, "Release v2.0 contains ROR IDs and metadata for 4 research organizations"]:
            with self.subTest(addition=addition), self.assertRaises(ror.SourceError):
                ror.metadata(page(self.raw).replace(b"</main>", addition.encode() + b"</main>"), RID)

    def test_api_off_origin_credentials_queries_and_fragments_refused(self):
        for url in ["https://zenodo.org/api/records/6347574", "https://evil.invalid/records/23500708", "https://x@zenodo.org/records/23500708", ror.record_url(RID) + "?x=1", ror.record_url(RID) + "#x"]:
            with self.subTest(url=url), self.assertRaises(ror.SourceError):
                ror.checked_url(url)

    def test_concept_resolution_retains_wait_without_follow(self):
        client = FakeClient(response={"http_status": 302, "location": "/records/23500708", "retry_after": "60"})
        result = ror.release(client=client)
        self.assertEqual((result["resolved_record_id"], result["retry_after_seconds"], result["redirects_followed"]), (RID, 60, 0))
        self.assertEqual(client.get_count, 1)
        self.assertEqual(result["next_request"], {"record_id": RID})

    def test_redirect_target_or_retry_header_ambiguity_refused(self):
        for location, retry in [("https://evil.invalid/records/23500708", "60"), ("/api/records/23500708", "60"), ("/records/6347574", "60"), ("/records/23500708", "later")]:
            with self.subTest(location=location, retry=retry), self.assertRaises(ror.SourceError):
                ror.release(client=FakeClient(response={"http_status": 302, "location": location, "retry_after": retry}))

    def test_policy_precedes_exact_record_and_archive_no_api(self):
        seen = []
        def transport(url, **kwargs):
            seen.append((url, kwargs))
            if url.endswith("/robots.txt"):
                return {"body": b"User-agent: *\nDisallow: /api/\nAllow: /records/\n", "content_type": "text/plain"}
            return {"body": page(self.raw), "content_type": "text/html; charset=utf-8"}
        result = ror.release(RID, client=ror.Client(transport))
        self.assertEqual(result["native_GET_requests"], 2)
        self.assertEqual([r[0] for r in seen], [ror.ORIGIN + "/robots.txt", ror.record_url(RID)])
        self.assertEqual(seen[1][1]["agent"], ror.AGENT)

    def test_policy_denial_requests_no_content(self):
        seen = []
        def transport(url, **kwargs):
            seen.append(url)
            return {"body": b"User-agent: *\nDisallow: /records/\n", "content_type": "text/plain"}
        with self.assertRaises(ror.SourceError):
            ror.release(RID, client=ror.Client(transport))
        self.assertEqual(seen, [ror.ORIGIN + "/robots.txt"])

    def test_archive_complete_count_unique_ids_and_all_country_memberships(self):
        result = ror.archive_records(self.raw, self.meta)
        self.assertEqual(result["dataset_records"], 4)
        self.assertEqual({k: len(v) for k, v in result["country_records"].items()}, {"DE": 2, "EG": 2})
        self.assertEqual(result["status_counts"], {"active": 2, "inactive": 1, "withdrawn": 1})

    def test_native_fields_status_types_aliases_and_relationships_preserved(self):
        result = ror.archive_records(self.raw, self.meta)
        self.assertEqual(result["country_records"]["EG"][0], {"native_array_index": 1, "record": data()[1]})
        self.assertEqual(result["country_records"]["DE"][1]["record"], data()[2])

    def test_checksum_mismatch_and_not_zip_refused(self):
        for raw in [b"<html>challenge</html>", self.raw + b"changed"]:
            with self.subTest(raw=raw[:12]), self.assertRaises(ror.SourceError):
                ror.archive_records(raw, self.meta)

    def test_extra_or_traversing_archive_members_refused(self):
        raw = archive(extra=True)
        with self.assertRaises(ror.SourceError):
            ror.archive_records(raw, ror.metadata(page(raw), RID))

    def test_declared_full_dataset_count_must_match(self):
        meta = copy.deepcopy(self.meta)
        meta["declared_dataset_records"] = 5
        with self.assertRaises(ror.SourceError):
            ror.archive_records(self.raw, meta)

    def test_duplicate_ids_not_deduplicated_as_complete(self):
        rows = data()
        rows[1]["id"] = rows[0]["id"]
        raw = archive(rows)
        with self.assertRaises(ror.SourceError):
            ror.archive_records(raw, ror.metadata(page(raw), RID))

    def test_missing_country_not_silently_excluded(self):
        rows = data()
        del rows[3]["locations"][0]["geonames_details"]["country_code"]
        raw = archive(rows)
        with self.assertRaises(ror.SourceError):
            ror.archive_records(raw, ror.metadata(page(raw), RID))

    def test_unknown_status_or_type_refused(self):
        for key, value in [("status", "hiring"), ("types", ["vacancy"])]:
            rows = data()
            rows[0][key] = value
            raw = archive(rows)
            with self.subTest(key=key), self.assertRaises(ror.SourceError):
                ror.archive_records(raw, ror.metadata(page(raw), RID))

    def test_cold_then_cached_country_segments_zero_further_provider_reads(self):
        with tempfile.TemporaryDirectory() as root:
            client = FakeClient()
            first = ror.directory(RID, "DE", limit=1, client=client, cache_root=root)
            self.assertEqual(client.get_count, 2)
            self.assertFalse(first["cache_hit"])
            cached = FakeClient()
            following = dict(first["next_request"])
            following["rid"] = following.pop("record_id")
            second = ror.directory(**following, client=cached, cache_root=root)
            self.assertEqual(second["native_GET_requests"], 0)
            self.assertIsNone(second["next_request"])
            self.assertEqual(second["organization_count"], 1)
            self.assertFalse(second["coverage_complete"])
            self.assertIsNone(second["vacancy_count"])
            egypt = ror.directory(RID, "EG", client=cached, cache_root=root)
            self.assertEqual(egypt["organization_count"], 2)
            self.assertEqual(cached.get_count, 0)

    def test_missing_snapshot_wrong_digest_and_outside_offsets_refused(self):
        with tempfile.TemporaryDirectory() as root:
            first = ror.directory(RID, "DE", client=FakeClient(), cache_root=root)
            for offset, digest in [(1, None), (1, "0" * 64), (2, first["snapshot_sha256"])]:
                with self.subTest(offset=offset, digest=digest), self.assertRaises(ror.SourceError):
                    ror.directory(RID, "DE", offset=offset, snapshot_sha256=digest, client=FakeClient(), cache_root=root)

    def test_country_projection_corruption_refused_without_refetch(self):
        with tempfile.TemporaryDirectory() as root:
            ror.directory(RID, "DE", client=FakeClient(), cache_root=root)
            folder = ror.cache_folder(RID, root)
            (folder / "DE.json").write_text("[]")
            client = FakeClient()
            with self.assertRaises(ror.SourceError):
                ror.directory(RID, "DE", client=client, cache_root=root)
            self.assertEqual(client.get_count, 0)

    def test_manifest_corruption_refused_without_refetch(self):
        with tempfile.TemporaryDirectory() as root:
            ror.directory(RID, "DE", client=FakeClient(), cache_root=root)
            (ror.cache_folder(RID, root) / "manifest.json").write_text("{}")
            client = FakeClient()
            with self.assertRaises(ror.SourceError):
                ror.directory(RID, "DE", client=client, cache_root=root)
            self.assertEqual(client.get_count, 0)

    def test_active_cache_lease_refuses_duplicate_download(self):
        with tempfile.TemporaryDirectory() as root:
            (ror.cache_folder(RID, root) / "building.json").write_text("{}")
            client = FakeClient()
            with self.assertRaises(ror.SourceError):
                ror.directory(RID, "DE", client=client, cache_root=root)
            self.assertEqual(client.get_count, 0)

    def test_directory_has_no_original_job_or_hiring_promotions(self):
        with tempfile.TemporaryDirectory() as root:
            result = ror.directory(RID, "DE", client=FakeClient(), cache_root=root)
            self.assertEqual(result["kind"], "organisation_directory")
            for field in ["coverage_complete", "reviewed_by_model", "full_posting_reviewed", "source_active_vacancy_verified", "legal_employer_or_job_worksite_verified"]:
                self.assertFalse(result[field])
            self.assertIsNone(result["original_published_at"])
            self.assertIsNone(result["source_result_count"])


if __name__ == "__main__":
    unittest.main()
