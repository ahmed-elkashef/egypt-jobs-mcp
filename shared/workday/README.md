# Original Workday public CXS reader

This shared reader supports explicitly identified employer boards in any country.
Obtain the exact board URL from an official employer careers authority. It does
not guess tenant slugs or enumerate a country's employers. The [dated live
proof](../../docs/workday-live-proof.json) verifies one official employer seed,
922 distinct current postings across 47 native pages, and three source bodies.

The unified tools are `shared_workday_capabilities`,
`shared_workday_inventory` and `shared_workday_detail`. Capabilities are offline.
An initial inventory request supplies only `board_url` and optional `limit` of
1–20. The fixed native POST body has empty `searchText` and `appliedFacets`.
Follow **every argument** in the returned `continuation`, including
`first_page_total`. This count comes from the initial native response, not a
fresh later-page count or an operator estimate.

Native later responses can contain 20 jobs with `total: 0`. Their global count
is unknown on that response; the zero is retained as raw evidence. At the last
nonempty page, stop when the accumulated native offset reaches the observed
initial total. An out-of-range offset can reset to page one rather than return
an empty list. Such requests are refused before network. Compare IDs across
pages and reconcile the observed count; moving pages can still omit/repeat ads.

Details require the exact returned `external_path` and the same `board_url`.
The anonymous GET is restricted to the same tenant/site's public CXS job route.
Returned native external URL must match tenant, site and posting path. Posting
identities include origin/site/path; requisition IDs alone are not unique.
Locale is preserved as source context rather than a new posting identity.

The complete native `jobDescription` markup and extracted text are retained
with the original native job facts. They are identified as
`native_cxs_job_description`; browser-visible text and independent completeness
review are not claimed. Relative `postedOn` and native `startDate` remain raw.
No original publication instant, employment start, remote worker country or
student contract is invented from these fields.

Current robots policy is checked with the correct plain-text representation.
403/429/server failures and malformed policies stop the read. A missing robots
resource (404/410) is qualified under RFC9309, not treated as an access denial.
Requests never follow redirects, use cookies or credentials, execute JavaScript,
fetch application forms, or touch account/candidate/contact/subscription APIs.
Source failures have null counts and no sliced body or fabricated empty supply.

The retained legacy `fetch_company_ats_jobs` tool refuses explicit Workday domain
fetching. Use these original board readers instead. Legacy auto-detection remains
explicitly limited discovery context, never verified supply.

Standalone CLI (Python with the repository's existing `lxml` dependency):

```sh
python shared/workday/reader.py --capabilities
python shared/workday/reader.py --board-url "$VERIFIED_WORKDAY_BOARD"
python shared/workday/reader.py --board-url "$VERIFIED_WORKDAY_BOARD" \
  --offset 20 --first-page-total "$EXACT_INITIAL_NATIVE_TOTAL"
python shared/workday/reader.py --board-url "$VERIFIED_WORKDAY_BOARD" \
  --external-path "$EXACT_NATIVE_JOB_PATH"
```

Native responses are acquisition evidence. Country coverage, historical weekly
coverage, worker eligibility, person-specific fit and application readiness are
separate decisions made by the consumer. Keep raw captures private; code
licensing does not grant a licence to redistribute employer posting content.
