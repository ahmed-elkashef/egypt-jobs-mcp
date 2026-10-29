"""Synthetic objective acquisition, complete body, clocks and access regressions."""

import copy
import importlib
import json
import sys
from pathlib import Path
from unittest import TestCase, mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
g = importlib.import_module("getinengineering")
z = importlib.import_module("zenjob")
r = importlib.import_module("readers")
GURL = g.ORIGIN + "/jobsuche/p123456"
ZID = "12345678-1234-4234-8234-123456789abc"
ZURL = z.ORIGIN + "/de/jobboerse/jobs/native-shift-" + ZID


def bootstrap(props):
    return (
        '<script id="__NEXT_DATA__">'
        + json.dumps({"props": props}).replace("<", r"\u003c")
        + "</script>"
    )


def g_jobs(start=0, count=39):
    return [
        {
            "id": 123456 + start + index,
            "url": "/jobsuche/p" + str(123456 + start + index),
            "title": "Native role",
            "homeOffice": True,
            "careers": [],
            "locations": [{"name": "Native city"}],
            "company": {"title": "Native employer", "logoUrl": "DO_NOT_EMIT_LOGO"},
            "jobSearchDebug": "DO_NOT_EMIT_DEBUG",
        }
        for index in range(count)
    ]


def g_ssr(jobs=None, narrowed=False):
    jobs = g_jobs() if jobs is None else jobs
    filters = {
        key: []
        for key in (
            "company",
            "degree",
            "studySubject",
            "thematicPriority",
            "city",
            "state",
            "homeOffice",
        )
    }
    filters["radius"] = 25
    if narrowed:
        filters["studySubject"] = [1]
    props = {
        "pageProps": {"pageProps": {"start": 0, "isDebug": False, "filters": filters}},
        "initialState": {
            "jobSearchJobs": {"jobs": jobs, "jobsCount": 100, "loading": False, "errorCode": 0},
            "userStatus": {"secret": "DO_NOT_EMIT_USER"},
        },
    }
    return (
        bootstrap(props) + "".join('<a data-job-id="' + str(job["id"]) + '"></a>' for job in jobs)
    ).encode()


def g_body(preview=False):
    content = '<section data-section-id="a"><h2>Tasks</h2><p>Every duty.</p></section><section data-section-id="b"><h2>Requirements</h2><p>Required qualification beyond snippet.</p></section>'
    job = {
        "id": 123456,
        "preview": preview,
        "publishState": "published",
        "content": content,
        "header": {
            "title": "Native role",
            "companyName": "Native employer",
            "locations": ["Native city"],
            "applyUrl": "DO_NOT_EMIT_APPLY_TOKEN",
        },
        "jobInfo": {"degrees": ["Master"]},
        "trackingPageViewData": "DO_NOT_EMIT_TRACKING",
    }
    props = {
        "initialState": {
            "jobJob": {"loading": False, "job": job},
            "userStatus": {"private": "DO_NOT_EMIT_USER"},
        }
    }
    posting = {
        "@type": "JobPosting",
        "url": GURL,
        "datePosted": "2026-10-20T00:00:00+02:00",
        "employmentType": "FULL_TIME",
    }
    return (
        bootstrap(props)
        + '<script type="application/ld+json">'
        + json.dumps(posting)
        + "</script>"
        + content
    ).encode()


def z_card(reference=ZID):
    return (
        '<a href="/de/jobboerse/jobs/native-shift-' + reference + '"><h2>80 EUR</h2><p>20 EUR/h</p>'
        '<h2>Native shift</h2><p>Native city</p><time datetime="2026-10-30T02:00:00Z">Tomorrow</time></a>'
    )


def z_page(page=1, next_page=2):
    return (
        '<main><select id="city-filter"><option value="">All</option></select><select id="category-filter"><option value="">All</option></select>'
        + z_card()
        + '<a class="bg-surface-quaternary" href="?page='
        + str(page)
        + '">'
        + str(page)
        + "</a>"
        + ('<a href="?page=' + str(next_page) + '">Next</a>' if next_page else "")
        + "</main>"
    ).encode()


def z_body(reference=ZID, notes=True):
    posting = {
        "@type": "JobPosting",
        "identifier": {"value": reference},
        "title": "Native shift",
        "description": "Main duties only.",
        "datePosted": "2026-10-19",
        "validThrough": "2026-10-30",
        "employmentType": "PART_TIME",
        "url": z.ORIGIN + "/de/jobboerse/native-shift-" + reference,
    }
    return (
        '<main><script type="application/ld+json">'
        + json.dumps(posting)
        + "</script><h1>Native shift</h1>"
        '<time datetime="2026-10-30T02:00:00Z">Tomorrow</time><h2>Beschreibung</h2><p>Main duties only.</p>'
        + (
            "<h2>Anforderungen &amp; Hinweise</h2><p>The shift may run longer. Safety condition beyond schema.</p>"
            if notes
            else ""
        )
        + "<script>DO_NOT_EMIT_SCRIPT</script></main>"
    ).encode()


class EngineeringTests(TestCase):
    def test_every_native_ssr_card_and_verified_api_continuation(self):
        result = g.inventory(g_ssr(), g.ORIGIN + "/jobsuche")
        self.assertEqual(result["returned_count"], 39)
        self.assertEqual(
            result["pagination"]["next_url"], g.ORIGIN + g.API_PATH + "?start=39&limit=39"
        )
        self.assertNotIn("DO_NOT_EMIT", json.dumps(result))
        self.assertIsNone(result["listings"][0]["original_source_date"])
        self.assertFalse(result["listings"][0]["germany_remote_eligibility_verified"])

    def test_native_api_offsets_are_counts_not_ssr_query_pages(self):
        url = g.ORIGIN + g.API_PATH + "?start=39&limit=39"
        result = g.inventory(
            json.dumps({"items": {"results": g_jobs(39)}, "total": 100}).encode(), url
        )
        self.assertEqual(
            result["pagination"]["next_url"], g.ORIGIN + g.API_PATH + "?start=78&limit=39"
        )
        self.assertFalse(result["pagination"]["native_request_offset_echo_present"])
        with self.assertRaises(ValueError):
            g.checked_url(g.ORIGIN + "/jobsuche?start=39", "inventory")

    def test_role_degree_restricted_and_unknown_queries_refused(self):
        for suffix in [
            "/jobsuche?degree=1",
            "/jobsuche?q=marketing",
            g.API_PATH + "?start=1&limit=39",
            g.API_PATH + "?start=0&limit=39&filter%5Bdegree%5D=1",
            "/api/v2/restricted/job/search",
            "/mein-account",
        ]:
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                g.checked_url(g.ORIGIN + suffix, "inventory")
        with self.assertRaises(ValueError):
            g.inventory(g_ssr(narrowed=True), g.ORIGIN + "/jobsuche")

    def test_missing_partial_duplicate_and_false_total_never_empty_success(self):
        for count, total in [(0, 0), (38, 100), (39, 38), (39, True)]:
            with self.subTest(count=count, total=total), self.assertRaises(ValueError):
                g.inventory(
                    json.dumps(
                        {"items": {"results": g_jobs(count=count)}, "total": total}
                    ).encode(),
                    g.ORIGIN + g.API_PATH + "?start=0&limit=39",
                )
        jobs = g_jobs()
        jobs[-1] = copy.deepcopy(jobs[0])
        with self.assertRaises(ValueError):
            g.inventory(g_ssr(jobs), g.ORIGIN + "/jobsuche")

    def test_complete_body_visible_requirements_and_independent_schema(self):
        result = g.detail(g_body(), GURL)
        self.assertIn("Required qualification beyond snippet.", result["description"])
        self.assertNotIn("DO_NOT_EMIT", json.dumps(result))
        self.assertEqual(result["source_schema_date_posted"], "2026-10-20T00:00:00+02:00")
        self.assertIsNone(result["original_source_date"])
        self.assertTrue(result["source_body_untruncated"])

    def test_preview_missing_or_changed_visible_sections_fail(self):
        for body in [
            g_body(preview=True),
            g_body().replace(
                b"<p>Required qualification beyond snippet.</p></section>",
                b"<p>Changed visible.</p></section>",
            ),
        ]:
            with self.assertRaises(ValueError):
                g.detail(body, GURL)

    def test_published_open_protocol_header_only_on_that_get_path(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"{}"
        response.geturl.return_value = g.ORIGIN + g.API_PATH + "?start=0&limit=39"
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch.object(r, "build_opener", return_value=opener):
            r.fetch("getinengineering", response.geturl.return_value, "inventory")
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("X-requested-with"), "XMLHttpRequest")
        self.assertIsNone(request.get_header("Cookie"))
        self.assertIsNone(request.get_header("Authorization"))


class ZenjobTests(TestCase):
    def test_complete_native_shift_page_and_actual_continuation(self):
        result = z.inventory(z_page(), z.ORIGIN + z.LIST_PATH)
        row = result["listings"][0]
        self.assertEqual(row["native_shift_start"], "2026-10-30T02:00:00Z")
        self.assertIsNone(row["original_source_date"])
        self.assertFalse(row["working_student_contract_verified"])
        self.assertEqual(result["pagination"]["next_url"], z.ORIGIN + z.LIST_PATH + "?page=2")

    def test_native_page_mismatch_gap_duplicate_and_empty_fail(self):
        for body in [
            z_page(2, 3),
            z_page(1, 3),
            z_page().replace(b"</main>", z_card().encode() + b"</main>"),
            b"<main/>",
        ]:
            with self.assertRaises(ValueError):
                z.inventory(body, z.ORIGIN + z.LIST_PATH)

    def test_unknown_filter_signup_and_application_paths_refused(self):
        for suffix in [
            z.LIST_PATH + "?q=marketing",
            z.LIST_PATH + "?page=1&page=2",
            "/de/jobs/anmeldung/",
            "/signup",
            "/de/jobboerse?city=FRANKFURT",
        ]:
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                z.checked_url(z.ORIGIN + suffix, "inventory")
        with self.assertRaises(ValueError):
            z.inventory(
                z_page().replace(
                    b'<option value="">All</option>', b'<option value="CITY" selected>City</option>'
                ),
                z.ORIGIN + z.LIST_PATH,
            )

    def test_whole_body_retains_separate_notes_beyond_structured_description(self):
        result = z.detail(z_body(), ZURL)
        self.assertIn("Safety condition beyond schema", result["description"])
        self.assertNotIn("DO_NOT_EMIT", json.dumps(result))
        self.assertIsNone(result["original_source_date"])
        self.assertEqual(result["source_schema_date_posted"], "2026-10-19")
        self.assertFalse(result["native_schema_url_matches_requested_route"])
        self.assertFalse(result["working_student_contract_verified"])

    def test_missing_notes_wrong_uuid_or_title_not_complete_body(self):
        for body in [
            z_body(notes=False),
            z_body(reference="87654321-1234-4234-8234-123456789abc"),
            z_body().replace(b"<h1>Native shift</h1>", b"<h1>Wrong shift</h1>"),
        ]:
            with self.assertRaises(ValueError):
                z.detail(body, ZURL)
