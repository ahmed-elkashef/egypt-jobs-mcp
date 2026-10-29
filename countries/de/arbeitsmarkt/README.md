> This retained component now belongs to [Job Market MCP](https://github.com/ahmed-elkashef/job-market-mcp). Install dependencies from the monorepo root with `npm ci --ignore-scripts`; see the root README for unified startup. The component instructions below preserve its standalone interface.

# German Arbeitsmarkt MCP

A read-only MCP server for German labour-market sources. It preserves the six Greyt GmbH tool families and improves Bundesagentur für Arbeit job acquisition with structured native records and explicit pagination evidence.

**Provenance:** derived from the MIT-declared [`german-arbeitsmarkt-mcp@1.0.0`](https://www.npmjs.com/package/german-arbeitsmarkt-mcp/v/1.0.0) distribution by **Greyt GmbH**. This is an independently maintained derivative, not a GitHub fork or an official BA service. See [CREDITS.md](CREDITS.md), [UPSTREAM.json](UPSTREAM.json) and [LICENSE](LICENSE).

## Run

Requires Node.js 20 or newer.

```sh
git clone https://github.com/ahmed-elkashef/german-arbeitsmarkt-mcp.git
cd german-arbeitsmarkt-mcp
npm ci --ignore-scripts
npm start
```

The server uses MCP over standard input/output. Use the top-level entrypoint; the unchanged vendored upstream entrypoints do not include these improvements. No personal profile, account login or credential file is required.

For an MCP client, configure `node` with the absolute path to `src/index.js`:

```json
{
  "mcpServers": {
    "german-arbeitsmarkt": {
      "command": "node",
      "args": ["/absolute/path/german-arbeitsmarkt-mcp/src/index.js"]
    }
  }
}
```

## Tools retained

| Family | Tools |
| --- | --- |
| Salaries | `gehalt_suche`, `gehalt_regionen` |
| Jobs | `job_suche`, `job_details` |
| Apprenticeships | `ausbildung_suche` |
| Study | `studium_suche`, `studienfelder` |
| Further training | `weiterbildung_suche` |
| Coaching | `coaching_suche` |

All nine tools are marked read-only. Five non-job families retain the published upstream clients and schemas; legacy errors are now flagged as MCP errors. The live release proof covers jobs, not the current availability of every non-job endpoint.

## What changed for jobs

- Search uses the current native `pc/v6/jobs` envelope. Full details use the working `pc/v4/jobdetails` route.
- Results provide both `structuredContent` and compatible JSON text. Every record preserves **all** workplaces, addresses and coordinates, source distance, hours flags, remote/career-change flags, raw dates, unknown fields and the full raw source record.
- Original publication, renewal/update and start dates stay separate. Calendar dates remain dates; no midnight, timezone or original instant is invented.
- `job_details` preserves the full description verbatim and reports whether a description is present. It never invents a missing body.
- Page metadata includes the provider's total, page, size, returned count, resolved location, next page and consistency. A source total is not a complete market census or a frozen snapshot.
- Validation rejects invalid pages, page sizes and offering types before network calls. Provider errors, timeouts and HTTP 429 become `isError: true`; `Retry-After` is retained. There are no automatic retries or rate-limit workarounds.

### Inventory without hidden filters

Omit `was` to avoid keyword/title filtering. No role-family, skill, salary, personal eligibility or candidate-fit filter is imposed by this server.

Example arguments to `job_suche`:

```json
{ "wo": "10115", "umkreis": 25, "angebotsart": 1,
  "veroeffentlicht_seit": 7, "page": 2, "size": 100 }
```

Offering types are distinct source partitions: **1 = Arbeit**, **34 = Praktikum**, 2 = self-employment and 4 = apprenticeship. For work plus internships, repeat the same geography/date envelope with types 1 and 34 and follow every needed page in each. Type 1 alone is not all paid work; type 34 does not itself prove student enrolment is mandatory or that an internship is paid.

## Limits

The API is source-controlled and can change or become unavailable. This project does not promise unlimited requests, exemption from rate limits, complete historical coverage, precise original publication instants, or that every indexed vacancy is still open. Verify the resolved location and returned geography; ambiguous place names can resolve to a different city. Source order may be distance order rather than newest-first, so do not stop because one page looks older.

`veroeffentlicht_seit` is a native age filter, not an exact half-open interval. Preserve original source dates, deduplicate by reference, verify boundary dates separately and keep uncertain publication times for review. Follow all pages; missing or inconsistent listing envelopes and errors never count as zero supply. Source records, unknown skills and broad remote labels are not applicant fit or worker eligibility.

This software's MIT licence does not grant new rights over BA/provider content. Upstream shared application identifiers are preserved in the vendored clients; no private user credentials or sessions are included. The server never applies, contacts an employer or sends a proposal.

## Verify

```sh
npm test
npm run test:live
```

Unit and MCP protocol tests cover metadata preservation, date precision, real pagination failure cases, full bodies, offering partitions, validation, timeouts, 429 and all nine tools. The optional live proof makes four bounded job requests through the actual stdio MCP server: work pages 1 and 2, internship page 1, and one full detail. It writes an ignored `.live-test/latest.json` receipt with counts and hashes; it stores no raw bodies or employer contacts in published proof. A successful probe is not full-market coverage.

Release evidence is in [docs/release-proof.json](docs/release-proof.json).
