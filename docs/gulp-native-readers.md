# Original GULP employment readers

The original `de_public_gulp_inventory` and `de_public_gulp_detail` tools use
anonymous, first-party public job read interfaces. These are employment records
from Randstad Professional / GULP, separate from freelance client projects and
from Randstad's own-company careers. No account, cookie, candidate profile,
application, message, saved search or contact action is available.

## Independently qualified read protocol

The public `https://www.gulp.de/gulp2/g/jobs` frontend advertises its read
interfaces. Interface references were inspected as factual protocol evidence on
30 October 2026. No reference program was executed, copied into this repository
or incorporated into the implementation.

The native jobs provider sends a **read-only POST** to:

`https://www.gulp.de/gulp2/rest/internal/projects/jobs/search`

The initial native DTO is:

```json
{"query":null,"page":0,"limit":20,"language":"DE"}
```

The exact native response has integer `totalCount` and array `projects`.
The public interface uses zero-based page indices and its actual default
twenty-record page size. These facts were checked against actual initial,
interior and terminal responses; this is not an inferred cursor or HTML paging
arithmetic. The dated qualification reported 667 records, with twenty on each
of pages zero and one and seven on page33. Those observations are not a current
count, an acquisition of the intervening pages or a frozen weekly census.

The independently advertised detail service performs GET on:

`https://www.gulp.de/gulp2/rest/internal/projects/job/{acquired-id}?language=DE`

Only an exact acquired public advert URI such as
`https://www.gulp.de/gulp2/g/jobs/C00000001` is accepted. The example ID above is
synthetic and is never requested by tests. Native ID, index ID, public URI and
requested ID must agree. No application route, arbitrary origin, source script
or employer original is requested.

## Whole native pages and safe continuation

Inventory accepts only `page` and, on subsequent pages, `first_page_total`.
All original public-DE tools use strict MCP object schemas: unknown fields
are rejected before their handlers, rather than silently removed by the SDK.
It has no role, degree, employer, interest, location, remote, language or
working-model query. Every whole native record and its public fields is retained.

Later pages require the previously acquired positive count and an in-range
native index. A changed count, short interior page, extra row, repeated ID
within one page, malformed metadata or contradictory identity produces a typed
source limit. The explicit client ceiling is ten million records /500,000
pages; it does not become a provider count. No empty-page probing, last-page
reset or arithmetic completion claim is permitted.

`next_request` carries the next native page and bound count. Consumers must
reconcile every page, all cross-page IDs, changes and dated evidence. Matching
counts are not an immutable snapshot. A single terminal page never proves
that other pages were acquired. Returned `coverage_complete` and human-review
flags always remain false.

## Complete public detail and individual review

The full public native detail DTO is preserved, including description,
responsibilities, skills, benefits, salary, schedule, source dates, public
recruiter metadata and published `metaJobPosting`. The reader also returns
text-only role sections without executing HTML or following media/controls.
The metadata preview is explicitly not a full primary.

Published JobPosting JSON is parsed separately. Malformed schema is retained
with a diagnostic, without repair; it cannot replace the acquired primary
fields. Whole API JSON must be strict UTF-8 and valid nonduplicated finite JSON.
Missing whole role fields or unexpected personalized account state refuse.

`TEMP_JOB` and `PERM_JOB` describe temporary/permanent placement contracts.
They do not establish student internship, mandatory-placement recognition or
working-student eligibility. Native `FULL_TIME` and descriptive part-time
language can conflict: both remain visible for individual review. Raw source
date names, German locale, source country, office location and remote-possible
flags do not prove original publication instants, Germany remote permission,
job worksites, practical commute or personal fit.

## Transport and policy limits

Exact allowlisted HTTPS read routes are checked before requests. Current robots
policy must permit each read. In addition to the standard-library parser,
matching wildcard Disallow rules are conservatively denied across supported
Python versions; a more specific Allow may require separate qualification.
Uncoordinated published pacing directives stop the reader. Redirects,
authentication failures, throttling, unknown content, transport failures and
oversized bodies return typed limits without retry, cookie/session bootstrap,
alternate agents or browser fallback. `Retry-After` is preserved for the
operator. No credential environment variable or dependency was added.

This implements the qualified public employment channel. It does not implement
freelance projects, bypass the separate own-careers HR4YOU policy barrier or
claim all German staffing/employer coverage.
