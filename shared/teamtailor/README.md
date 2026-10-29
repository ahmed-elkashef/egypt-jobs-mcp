# Original Teamtailor public career feeds

The career-site reader uses native advertised resources. It does not call
Teamtailor's secret-key account API. Obtain the exact career origin from the
official employer authority. Vendor `*.teamtailor.com` career subdomains and
the explicitly verified custom origins in capabilities are supported; account,
support and arbitrary custom hosts are refused.

Three unified read-only tools are available:

- `shared_teamtailor_capabilities`: offline source contract and allowed origins.
- `shared_teamtailor_inventory`: complete native JSON/RSS feeds with full bodies.
- `shared_teamtailor_detail`: reacquire the same full feeds, select an exact
  returned native GUID, and preserve its complete description and metadata.

The reader checks current robots policy before each fixed GET route. `/jobs`
must advertise its RSS feed and an exact same-origin `Link: rel=api-catalog`.
The catalogue's `/jobs` anchor must advertise `/jobs.json` as JSON Feed1.1.
The reader then reconciles every JSON/RSS GUID, URI and title, plus the native
HTML count when recognized. No role, country, keyword or candidate selection
is accepted. Unknown UI counts remain unknown. Unverified feed continuation
is an explicit limitation, never a guessed page or partial complete-board claim.

Complete JSON `content_html`, independent `_jobposting` and RSS description
variants remain available. Differences are flagged without overwriting a
body. RSS additionally preserves remoteStatus, department, role, division and
every native location. A `none` remote label does not establish an onsite
contract. A source role or location does not establish working-student status,
compatible hours, Germany remote eligibility or person fit.

The source clocks `date_published`, schema `datePosted` and RSS `pubDate` stay
separate from original publication, reopening and observation clocks. A current
feed and reconciled count are not a complete historical weekly interval.
Application requirements and browser-rendered completeness are not inferred.

The [dated aggregate live proof](../../docs/teamtailor-live-proof.json) reconciles
15 Teamtailor, 5 Highsnobiety and 78 Voi current postings across native HTML,
JSON and RSS. All98 complete description variants matched. One native employer
job HTML response independently contained the exact feed description markup.
These are three employer examples, not a national employer directory. A
vendor's customer marketing page is also not a complete employer census.

The original reader makes no authenticated, account, application-form, contact
or subscription request. It never executes scripts, follows redirects, fetches
embedded media, or sends cookies/credentials. XML entity declarations and
malformed/nonfinite/duplicate JSON fail explicitly. HTTP errors, policy denials,
count/identity mismatches and over-bound responses retain null counts; bodies
are never shortened into an apparent successful read.

Standalone CLI using the repository's existing Python/lxml runtime:

```sh
python shared/teamtailor/reader.py --capabilities
python shared/teamtailor/reader.py --careers-origin "$VERIFIED_CAREER_ORIGIN"
python shared/teamtailor/reader.py --careers-origin "$VERIFIED_CAREER_ORIGIN" \
  --job-id "$EXACT_NATIVE_GUID"
```

Keep raw captures in the consuming application's private evidence store.
Source attribution and content rights remain with the publisher; repository
code licensing does not license redistribution of employer posting content.
