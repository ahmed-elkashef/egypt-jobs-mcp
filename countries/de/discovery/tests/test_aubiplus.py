"""Synthetic native grouped inventory, scope, text and malformed-data checks."""
import unittest
from urllib.parse import urlencode

from aubiplus import ENTRY, ORIGIN, checked_url, identity, parse_detail, parse_inventory, read

from network import Response, SourceError

URL = ORIGIN + "/praktikum/example-role-1/"


def uri(scope="student_internship", page=1):
    fields = [("fLand[0]", "deutschland")]
    if scope != "all":
        fields.append(("fTyp[0]", "studentenpraktikum" if scope == "student_internship" else "werkstudent"))
    if page != 1:
        fields.append(("seite", str(page)))
    return ENTRY + "?" + urlencode(fields)


def page(scope="student_internship", position=1, last=False, total=52):
    model = "" if scope == "all" else "studentenpraktikum" if scope == "student_internship" else "werkstudent"
    selected = f'<input name="fTyp[]" value="{model}" checked>' if model else ""
    current = f'<a class="bg-info" href="{uri(scope,position)}">{position}</a>'
    following = '<li class="page-item disabled invisible"><a href="#" aria-label="Weiter zu Seite "></a></li>' if last else f'<li><a href="{uri(scope,position+1)}" aria-label="Weiter zu Seite {position+1}"></a></li>'
    return f'''<html><head><title>{total} Plätze gefunden</title></head><body>
<form class="suchmaschine-form" action="{ENTRY}" method="get">{selected}<input name="fLand[]" value="deutschland" checked>
<div class="result-container"><div class="my-3 text-primary-dark rounded-3"><a href="/unternehmen/example/">Example employer</a>
<div class="row"><div><h2><a href="/praktikum/example-role-1/">Öffentliche Kommunikation</a></h2><p>Frankfurt; start ASAP</p></div></div>
<div class="row"><div><h2><a href="/werkstudium/other-role-1/">Other role</a></h2><p>Other context</p></div></div>
</div></div><ul class="pagination">{current}{following}</ul></form></body></html>'''.encode()


def advert():
    malformed = '{"@type":"JobPosting","description":"literal\ncontrol character"}'
    return f'''<html><head><link rel="canonical" href="{URL}"><meta property="og:url" content="{URL}">
<script type="application/ld+json">{malformed}</script><script type="application/ld+json">{{"@type":"Organization","name":"Example"}}</script></head>
<body><main><div class="card"><h1>Öffentliche Kommunikation</h1><p>Header deadline30November2030.</p><img alt="Public logo" src="https://example.invalid/logo.png"></div>
<div id="stellenbeschreibung"><h2>Complete duties</h2><p>All actual work, required and preferred conditions, body-only deadline29November2030, compensation, internship duration and native programme context remain complete.</p></div>
<div id="sidebar"><p>Frankfurt; source start date2030-01-01; source referenceREF1.</p></div>
<div id="weitere-bewerbungsmoeglichkeiten"><p>Published application information and materials.</p><button onclick="secret()">Apply control</button><form><input name="csrf" value="secret"></form></div>
<div id="weitere-angebote"><h2>Unrelated engineering role</h2></div></main></body></html>'''.encode()


class AubiPlusContracts(unittest.TestCase):
    def test_complete_grouped_rows_keep_namespaced_identity_and_context(self):
        d = parse_inventory(page(), "student_internship")
        self.assertEqual(d["returned_count"], 2)
        self.assertEqual(d["native_group_count"], 1)
        self.assertEqual(d["metadata"][0]["title"], "Öffentliche Kommunikation")
        self.assertNotEqual(d["metadata"][0]["id"], d["metadata"][1]["id"])
        self.assertIn("Frankfurt", d["metadata"][0]["native_offer_row_text"])
        self.assertEqual(d["metadata"][0]["company"], "Example employer")

    def test_source_counter_is_not_unique_records_or_page_arithmetic(self):
        d = parse_inventory(page(total=101), "student_internship")
        self.assertEqual(d["source_result_count"], 101)
        self.assertEqual(d["returned_count"], 2)
        self.assertIn("not_qualified_as_unique_adverts", d["source_count_unit"])
        self.assertEqual(d["next_request"]["page"], 2)

    def test_native_continuation_exact_uri_and_initial_counter_are_required(self):
        d = parse_inventory(page(position=2), "student_internship", 2, first_page_total=52, continuation_url=uri(page=2))
        self.assertEqual(d["next_request"]["continuation_url"], uri(page=3))
        for extra in [{}, {"first_page_total":52}, {"first_page_total":52,"continuation_url":uri("working_student",2)}]:
            with self.subTest(extra=extra), self.assertRaises(SourceError):
                parse_inventory(page(position=2), "student_internship", 2, **extra)

    def test_native_selected_scope_country_and_highlighted_page_must_match(self):
        for raw in [page("all"), page().replace(b'value="deutschland" checked',b'value="oesterreich" checked'), page(position=2)]:
            with self.subTest(raw=raw[:30]), self.assertRaises(SourceError):
                parse_inventory(raw, "student_internship")

    def test_moving_counter_is_not_silently_complete(self):
        with self.assertRaises(SourceError):
            parse_inventory(page(position=2,total=51), "student_internship",2,first_page_total=52,continuation_url=uri(page=2))

    def test_observed_disabled_terminal_needs_no_total_arithmetic(self):
        d = parse_inventory(page(last=True,total=101), "student_internship")
        self.assertIsNone(d["next_request"])
        self.assertFalse(d["has_more"])

    def test_missing_or_inconsistent_terminal_is_not_completion(self):
        for raw in [page(last=True).replace(b'disabled invisible',b'invisible'),page(last=True).replace(b'aria-label="Weiter zu Seite "',b'aria-label="Weiter zu Seite 2"'),page(last=True).replace(b'</ul>',f'<a href="{uri(page=2)}">2</a></ul>'.encode())]:
            with self.subTest(raw=raw[:30]), self.assertRaises(SourceError):
                parse_inventory(raw,"student_internship")

    def test_changed_next_scope_and_numbered_scope_are_refused(self):
        for raw in [page().replace(uri(page=2).encode(),uri("working_student",2).encode()),page().replace(b'</ul>',f'<a href="{uri("working_student",3)}">3</a></ul>'.encode())]:
            with self.subTest(raw=raw[:30]), self.assertRaises(SourceError):
                parse_inventory(raw,"student_internship")

    def test_empty_clipped_and_missing_row_are_never_zero_supply(self):
        for raw in [page(total=0),page()[:-7],page().replace(b'<h2>',b'<h3>').replace(b'</h2>',b'</h3>')]:
            with self.subTest(raw=raw[:30]), self.assertRaises(SourceError):
                parse_inventory(raw,"student_internship")

    def test_complete_metadata_never_promotes_models_clocks_or_human_review(self):
        d = parse_inventory(page(),"student_internship")
        for row in d["metadata"]:
            self.assertIsNone(row["description"])
            self.assertIsNone(row["original_published_at"])
            self.assertTrue(row["model_reconciliation_required"])
            self.assertFalse(row["full_posting_reviewed"])
            self.assertFalse(row["reviewed_by_model"])

    def test_url_guard_refuses_queries_actions_other_hosts_and_role_keywords(self):
        for url in [ORIGIN+'/login',ORIGIN+'/source.js',URL+'?apply=true',URL+'#apply','https://elsewhere.invalid/praktikum/example-role-1/',ENTRY+'?fLand%5B%5D=deutschland&s=PR',ENTRY+'?fLand%5B%5D=deutschland&aSuggestLat=50',ENTRY+'?fLand%5B%5D=deutschland&fLand%5B0%5D=deutschland']:
            with self.subTest(url=url), self.assertRaises(SourceError):
                checked_url(url)
        with self.assertRaises(SourceError):
            checked_url(URL,'POST')

    def test_namespace_ids_do_not_collapse_across_offering_kinds(self):
        self.assertNotEqual(identity(URL)[2],identity(ORIGIN+'/werkstudium/example-role-1/')[2])

    def test_acquired_internship_thesis_namespace_is_retained_in_all_supply(self):
        raw=page('all').replace(b'/praktikum/example-role-1/',b'/abschlussarbeitsthema/example-role-1/')
        d=parse_inventory(raw,'all')
        self.assertEqual(d['metadata'][0]['native_kind'],'abschlussarbeitsthema')
        self.assertTrue(d['metadata'][0]['model_reconciliation_required'])

    def test_full_header_body_facts_application_information_are_preserved(self):
        d = parse_detail(advert(),URL)
        for text in ['Öffentliche Kommunikation','Header deadline','body-only deadline','source referenceREF1','Published application information']:
            self.assertIn(text,d['source_primary_text'])
        self.assertNotIn('Unrelated engineering role',d['source_primary_text'])

    def test_malformed_published_schema_is_reported_without_repair_or_clocks(self):
        d = parse_detail(advert(),URL)
        self.assertEqual(len(d['published_structured_data_parse_errors']),1)
        self.assertFalse(d['published_structured_data_parse_errors'][0]['repaired'])
        self.assertEqual(d['published_structured_data'][0]['@type'],'Organization')
        self.assertFalse(d['malformed_published_data_repaired_or_promoted'])
        self.assertIsNone(d['original_published_at'])

    def test_canonical_and_opengraph_each_bind_the_exact_advert(self):
        for marker in [b'rel="canonical" href=',b'property="og:url" content=']:
            raw=advert().replace(marker+b'"'+URL.encode(),marker+b'"'+ORIGIN.encode()+b'/praktikum/other-2/',1)
            with self.subTest(marker=marker),self.assertRaises(SourceError):
                parse_detail(raw,URL)

    def test_missing_complete_header_body_facts_or_information_refuses(self):
        for marker in [b'<h1>',b'id="stellenbeschreibung"',b'id="sidebar"',b'id="weitere-bewerbungsmoeglichkeiten"']:
            with self.subTest(marker=marker),self.assertRaises(SourceError):
                parse_detail(advert().replace(marker,b'changed-marker',1),URL)

    def test_no_source_control_or_media_material_eligibility_promotion(self):
        d = parse_detail(advert(),URL)
        for word in ['secret','onclick=','src=','Apply control']:
            self.assertNotIn(word,d['full_primary_body'])
        self.assertIn('Public logo',d['source_primary_text'])
        for key in ['coverage_complete','full_posting_reviewed','reviewed_by_model','source_active_vacancy_verified','nontext_media_requirements_verified','actual_application_form_material_list_verified','employer_primary_and_external_attachments_independently_verified']:
            self.assertIs(d[key],False)

    def test_invalid_utf8_is_refused_without_replacement_or_guess(self):
        for operation,raw in [(lambda value:parse_inventory(value,'student_internship'),page()),(lambda value:parse_detail(value,URL),advert())]:
            with self.subTest(operation=operation),self.assertRaises(SourceError):
                operation(raw.replace(b'</body>',b'\xff</body>'))

    def test_http_status_charset_and_real_request_metrics(self):
        class Stub:
            get_count=2
            read_post_count=0
            def __init__(self,status=200,content_type='text/html; charset=utf-8'):
                self.status,self.content_type=status,content_type
            def get(self,_):
                return Response(self.status,advert(),self.content_type)
        d=read('detail',url=URL,client=Stub())
        self.assertEqual(d['native_GET_requests'],2)
        for kw in [{'status':206},{'content_type':'text/html'},{'content_type':'text/html; charset=latin-1'}]:
            with self.subTest(kw=kw),self.assertRaises(SourceError):
                read('detail',url=URL,client=Stub(**kw))

    def test_bad_arguments_refuse_before_any_network(self):
        class Never:
            def get(self,_):
                raise AssertionError('Unexpected network')
        for extra in [{'scope':'PR'},{'page':True},{'page':2},{'first_page_total':52},{'continuation_url':uri()}]:
            with self.subTest(extra=extra),self.assertRaises(SourceError):
                read('inventory',client=Never(),**extra)
        with self.assertRaises(SourceError):
            read('detail',url=ORIGIN+'/login',client=Never())


if __name__ == '__main__':
    unittest.main()
