# Changelog

## 0.3.2

- Paired aware `from_time` / `to_time` options on Freelancer search only, forwarded to Python v0.3.2 with exact raw-offset continuation.
- Explain native update activity versus exact submission-window classification, unknown timestamps and the default hourly billing limit.
- Refuse partial/cross-source date arguments and preserve read-only scope; no new tools or application actions.
- Require backend v0.3.2 for the date options and full WUZZUF work-model taxonomy.

## 0.3.1

- Require Python backend v0.3.1 in installation/CI to restore strict full-feed parsing of native Remote OK, Working Nomads and Himalayas job-link shapes.
- Preserve a missing exact vacancy link as an explicit record gate rather than an empty feed. Tool names/read-only scope remain unchanged.

## 0.3.0

- Three new read-only tools, fourteen total: ATS capabilities, explicit employer board, and exact Greenhouse/Lever job detail.

- Explicit employer-board readers for the official Greenhouse, Lever and Ashby public contracts.
- Retain stable posting IDs and complete native descriptions and location/model/date/compensation fields.
- Distinguish whole-board snapshots from Lever pages and geographic/weekly coverage.
- Failed transport or malformed payloads remain explicit limits instead of fabricated empty supply.
- Exact board tokens, fixed trusted endpoints, and synthetic boundary/pagination/full-text checks.

## 0.2.0

- Five new read-only tools, eleven total, for worldwide remote feeds and freelance projects.
- Remotive, Remote OK, We Work Remotely, Working Nomads and Himalayas global adapters.
- Public Freelancer project pagination/full briefs and approval-gated Upwork GraphQL reads.
- Fixed source scope, honest snapshot continuation, preserved full returned text and source attribution.
- Explicit structured approval limitations survive backend exit code 2; bounded 64 MiB transport.
- Serialized MCP output bounded to 9 MiB with honest Python CLI fallback; oversize results never disconnect common clients or slice listings.
- Synthetic regression tests for large output, pagination and credential boundaries.

## 0.1.0

- Initial standalone MIT release with six read-only MCP tools.
- Portable installed Python backend, without a private repository dependency.
- Public source and capture boundaries, exact capture schemas and immutable receipts.
- Operator public-DOM helper with early URL validation.
- Synthetic offline tests, upstream attribution and source content policy.
- Pinned SDK 1.32.1 and dependency lockfile.
