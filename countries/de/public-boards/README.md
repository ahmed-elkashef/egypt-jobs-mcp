# Original public German board readers

This package reads six providers through ordinary permitted HTTP, native JSON,
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
