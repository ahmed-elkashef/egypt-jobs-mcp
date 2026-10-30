# Original public German board readers

This package reads fourteen providers (EnglishJobs metadata only; source-specific access/cap limits apply) through ordinary permitted HTTP, native JSON,
SSR data and an official feed. No browser, account or application action starts.

| Source | Inventory | Full detail |
| --- | --- | --- |
| Absolventa | `/jobs`, complete primary cards and actual native page links | Native `internal-job-offer` body plus JobPosting |
| academics | `/stellenanzeigen`, native primary IDs and active-page controls | Native `job-ad-content` body plus JobPosting |
| stellenanzeigen.de | `/jobs/`, JSON-only native Flight state reconciled against every visible primary card | Native `job-ad-details-widget` plus JobPosting |
| Yourfirm | `/stellenangebote/`, the same verified SSR contract | Native `job-ad-details-widget` plus JobPosting |
| GermanTechJobs | Native whole `/api/jobsLight` array | `/api/jobWithUrl/{actual jobUrl}`; description, mandatory and optional requirements and responsibilities |
| service.bund.de | Official vacancy RSS feed | Guarded native `/IMPORTE/Stellenangebote/…/*.html` body |

`de_public_german_boards_capabilities` is offline. The inventory and detail tools
require an explicit source and exact native URL. Source origins, paths and query
fields are fixed. Career/title/education/keyword queries, duplicate parameters,
login, apply, newsletter and arbitrary URLs are refused. Current robots is checked
before every resource, including redirect targets. Identity/page changes are
refused; partial and oversized HTTP responses never become complete or empty
success. Rate-limit status and Retry-After remain explicit.

Static pagination follows real links. The SSR providers expose a numeric native
page/offset/limit/count contract, independently checked at pages1,2,3. Their next
URL is derived from that verified contract and explicitly labelled as such; it is
not misrepresented as an emitted next href. Their relevance sorting and moving
counts do not prove chronological or frozen-window traversal. Native default
filters are returned so a consumer can inspect their scope.

The Flight reader parses JSON and length-delimited UTF8 text. It never evaluates
website JavaScript, imports provider modules or follows instructions inside job
content. References are resolved as data; unknown/malformed/ambiguous state fails
explicitly. Only the known native search result and query metadata reach the
inventory output, never whole user/account/tracking bootstrap state.

Keep original campaign, renewal, activation, creation, expiry, feed-publication
and observation clocks distinct. For example, a current-start field can say
29October while originalStartDate says14September. No field is silently promoted
to a verified original employer publication instant. Site country and remote/model
labels do not establish worker-country eligibility, recognition or applicant fit.

The observed government RSS snapshot contains500items and only27–29October,
leaving earlier weekly history unresolved. A denied search route is not bypassed.
Empty titles and other incomplete feed records remain metadata, including their
verification requirement. Native URL fragments and anonymous jsessionid markers
are removed from returned resource URLs; raw captures stay private. Provider/path
namespaces prevent numeric IDs from colliding. This is not all-government supply.

Full native visible bodies retain requirements beyond short structured fields.
Employer originals, required files, changed/reopened identities and individual
eligibility still need consumer review. No source read becomes an application or
an applicant-fit decision.

Set `JOB_MARKET_CAPTURE_DIR` to an explicitly private directory for optional
content-addressed native bytes. Never commit real job datasets, raw web pages,
bootstrap/session state, applicants or credentials. Code licensing does not grant
rights to republish provider content. Tests are synthetic; bounded live evidence
is separate and dated.


## Additional native contracts in v0.4.5

Jobs.de returns native jobs DTOs, current clocks and explicit page ranges. Pages
1, 2 and 3 and the frontend formula independently establish that `ranges.last`
is a count. Conditions and fulltext must remain empty; numeric continuation is
labelled as derived rather than a provider-emitted href. Native application flags
are retained as portal data, never employer document waivers.

Jobware exposes its official complete advertisements sitemap. Each nine-digit
advertisement ID retains leading zeroes. `lastmod` and `expires` do not become an
original publication date. Full details require both the structured wrapper and
the exact same-advertisement native iframe, with independent current robots
checks. An empty/denied/mismatched iframe never falls back to a short snippet.

BerlinStartupJobs root inventory returns a **partition catalogue**, with no empty
vacancy array. Read every category and emitted next-page href, retaining new
unsupported categories rather than dropping them. Current role and work-model
categories overlap; acquiring only candidate-interest categories is incomplete.
The dated diagnostic traversed all 12 native categories and found 136 distinct
native URLs. Complete visible bodies remain separate from metadata and fit.

EnglishJobs supports native state/student/remote **metadata only**. It preserves
all cards, the selected page and real continuation. The dated signed-clickout
robots denial remains explicit. Signed/encrypted redirect values never reach
outputs; no redirect decoding, challenge execution or denied request is used.
Actual original employer identity and a separately permitted complete body remain
necessary. A native theme is not a proven employment contract or national census.


## XING and immutable URI discovery in v0.4.6

Anonymous native lists retain all primary records and actual page/range/count
metadata, including external promoted cards. The source enum INTERN is labelled
Studierende; visible descriptions and exact contracts still need reconciliation.
The native jobs-in-hessen route resolves literal location text Hessen with a20km
radius. It is **not** evidence of a Hesse state polygon. The student page100
returned20 records with no next link despite more than12,000 reported records;
this terminal is a provider cap and remains unresolved coverage.

The data-object parser accepts only inert JSON plus explicit undefined-as-unknown.
It never executes website JavaScript. Only selected job facts are hydrated from
references; viewer/account/matching graphs, tracking tokens and signed branding
assets are excluded. A full detail requires matching native DTO and visible
complete description plus the independent JobPosting. Refreshed/activation clocks
never silently become an original employer publication.

Advertised sitemap records are URI discovery, including expired adverts and
directory/category links. They are never normal vacancy pages. For a large whole
partition, set JOB_MARKET_CAPTURE_DIR to an explicitly private directory. The
reader preserves every URI in a content-addressed immutable capture and returns a
manifest. Read every segment using de_public_german_board_capture_segment with
the exact capture_id and zero-based segment_index. Segments contain1,000 URIs,
are explicitly consumer segmentation rather than provider pagination, and bind
the original resource hash. Missing configuration, checksum changes, symlinks and
invalid/out-of-range indices fail without truncation or an arbitrary file API.


## get in Engineering and Zenjob in v0.4.7

get in Engineering's first39 native SSR records reconcile with every visible
primary card. Its published anonymous openV2 GET `/api/v2/open/job/search`
contract supplies39 records at offsets0/39/78 with `X-Requested-With:
XMLHttpRequest`. This is a protocol header, with no authentication or browser
identity; normal verified TLS remains enabled. The SSR search always starts at0,
so a guessed SSR `start` URL is refused. Only that unfiltered native GET is
supported; degree, career, title, debug and restricted API fields are refused.
Full native content sections match the visible sections plus an independent
JobPosting. Home office and schema publication dates remain unqualified evidence.

Zenjob exposes public UUID shift cards, native active-page markers and real
continuation links. The `>>` control is another native link, not an assumed last
page. Full detail retains both structured description and the entire visible
requirements/notes; the source can include a shift-length warning only in the
latter. Shift starts, datePosted and expiry remain separate. PART_TIME and
student-oriented shifts do not establish a working-student contract. A source
schema URL can omit the actual `/jobs/` route; the reader reconciles UUID/title
without requesting that alternate path. No native filter POST, app signup,
account or application action is supported.

HeyJobs' permitted directory/sitemap discovery is accessible but the tested
native list/detail routes returned202. No challenge, protected API workaround,
Next-data rewrite or browser fingerprint was used. Instaffo's own current FAQ
excludes internships/working-student roles; its public general job board remains
a separate implementation question. These are dated source facts, not national
coverage claims. See the aggregate proof; raw corpus/bootstrap stays private.


## Official Frankfurt student portal in v0.4.8

`swffm` is the official `stellenmarkt.swffm.de` portal. Native unfiltered pages
and enabled controls are reconciled; the disabled terminal Next points to the
root and is never followed. The homepage is a featured-reference catalogue. The
finite employer directory/profile context is separately typed and never returned
as an empty/full vacancy list or a complete regional/company census.

The dated three-page traversal retained56 distinct ad references (20/20/16) and
six employer profiles. The portal label does not prove a Hesse worksite: the
first ad was in Münster. All source cards remain present, including mixed,
private and graduate categories; student labels do not establish exact contracts.

Native visible HTML sections were available for48 ads. Seven PDF ads independently
publish a text alternative in the permitted HTML response. Preserve that complete
provided text separately from structured description: a real case says working
student in the text and full-time in schema, while another start fact says2027
and the body says ASAP. No original date, contract or availability is invented.
The eighth PDF ad has no such full text and remains source-limited. PDFs are
robots-denied: none were fetched and no viewer, asset or URL rewrite was used.
Provided-text completeness does not verify PDF/employer completeness. There is
no keyword/Ajax/query, account, publication, application or contact operation.

## Frankfurt Airport Retail native public board

The original far_retail module is exposed through the existing German board
capabilities/inventory/detail tools. Its qualified whole board is
https://frankfurt-airport-retail.de/far/de/karriere-start/jobs. Public job URIs
use the native /far/de/job/<jobId> route, independently checked against the
server's matching jobId/title. This is one employer source, not a national or
Heinemann employer census.

The source's anonymous first-party API uses POST for reads. Only fixed whole
company jobsearch, non-preview jobdetails and contentful benefits/texts are
used, after checking policy for the page and each actual API path. The native
wildcard means all company vacancies; no role, hours or department selector
is exposed. @odata.count must match every unique metadata row. Capped or
changed responses refuse rather than presenting a partial or empty market.

A full detail retains introduction/tasks/profile, every returned benefit
headline, separate company/recruiter copy, raw variants and each exact read's
provenance. The native client transforms benefit IDs into a prefixed CSV and
normalizes the recruiter with the native override field; those public read
parameters are reproduced without executing or copying the client. Hydration
bearer fields, source scripts/images, account, preview, application and contact
operations are never used. Source apply links are returned as data only.

Native sector and experience categories are not contract models. Aushilfen,
Berufseinsteiger and monthly hours do not establish a working-student contract,
weekly schedule, original publication or fit. Company context remains distinct
from requirements. Textual completeness does not certify decorative images or
the external application portal.

The [dated actual MCP proof](../../../docs/far-retail-live-proof.json) reconciles
all 12 metadata rows, six explicit apprenticeship cuts and all six remaining
complete public descriptions, with three guarded refusals. All 674 local tests
pass (140 Node/534 Python). Release CI and installed-runtime checks are separate.


## Modern SAP careers front

The original sap_modern reader uses the existing German public-board tools,
separately from the legacy SAP SuccessFactors RMK reader. Its fixed board is
https://jobs.sap.com/en/jobs/; the advertised native Germany facet is
https://jobs.sap.com/en/jobs/?country=Germany. Follow each actual next page
and preserve the first native total. No role, experience, department, custom
sort or candidate query is exposed. A whole current front is not a frozen
week, national market or complete employer census.

The source serves both inline and cached React Flight frames. The original
data-only parser checks byte lengths, explicit stream start/closure, separate
record namespaces and resolved model agreement. It never evaluates website
scripts or modules. The public native default newest sort, page, size, query
echo, counts and unique posting IDs must reconcile.

Full primary HTML is retained independently of schema descriptions and generic
page context. URL IDs differ from requisition references. Posting/display
clocks, part/full-time and work-pattern labels remain raw; there is no exact
student contract, original-publication, worker-country or applicant-fit claim.
Runtime reads only anonymous first-party public HTML and robots. No source
script, image, account, application, personalization or contact request.

Protocol facts were checked against the
[public React 19.2 client protocol](https://github.com/facebook/react/blob/v19.2.0/packages/react-client/src/ReactFlightClient.js).
This is an original Python data reader; source website and framework code are
not executed or copied into the implementation. Source-specific native and
installed qualification receipts are recorded separately from unit tests.

The [actual unified MCP qualification](../../../docs/sap-modern-live-proof.json)
read all five Germany pages (55 unique IDs) and all 28 current whole-front pages
(334 unique IDs), with the Germany set contained in the whole front. Two complete
public bodies, separate primary/schema/context variants and three refusal cases
passed. These are source-format tests, without an applicant-fit or weekly-market
claim. All 695 local tests pass (140 Node/555 Python), including 21 new targeted
cases. Exact release CI and installed-runtime qualification remain separate.

## JOIN employer boards

Use `source: "join"` with an independently identified exact company board. The original reader checks both native SSR layouts and every source page/count; general-application context and cached virtual-page rows never add vacancies. Complete primary HTML, separate schema/company content, internal/public IDs and same-company canonical redirects are preserved. No role query or account/application action. See [the full contract](../../../docs/join-native-reader.md).
