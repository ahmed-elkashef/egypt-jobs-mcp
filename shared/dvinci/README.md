# Original d.vinci public-publication reader

Read-only original code for d.vinci's documented anonymous job-publication
interface. This uses the singular `/jobPublication` publishing routes. It does
not use the protected account REST API, credentials or application APIs.

Primary contract: [Job Publication API v1.33](https://static.dvinci-easy.com/files/d.vinci%20job-publication-api.html).
The changelog documents anonymous publication access since ATS2022.11. A 403
means this interface is disabled for that portal; no XML/RSS/auth fallback is
attempted after a refusal.

## MCP operations

- `shared_dvinci_capabilities`: offline source contracts and verified custom origins.
- `shared_dvinci_inventory({portal_url, include_body?})`: every current regular
  publication from one independently identified portal. The default documented
  `fields=small` query changes fields, with no role, geography, language,
  category or target-group selection. `include_body: true` omits that query
  parameter and retains full native body variants for every returned row.
- `shared_dvinci_detail({portal_url, publication_id})`: exact full publication
  through documented `GET /jobPublication/show/{id}.json`.

The source returns one complete array without documented pagination or an
independent server total. The array length remains distinct from a separately
reported count. An error, malformed last row, duplicate publication ID or
oversized response never becomes an empty or silently shortened inventory.

Portal seeds are exact HTTPS `<tenant>.dvinci-hr.com` origins, optionally with
`/portal/<name>`, plus the independently verified custom origins listed by
capabilities. No account/job/apply path can be supplied as a portal. Every read
checks current robots policy;404/410 qualifies resource unavailability under
RFC9309, while denials/challenges/server errors stop. Redirects, cookies, auth,
script execution and fetching images are excluded. Each complete response is
bounded at 8 MiB; the IPC bridge also refuses oversized output without slicing.

## Identity and complete native bodies

Identity is portal plus publication ID. `jobOpening.id` is a different native
identity: multiple language/publication records can refer to the same opening
and must all survive acquisition. Null and external published job URLs remain
source records; the reader never follows application or native external URLs.

Full responses preserve every `renderedContent` section, including additional
information, benefits and contact. They also retain raw introduction/tasks/
profile/offer/closing variants and all ten company description fields. The
canonical native description uses rendered sections and unrepresented raw
sections; unused company text remains separate context, not an automatically
advertised requirement. The proof found an empty raw offer field alongside a
nonempty rendered benefits section. HTML is parsed inertly; native markup and
text are source representations, not a browser-render or completed fit review.

## Clocks and eligibility

Publication `startDate`/`endDate` are optional availability clocks. Requisition
`createdDate` and raw `earliestEntryDate` remain separate. None is promoted to
verified first-publication/reopening time. Working-time, target-group and
contract-period labels are configurable employer master data; no universal
eligibility enum is inferred. Location/partial-remote wording does not prove
that a worker can remain based in Germany or that a student contract fits.

The [dated aggregate proof](../../docs/dvinci-live-proof.json) covers two
independently identified portals and 28 current regular publications, with
compact/full identity reconciliation, all native body variants and exact
details. These examples do not enumerate Germany's employers or a historical
week. The repository includes no raw advertisement corpus or applicant data.

Standalone: `python shared/dvinci/reader.py --capabilities`, then
`--portal-url https://dein-weg-zu.dvinci.de`, optionally `--include-body` or an
exact `--job-id` returned by inventory. No account or application operation is
implemented.
