# Original Onlyfy native career reader

Original anonymous source code for independently identified employer boards
at `https://<tenant>.onlyfy.jobs/en` or `/de`. This reads public native career
pages and complete ad HTML. It does not use the authenticated account API or
assume that a first page or short schema excerpt represents complete supply.

## Operations

- `shared_onlyfy_capabilities`: offline supported contracts and limitations.
- `shared_onlyfy_inventory({board_url, page?, first_page_total?})`: one whole
  native unfiltered page. Every source card survives; no title, geography,
  candidate, target-group or job-language query is accepted.
- `shared_onlyfy_detail({job_url})`: an exact returned native posting URI,
  its shell schema and the complete public primary job frame.

The native public UI established `?page=N` continuation. Ten-card ranges,
current page and actual next-button enabled state must reconcile. Later reads
require the observed first-page total; out-of-range requests are refused
before network and moving/reset/contradictory source pages remain explicit
limits. Native English/German UI fields are supported without inventing a
universal contract or qualification enum.

## Complete body and variant boundaries

The job shell can have an empty primary body while its `JobPosting.description`
is only a 200-character summary. The ordinary job UI loads a separate full ad
at `/job/show/<handle>/full?lang=<locale>&mode=candidate`. This route was
observed in the native public UI; removal of its transient cache-buster was
verified byte-for-byte. The reader first checks the shell's native schema and
same-handle print-link contract, then obtains the full HTML frame. It never
requests the print PDF or an application URL.

The canonical body is the complete `main.main-element` inside the native
`job-ad-component`. Additional `step-stone-job-ad` export variants are retained
separately with their original HTML/text; they are not automatically promoted
to visible requirements. The original full component also remains available
for reconciliation. Script/style text is excluded from the extracted text;
no source script or external asset is executed or fetched.

Public posting handles, schema identifiers and human reference codes are
separate. Inventory identity is employer origin plus native posting handle;
UI locale and page-only back-navigation references do not become new jobs.
Native datePosted, employmentType, TELECOMMUTE and applicant-location fields
are preserved without inventing a first-publication instant, student contract,
Germany-based remote eligibility or individual applicant fit. Physical
meetings/worksites in the full text still require reconciliation.

## Access and coverage

Each call checks current robots policy. 404/410 qualifies resource unavailability
under RFC9309; denials, challenges, malformed policy and source errors stop.
HTTP follows no redirects, sends no auth/cookies and refuses complete responses
above 8 MiB. The IPC bridge also refuses over-budget output without clipping.
No account API, script/CDN, print/PDF, application, contact or subscription
operation is implemented. Legacy onlyfy.io published-handle feeds are distinct;
the reader never guesses a handle or claims their live coverage.

Primary publishing reference:
[XING Job-Feed Integration](https://help.xing.com/hc/de/articles/31499221281309-Job-Feed-Integration).
The native newer career-board protocol is qualified separately through the
employer's public page. One employer board is not a country/employer census or
a complete historical week. Source acquisitions never become candidate
verdicts or application-ready rows.

The shared `public_http.py` module provides bounded anonymous requests, robots
policy and strict JSON for original readers. Existing adapters retain their
interfaces and dependencies.

Standalone: `python shared/onlyfy/reader.py --capabilities`, then `--board-url`
with an exact verified board. Use native `--page` and `--first-page-total` for
continuation, or an exact returned `--job-url` for a complete ad.

## Frozen live qualification, 30 October 2026

The actual unified MCP enumerated seven native THOST pages with 69 distinct
handles and fetched all 69 complete primary ad bodies, each with a separately
preserved export variant. Every schema summary had 200 characters; primary
bodies ranged from 1947 to 4138 characters. German first-page handles matched;
other locale pages were not compared. Unsupported continuation/application
paths were refused, and previous original reader capabilities stayed compatible.
See the [dated aggregate proof](../../docs/onlyfy-live-proof.json). This is an
employer-board qualification, not historical or Germany-wide coverage or fit.
