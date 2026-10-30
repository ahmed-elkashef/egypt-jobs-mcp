# Ausbildung.de public internship reads

The original `de_public_ausbildung_inventory` and
`de_public_ausbildung_detail` tools read the portal's public internship scope.
The `/schuelerpraktikum/` section includes university internships: its section
name is not proof that an advert is exclusively for pupils. Native mandatory,
voluntary, school-class, minimum-age and educational-direction fields are
retained as evidence, not promoted into university or applicant eligibility.

## Independently qualified public protocol

The unfiltered initial page is
`https://www.ausbildung.de/schuelerpraktikum/stellen/`. Its public React Flight
data contains `searchType: student`, empty `searchParams`, empty initial filters,
DE entry metadata, and separate `hits.primary`, `hits.extended` and `meta`.
Only literal JSON/text data records are parsed; no JavaScript evaluator, website
runtime, dynamic import or source program is executed.

On 30 October 2026, the actual native Search component advertised the named
`getInternshipSearchResults` read operation and increments of `from: 20`.
The anonymous native request is POST to the same public listing URL, with
`Accept: text/x-component`, `Content-Type: text/plain;charset=UTF-8`, the
published `Next-Action` function routing identity, and JSON argument data
`[{"from":20}]`. No account, credential, cookie, CSRF token, applicant field,
application action or third-party script request is involved. Its actual result
envelope uses the **string** `statusCode: "200"` and Flight action result `$@1`.

This reader fixes the independently qualified read operation. Callers cannot
provide a different function identity, headers, URL, query or arbitrary action.
The public function reference is routing data, not a user/session credential.
The reference belongs to the actually advertised asset
`/_next/static/chunks/006sfh0i8jsm5.js`, SHA-256
`2a3916610a6dcb25d4ff77510fd21b01119f1685d8bf530a59035f430567d40c`.
Only those interface facts are included here. No website reference-program
bytes are included in this repository or imported by the runtime.

An initial page must advertise that qualified deployment; a changed deployment
stops for separate qualification. Later requests carry the acquired exact
`resultsCount`, `vacanciesCount`, DE entry and protocol binding. `from` must be
an in-range multiple of 20. Changing either counter, incomplete/oversized pages,
duplicate vacancy IDs in a page, nonempty extended recommendations, active
filters or unexpected personalized state stops without clipping or resetting.
The consumer must also reconcile cross-page identity drift and predecessors.

## Scope and counts

Native qualification observed 3,916 results and 4,834 places. These are dated
observations, not runtime constants. A result can represent several places or
branches. Vacancy UUID and parent posting UUID are distinct; the native slug
and public advert URL identify the **vacancy** UUID.

The native empty query still displays Frankfurt as default source context.
This is retained and never treated as a person's commute constraint or proof
of every worksite's location. Source DE locale is not job geography or remote
permission. The reader adds no career, geography, model or duration filters.
The unfiltered internship scope is not the whole German employment market,
an apprenticeship census, a separate working-student inventory, or an immutable
weekly snapshot. Sampling a terminal page does not prove preceding pages were
acquired; all coverage and review flags remain false.

## Public advert bodies

Details accept only an exact acquired HTTPS native slug/vacancy UUID route,
without query, fragment or application suffix. Canonical URL, one main/header,
and the actual native internship role/application sections must be present.
The complete main text, advertised links/media references and separately
published structured data are retained. Malformed JSON-LD is reported with
its original text rather than repaired. Strict Flight parsing rejects duplicate
keys, nonfinite numbers, invalid UTF-8 and malformed complete JSON records.

External references and application buttons are evidence only and are not
followed. A portal mirror can remain available after its employer offer
returns 404; body acquisition does not verify current employer status, actual
required materials, individual fit, current enrolment, university recognition
or an original publication clock. Nontext requirements remain unreviewed.

Current exact-route robots policy, including conservative wildcard denials,
applies before data requests. Policy failures, pacing requirements, redirects,
throttles, authentication and unexpected responses stop without retry or
bypass. The tools create no account, application, contact or subscription.
