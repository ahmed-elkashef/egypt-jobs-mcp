"""Synthetic native scope, pagination, complete-content and identity regressions."""
import json
import unittest

from berlin import (
    FILTER,
    ORIGIN,
    SOURCE,
    checked_url,
    detail,
    inventory,
    inventory_uri,
    parse_detail,
    parse_inventory,
)
from network import Response, SourceError

URL = ORIGIN + "/Student-role-de-j1.html"


def page(scope="all", start=0, total=5, n=2):
    selected = ' selected="selected"' if scope == "student_entry" else ""
    rows = "".join(f'<tr><td><a href="/Student-role-de-j{i}.html">Student &amp; role {i}</a></td><td>Office {i}</td><td>E6</td><td>01.01.2020</td><td>31.12.2030</td></tr>' for i in range(start + 1, start + n + 1))
    href = inventory_uri(scope, start)
    current = f'<li class="nav_item stellen_navi_sel"><a href="{href}">{start//2+1}</a></li>'
    following = ""
    if start + n < total:
        following = f'<li><a href="{inventory_uri(scope,start+n)}">{start//2+2}</a></li><li><a href="{inventory_uri("all",start+n)}">weiter</a></li>'
    return f'''<html><head><meta charset="utf-8"></head><body><div id="jobslisting"><h1>Stellensuche</h1><select name="{FILTER}"><option value="28"{selected}>Praktikum/Werkstudierende</option></select><h2 class="number_jobs">{total} Stellenangebote gefunden</h2><table id="joboffers"><thead><tr><th>Stellenbezeichnung</th><th>Behörde/Einrichtung</th><th>Entgeltgruppe/Besoldungsgruppe</th><th>Veröffentlicht</th><th>Bewerbungsfrist</th></tr></thead><tbody>{rows}</tbody></table><ul id="joblist_navigator">{current}<li><a href="javascript:void(0);">...</a></li>{following}</ul></div></body></html>'''.encode()


def advert():
    schema = json.dumps({"@type": "JobPosting", "title": "Separate schema title", "description": "Separate schema requirements", "datePosted": "2020-01-01"})
    return f'''<html><head><link rel="canonical" href="{URL}"><meta property="og:url" content="{URL}"><script type="application/ld+json">{schema}</script></head><body><div id="jobTplContainer"><h1>Student role</h1><p>Bonn; header deadline31December2030</p><div>All introduction and tasks with body-only clause and different deadline30December2030.</div><p>Full requirements and conditions.</p><img src="https://example.invalid/picture.png" alt="Graphic explanation"><a href="https://employer.example/Native-role-de-j9.html">Employer original</a><a href="/profile.pdf">Profile document</a><a href="/apply">Apply</a><script>privateState='not-exported'</script><form><input name="csrf" value="secret"></form></div></body></html>'''.encode()


class BerlinContracts(unittest.TestCase):
    def test_initial_all_rows_and_unknown_original_clocks(self):
        d = parse_inventory(page())
        self.assertEqual(d["returned_count"], 2)
        self.assertEqual(d["source_result_count"], 5)
        self.assertEqual(d["metadata"][0]["title"], "Student & role 1")
        self.assertIsNone(d["metadata"][0]["original_published_at"])
        self.assertEqual(d["metadata"][0]["native_published_label"], "01.01.2020")

    def test_student_entry_is_native_selected_scope_not_model_verdict(self):
        d = parse_inventory(page("student_entry"), "student_entry")
        self.assertEqual(d["native_scope"]["scope"], "student_entry")
        self.assertFalse(d["all_source_or_student_models_reviewed"])

    def test_numbered_next_preserves_scope_while_weiter_drops_it(self):
        d = parse_inventory(page("student_entry"), "student_entry")
        self.assertEqual(d["next_request"], {"provider": "berlin", "scope": "student_entry", "start": 2, "first_page_total": 5})
        self.assertIn("filter", d["next_url"])
        self.assertTrue(all(x["scope"] == "student_entry" for x in d["native_numbered_paging_links"]))
        self.assertFalse(d["native_other_paging_links"][0]["retains_scope"])

    def test_continuation_retains_initial_total(self):
        d = parse_inventory(page(start=2), "all", 2, first_page_total=5)
        self.assertEqual(d["next_request"]["first_page_total"], 5)
        self.assertEqual(d["metadata"][0]["id"], SOURCE + "::3")

    def test_final_unequal_row_count_has_no_fake_continuation(self):
        d = parse_inventory(page(start=4, n=1), "all", 4, first_page_total=5)
        self.assertFalse(d["has_more"])
        self.assertIsNone(d["next_request"])

    def test_changed_native_total_is_not_silently_complete(self):
        with self.assertRaises(SourceError):
            parse_inventory(page(start=2, total=6), "all", 2, first_page_total=5)

    def test_scope_loss_refuses_before_rows(self):
        with self.assertRaises(SourceError):
            parse_inventory(page(), "student_entry")

    def test_selected_offset_cannot_reset_to_first_page(self):
        with self.assertRaises(SourceError):
            parse_inventory(page(), "all", 2, first_page_total=5)

    def test_missing_native_row_field_is_not_a_complete_page(self):
        with self.assertRaises(SourceError):
            parse_inventory(page().replace(b"<td>E6</td>", b"<td></td>", 1))

    def test_duplicate_job_ids_refuse(self):
        with self.assertRaises(SourceError):
            parse_inventory(page().replace(b"role-de-j2.html", b"role-de-j1.html"))

    def test_clipped_document_cannot_report_empty_or_success(self):
        with self.assertRaises(SourceError):
            parse_inventory(page()[:-7])
        with self.assertRaises(SourceError):
            parse_detail(advert()[:-7], URL)

    def test_native_column_contract_is_checked(self):
        with self.assertRaises(SourceError):
            parse_inventory(page().replace(b"Ver\xc3\xb6ffentlicht", b"Other"))

    def test_unqualified_empty_format_is_never_zero_supply(self):
        with self.assertRaises(SourceError):
            parse_inventory(page(total=0, n=0))
        with self.assertRaises(SourceError):
            parse_inventory(b"<html><body>Login</body></html>")

    def test_missing_numbered_continuation_does_not_fall_back_to_weiter(self):
        p = page("student_entry").replace(b">2</a>", b">next</a>")
        with self.assertRaises(SourceError):
            parse_inventory(p, "student_entry")

    def test_native_next_offset_must_follow_all_current_rows(self):
        p = page().replace(b"start=2", b"start=3")
        with self.assertRaises(SourceError):
            parse_inventory(p)

    def test_guard_refuses_writes_accounts_scripts_and_other_hosts(self):
        for u in [ORIGIN + "/apply", ORIGIN + "/login", ORIGIN + "/source.js", URL + "?token=secret", URL + "#apply", "https://elsewhere.invalid/Student-role-de-j1.html"]:
            with self.subTest(u=u), self.assertRaises(SourceError):
                checked_url(u)
        with self.assertRaises(SourceError):
            checked_url(URL, "POST")

    def test_initial_and_continuation_arguments_checked_before_network(self):
        class NoNetwork:
            def get(self, _):
                raise AssertionError("Network reached")
        for kw in [{"start": 2}, {"first_page_total": 5}, {"start": True}, {"scope": "internships"}, {"start": 2, "first_page_total": True}]:
            with self.subTest(kw=kw), self.assertRaises(SourceError):
                inventory(client=NoNetwork(), **kw)
        with self.assertRaises(SourceError):
            detail(ORIGIN + "/login", client=NoNetwork())

    def test_exact_HTTP_status_and_native_request_metrics_are_preserved(self):
        class Stub:
            def __init__(self, body, status):
                self.body, self.status, self.get_count, self.read_post_count = body, status, 1, 0

            def get(self, _):
                self.get_count += 1
                return Response(self.status, self.body, "text/html")
        for operation, raw in [(lambda client: inventory(client=client), page()), (lambda client: detail(URL, client=client), advert())]:
            with self.assertRaises(SourceError):
                operation(Stub(raw, 206))
            d = operation(Stub(raw, 200))
            self.assertEqual(d["native_HTTP_status"], 200)
            self.assertEqual(d["native_GET_requests"], 2)
            self.assertEqual(d["native_read_POST_requests"], 0)

    def test_full_portal_body_and_separate_schema_are_both_preserved(self):
        d = parse_detail(advert(), URL)
        self.assertIn("body-only clause", d["source_primary_text"])
        self.assertEqual(d["published_schema_job_postings"][0]["description"], "Separate schema requirements")
        self.assertNotEqual(d["published_schema_job_postings"][0]["title"], d["title"])

    def test_missing_or_ambiguous_jobposting_is_not_a_qualified_full_advert(self):
        for raw in [advert().replace(b'"JobPosting"', b'"WebPage"'), advert().replace(b'</head>', b'<script type="application/ld+json">{"@type":"JobPosting"}</script></head>')]:
            with self.subTest(raw=raw[:40]), self.assertRaises(SourceError):
                parse_detail(raw, URL)

    def test_canonical_and_opengraph_must_each_match_exact_request(self):
        for marker in [b'rel="canonical" href=', b'property="og:url" content=']:
            p = advert().replace(marker + b'"' + URL.encode(), marker + b'"' + ORIGIN.encode() + b"/Other-de-j9.html", 1)
            with self.subTest(marker=marker), self.assertRaises(SourceError):
                parse_detail(p, URL)

    def test_generic_or_title_only_page_is_not_a_complete_advert(self):
        with self.assertRaises(SourceError):
            parse_detail(advert().replace(b'id="jobTplContainer"', b'id="other"'), URL)
        with self.assertRaises(SourceError):
            parse_detail(advert().replace(b"<h1>Student role</h1>", b""), URL)

    def test_references_retained_without_controls_or_fetch(self):
        d = parse_detail(advert(), URL)
        self.assertEqual(len(d["native_advertised_references"]), 2)
        self.assertTrue(all(x["independently_verified"] is False for x in d["native_advertised_references"]))
        self.assertNotIn("privateState", d["full_primary_body"])
        self.assertNotIn("secret", d["full_primary_body"])
        self.assertNotIn("src=", d["full_primary_body"])
        self.assertIn("Graphic explanation", d["source_primary_text"])

    def test_no_clock_media_materials_or_human_review_promotion(self):
        d = parse_detail(advert(), URL)
        for key in ["coverage_complete", "full_posting_reviewed", "reviewed_by_model", "original_publication_verified", "nontext_media_requirements_verified", "actual_application_form_material_list_verified", "employer_primary_and_external_attachments_independently_verified"]:
            self.assertIs(d[key], False)
        self.assertEqual(d["native_nontext_media_count"], 1)
        self.assertIsNone(d["original_published_at"])

    def test_unknown_duplicated_and_role_query_fields_refuse(self):
        for q in ["start=0&keyword=PR", "start=0&start=20", "filter%5Btaetigkeit_id%5D%5B%5D=29", "start=-1", "start=00020", "start=1000001", "start=0&filter%5Btaetigkeit_id%5D%5B%5D=28&filter%5Btaetigkeit_id%5D%5B28%5D=28"]:
            with self.subTest(q=q), self.assertRaises(SourceError):
                checked_url(ORIGIN + "/stellenangebote.html?" + q)

    def test_exact_inert_ellipsis_never_executes_but_numbered_script_refuses(self):
        self.assertEqual(parse_inventory(page())["returned_count"], 2)
        with self.assertRaises(SourceError):
            parse_inventory(page().replace(b'javascript:void(0);">...', b'javascript:void(0);">3'))


if __name__ == "__main__":
    unittest.main()
