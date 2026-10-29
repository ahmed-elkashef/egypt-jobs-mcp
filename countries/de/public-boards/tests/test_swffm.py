"""Synthetic full-page, finite-directory, body-variant and no-viewer regressions."""

import importlib
import json
import sys
from pathlib import Path
from unittest import TestCase

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
s = importlib.import_module("swffm")
URL = s.ORIGIN + "/anzeige/123456-native-role"


def card(reference="123456"):
    return (
        '<div class="card job-list-item"><div class="mt-1 mb-2">Praktikum</div>'
        '<a href="/anzeige/'
        + reference
        + '-native-role">Native role</a><div class="card-subtitle">Native employer</div>'
        '<div class="card-footer"><div class="col-9">Münster</div><div class="col-3">29.10.2026</div></div></div>'
    )


def page(number=1, next_number=2, terminal=False):
    return (
        '<meta charset="utf-8"><main>'
        + card()
        + '<ul class="pagination"><li class="active"><span>'
        + str(number)
        + "</span></li>"
        + (
            '<li><a href="/stellenangebote/seite/' + str(next_number) + '">Next</a></li>'
            if not terminal
            else '<li class="disabled"><a href="/stellenangebote/">Next</a></li>'
        )
        + "</ul></main>"
    ).encode()


def body(pdf=False, alternative=True):
    posting = {
        "@type": "JobPosting",
        "title": "Native role",
        "description": "Independent schema full-time version.",
        "datePosted": "2026-10-29",
        "employmentType": "FULL_TIME",
    }
    content = (
        '<p class="d-none">Published alternative says working student; all requirements retained.</p>'
        if alternative
        else ""
    )
    content += '<a href="/fileadmin/source.pdf">PDF</a><div class="dw-pdf-iframe-container"><iframe src="/viewer?file=%2Ffileadmin%2Fsource.pdf"></iframe></div>'
    if not pdf:
        content = "<h3>Stellenbeschreibung</h3><p>Start immediately; all duties.</p><h3>Anforderungen</h3><p>Complete additional requirements.</p>"
    return (
        '<meta charset="utf-8"><script type="application/ld+json">'
        + json.dumps(posting)
        + "</script><main><h1>Native role</h1>"
        "<p>Anzeigen-Nr. 123456, veröffentlicht am 29.10.2026</p><dl><dt>Beginn:</dt><dd>26.04.2027</dd>"
        "<dt>Home-Office möglich:</dt><dd>Ja</dd></dl>"
        + content
        + "<script>DO_NOT_EMIT_SCRIPT</script></main>"
    ).encode()


class FrankfurtStudentPortalTests(TestCase):
    def test_whole_native_cards_and_actual_continuation_without_hesse_assumption(self):
        value = s.inventory(page(), s.ORIGIN + s.LIST_PATH)
        row = value["listings"][0]
        self.assertEqual(row["native_city"], "Münster")
        self.assertFalse(row["hesse_membership_verified"])
        self.assertEqual(row["source_publication_date"], "2026-10-29")
        self.assertIsNone(row["original_source_date"])
        self.assertEqual(value["pagination"]["next_url"], s.ORIGIN + "/stellenangebote/seite/2")

    def test_disabled_terminal_next_href_is_never_a_return_to_root(self):
        value = s.inventory(page(3, terminal=True), s.ORIGIN + "/stellenangebote/seite/3")
        self.assertIsNone(value["pagination"]["next_url"])
        self.assertEqual(value["pagination"]["native_page_links"], {})

    def test_wrong_active_page_gaps_empty_or_unreconciled_cards_fail(self):
        for content in [
            page(2, 3),
            page(1, 3),
            b"<main/>",
            page().replace(b"</main>", b'<a href="/anzeige/123457-native-role">Omitted</a></main>'),
        ]:
            with self.assertRaises(ValueError):
                s.inventory(content, s.ORIGIN + s.LIST_PATH)

    def test_queries_ajax_uploads_viewers_and_apply_are_not_supported_reads(self):
        for path in [
            s.LIST_PATH + "?q=marketing",
            "/systemseiten/ajaxlist/",
            "/fileadmin/source.pdf",
            "/viewer?file=%2Ffileadmin%2Fsource.pdf",
            "/apply",
            "/anzeige/123456-native-role?apply=1",
        ]:
            for operation in ["inventory", "detail"]:
                with self.subTest(path=path, operation=operation), self.assertRaises(ValueError):
                    s.checked_url(s.ORIGIN + path, operation)

    def test_home_featured_and_finite_employer_directory_are_not_vacancy_pages(self):
        root = (
            '<main><a href="/stellenangebote/">All ads</a><a href="/unternehmensprofile">Profiles</a>'
            + card()
            + "</main>"
        ).encode()
        value = s.inventory(root, s.ORIGIN + "/")
        self.assertEqual(value["kind"], "german_public_board_partition_catalogue")
        self.assertNotIn("listings", value)
        directory = s.inventory(
            b'<main><a href="/unternehmensprofile/detail/native-employer">Profile</a></main>',
            s.ORIGIN + "/unternehmensprofile",
        )
        self.assertEqual(directory["native_profile_reference_count"], 1)
        self.assertFalse(directory["complete_employer_census"])
        self.assertNotIn("returned_count", directory)

    def test_employer_profile_refs_are_context_not_complete_company_supply(self):
        value = s.inventory(
            ("<main><h1>Native employer</h1>" + card() + "</main>").encode(),
            s.ORIGIN + "/unternehmensprofile/detail/native-employer",
        )
        self.assertEqual(value["kind"], "german_public_board_employer_profile_context")
        self.assertEqual(len(value["native_job_references"]), 1)
        self.assertFalse(value["native_profile_job_references_are_complete_company_supply"])

    def test_full_native_body_and_conflicting_start_facts_are_both_retained(self):
        value = s.detail(body(), URL)
        self.assertIn("Start immediately", value["description"])
        self.assertIn(
            {"label": "Beginn", "value": "26.04.2027", "native_links": []}, value["native_facts"]
        )
        self.assertEqual(value["body_representation"], "native_visible_html_sections")
        self.assertIsNone(value["original_source_date"])
        self.assertNotIn("DO_NOT_EMIT", json.dumps(value))

    def test_published_html_pdf_text_is_separate_from_conflicting_schema_and_unverified_pdf(self):
        value = s.detail(body(pdf=True), URL)
        self.assertIn(
            "working student", value["native_body_fields"]["published_pdf_text_alternative"]
        )
        self.assertEqual(value["native_job_posting"]["employmentType"], "FULL_TIME")
        self.assertEqual(value["body_representation"], "native_published_pdf_text_alternative")
        self.assertFalse(value["native_pdf_verification_complete"])
        self.assertFalse(value["pdf_or_viewer_requested"])
        self.assertNotIn("<iframe", value["description_html"])

    def test_pdf_viewer_and_schema_without_published_full_text_do_not_become_body(self):
        with self.assertRaises(ValueError):
            s.detail(body(pdf=True, alternative=False), URL)

    def test_different_id_title_or_unpaired_facts_fail(self):
        for content in [
            body().replace(b"Anzeigen-Nr. 123456", b"Anzeigen-Nr. 654321"),
            body().replace(b"<h1>Native role</h1>", b"<h1>Other</h1>"),
            body().replace(b"<dt>Beginn:</dt>", b""),
        ]:
            with self.assertRaises(ValueError):
                s.detail(content, URL)
