# Egypt Jobs MCP

Read-only MCP tools for Egyptian public job sources, worldwide remote feeds,
and freelance client projects. Built to make source acquisition reusable,
observable and accessible.
It combines the standalone [Egypt Job Sources Python library](https://github.com/ahmed-elkashef/egypt-job-sources)
with a small JavaScript SDK server over standard input/output.

**MIT licensed.** Credits, exact upstream reference commits and authors are in
[ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) and
[upstream-references.json](upstream-references.json). These are independently
written adapters informed by community references. No fork ancestry, copied
scraper implementation or platform affiliation is claimed.

## Install from GitHub

Requires Node.js 20 or newer and Python 3.11 or newer. Install the Python project
first; this release is distributed as source on GitHub, not through npm or PyPI.

```bash
git clone --branch v0.3.2 --depth 1 https://github.com/ahmed-elkashef/egypt-job-sources.git
cd egypt-job-sources
python3 -m venv .venv
.venv/bin/python -m pip install .
cd ..
git clone --branch v0.3.2 --depth 1 https://github.com/ahmed-elkashef/egypt-jobs-mcp.git
cd egypt-jobs-mcp
npm ci --ignore-scripts
EGYPT_JOBS_PYTHON="$(pwd)/../egypt-job-sources/.venv/bin/python" node smoke.mjs
```

On Windows use the virtual environment's `Scripts/python.exe`. Configure an MCP
client with absolute paths:

```json
{
  "mcpServers": {
    "egypt-jobs": {
      "command": "node",
      "args": ["/absolute/path/egypt-jobs-mcp/index.mjs"],
      "env": {
        "EGYPT_JOBS_PYTHON": "/absolute/path/egypt-job-sources/.venv/bin/python"
      }
    }
  }
}
```

Without `EGYPT_JOBS_PYTHON`, the server uses `python3` on PATH. The Python package
must be installed into that interpreter. Start directly with `npm start`.
The server writes MCP messages to stdout; it does not open a network listener.

## Tools

| Tool | Inputs and behavior |
| --- | --- |
| `read_source_page` | `source`, `page` (default 1), optional `work_model`, Jobicy `cursor`, or board `continuation_url`. WUZZUF pages include hydrated full resources. |
| `read_source_detail` | `source` and canonical public `url`; no generic URL fetch. |
| `wuzzuf_work_model_taxonomy` | Blank-query Egypt employment facets and selected country. |
| `jobicy_location_taxonomy` | Current official location slugs. |
| `parse_rendered_board_page` | Source and exact `{url,kind,captured_at,html}` public DOM object; no network or browser control. |
| `read_saved_board_capture` | SHA-256 receipt only; verifies and reparses original local evidence. |
| `remote_source_capabilities` | Access, attribution, pagination and completeness limits for each global feed. |
| `read_remote_feed` | `source`: `remotive`, `remoteok`, `weworkremotely`, `workingnomads`, or `himalayas_global`; optional exact returned cursor for Himalayas only. All returned listings, without title/keyword filters or text slicing. |
| `freelance_source_capabilities` | Public Freelancer and approval-gated Upwork contracts and limits. |
| `read_freelance_projects` | `source`: `freelancer` or `upwork`; `limit` 1–100, default 20. Freelancer uses `offset`; Upwork uses its returned `cursor`. |
| `read_freelance_project_detail` | Source and a numeric `project_id`. Full client brief; no bids, profiles, messages or files. |

Supported sources: WUZZUF, Forasna, ArabJobs, Bayt Egypt, Himalayas, Jobicy and
Mostaql, plus the worldwide feeds and freelance routes above. WUZZUF models include `full_time`, `part_time`, `freelance_project`
(`freelance` alias), `internship`, `shift_based` and `volunteering`; omission means
broad Egypt inventory. No keyword, career-title, skill or seniority filter is
exposed. Source labels do not establish actual hours or candidate suitability.

Example tool input:

```json
{"source":"wuzzuf","page":1,"work_model":"part_time"}
```

## Source capabilities and limits

| Source | Route | Limit |
| --- | --- | --- |
| WUZZUF | Transparent anonymous public JSON:API, 15/page and full-resource hydration | Undocumented frontend contract; can change. Public start is a page index, API startIndex is a card offset. |
| Forasna | Operator-authorized public browser DOM | Ordinary HTTP may be denied. Click visible Next and verify URL/active page/IDs: href offsets and rendered UI actions can disagree. No inferred numbered offsets. |
| ArabJobs | Country-only Egypt HTTP, newest-first pager and canonical details | Archive-like inventory and sparse descriptions may not represent active vacancies. |
| Bayt Egypt | Public page and JobPosting parser | HTTP access may be denied; failures remain visible. |
| Himalayas | Official country-filtered API | Egypt includes worldwide listings. Preserve canonical source attribution; verify location/hours. |
| Jobicy | Official global cursor feed and taxonomies | Seven-day window. Start new polling passes no more than hourly; cursor requests can complete one pass. |
| Mostaql | Public client-project list and scoped brief/terms | Posted project budget is not salary or earned income; scope, fees, hours and payment access need review. |
| Remotive | Official global JSON feed | 24-hour delay; cache responses and observe the provider's limit of four fresh fetches per day. Attribution required. |
| Remote OK | Public JSON feed with source legal metadata | Recent snapshot, not a historical census. Preserve source name and canonical links; descriptions may be abbreviated. |
| We Work Remotely | Official all-jobs RSS | Current feed window only; public source text may omit details. Canonical listing review required. |
| Working Nomads | Public footer-linked JSON endpoint | Exposed snapshot; no verified historical exhaustion or description completeness. Source reuse restrictions apply. |
| Himalayas global | Official full global cursor feed, 20/page | Daily refresh; follow exact returned cursor. Location, timezone, pay currency and pay period need review. |
| Freelancer.com | Public active-project API and numeric-ID detail | Moving offset inventory; full briefs, original budgets and commitments. Only public project fields retained; no account required for these reads. |
| Upwork | Fixed read-only GraphQL marketplace queries | Approved API application, authorized scopes and OAuth access token required. Browser login alone is insufficient. No live authenticated API verification is claimed. |

Successful text acquisition is not a model review or a completed market census.
Responses retain `coverage_complete=false` and `reviewed_by_model=false`.
Access, structure, identity or hydration failures are `source_limited`; they
never become fabricated zero jobs. Raw dates with unknown timezones stay raw.
Keep source-owned content private and follow [SOURCE_POLICY.md](SOURCE_POLICY.md).
The MIT license covers authored software, not third-party listings or site data.

### Upwork activation

The server reads `UPWORK_ACCESS_TOKEN` only from its machine-local environment.
Obtain it through an approved Upwork API application with the required read
scopes; never pass browser cookies, session tokens or credentials as tool inputs.
Missing approval/token returns an explicit `api_approval_required` limitation.
See [Upwork's API requirements](https://support.upwork.com/hc/en-us/articles/115015857647-How-to-request-an-API-key-from-Upwork).
Only fixed marketplace search/detail queries are implemented. No arbitrary
GraphQL or account write operations are exposed. Canonical job URLs stay null
when the verified query contract does not supply one.

### Bounded acquisition

Remote HTTP bodies are limited to 25 MiB; MCP Python subprocess output is limited
to 64 MiB and 55 seconds. Serialized MCP results are bounded to 9 MiB to fit
common SDK client buffers; larger complete results return `source_limited` and
can be acquired through the Python CLI into private storage. No partial listings
are returned. Oversize output, timeouts and malformed responses are
visible limitations, never silently truncated listings or empty supply. Feeds
without a cursor return `has_more=null`; a snapshot does not prove exhaustion.
Native work-type and worldwide labels may conflict with descriptions. Resolve
actual hours and country restrictions after reading the full canonical text.

## Browser evidence handoff

The Python package's `egypt-job-capture serve` starts a loopback-only local form.
Run it with the same interpreter configured for this MCP, open its printed local
URL, and transfer selected public DOM from a browser you are authorized to use.
The standalone `captureEgyptBoardDOM` function in
[browser-extract.mjs](browser-extract.mjs) validates the public page scope before
reading content. Copy the function without its `export` keyword into your
browser tool's read-only DOM evaluator and call it with
`{source:'forasna',kind:'page'}` or `kind:'detail'`.

Submit the exact capture object through the local form and inspect the saved
receipt. Call `read_saved_board_capture` with its SHA-256. The capture tool keeps
immutable receipts in the user's local cache; `EGYPT_JOBS_CAPTURE_DIR` can select
another local directory. It never reads cookies, session storage, hidden account
state or applicant data. Stop the receiver after use. It does not drive a
browser, solve challenges or widen access.

## Development

Install the Python library into your test interpreter, then:

```bash
npm ci --ignore-scripts
EGYPT_JOBS_PYTHON=/path/to/python npm test
node smoke.mjs
```

Tests use synthetic payloads and make no source-site network requests. GitHub
Actions tests the MCP against the paired Python library. Contributions are
welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Do not submit real captures,
candidate records, credentials or downloaded job corpora.

## Official employer boards

Version 0.3.0 adds `ats_source_capabilities`, `read_employer_board`, and `read_employer_job_detail` (fourteen read-only tools total). Each board call requires an explicit confirmed provider/board token. Greenhouse/Ashby use official whole-board responses; Lever uses skip/limit and global/EU endpoints. Only Greenhouse/Lever have documented individual detail reads here. No employer-domain guessing, arbitrary URL target, application, candidate data or internal posting access. Full text and stable IDs are preserved; API failures remain limits. A board snapshot is not a geographic or frozen-week census.

### Freelancer activity intervals

`read_freelance_projects` accepts paired aware RFC3339 `from_time` and `to_time` only for `source:freelancer`. For example, freeze `2026-01-01T12:00:00Z` to `2026-01-03T12:00:00Z` and repeat those exact values on each returned-offset page. Native date filters constrain **update activity**; the backend separately reports exact `[start,end)` submission-window classification. Missing or conflicting source timestamps remain undetermined, and every public row and raw pagination count remains intact. Known activity outside the requested native interval produces an explicit limitation. These parameters do not establish first-ever creation, an exhaustive market census or immunity to provider limits. No date argument is accepted for Upwork or detail reads.

The native hourly commitment value is a billing limit, often the default 40 hours per week, rather than proof of mandatory full-time attendance. Actual required hours must be established from the brief.
