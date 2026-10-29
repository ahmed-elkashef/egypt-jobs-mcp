# Original public German board readers

This package reads eleven providers (EnglishJobs metadata only; source-specific access/cap limits apply) through ordinary permitted HTTP, native JSON,
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
