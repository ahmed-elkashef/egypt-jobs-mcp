# Changelog

## 0.4.2

- Add original Germany Jobmensa public page/detail tools with current robots checks, strict native URL/continuation validation, complete JSON-LD and private raw capture.
- Keep mixed models, source dates, hours and worker-country constraints separate; no account or application action.
- Extend offline protocol and synthetic parser tests. Country registry remains an open discovery register.

## 0.4.1 — 2026-10-29

- Preserve BA v6's native `stellenangebotsart` ahead of legacy offering aliases;
  retain source enum values without inferring a precise employment model.
- Preserve Arbeitnow's officially linked Netherlands posting URLs in mixed
  native pages. Keep the fetch endpoint and continuation scope fixed, complete
  bodies intact, and hostile lookalike domains rejected.
- Package versions: German Arbeitsmarkt 1.1.1 and Python source adapters 0.3.6.
  No new source, country-eligibility or frozen-market completeness is claimed.

## 0.4.0 — country consolidation

- Rename the existing Egypt MCP repository to Job Market MCP and preserve its history and releases.
- Consolidate Egypt Python/MCP, German BA, original StepStone and shared public-source code with exact provenance and licences.
- Add a country source registry, explicit capability/gap inspection and frozen scan-plan tools.
- Add a unified read-only stdio federation with native tool namespacing, complete result forwarding, explicit backend/size limits and owned process cleanup.
- Preserve the legacy Egypt entrypoint and Python imports. Add StepStone module startup/read-only annotations and update Zod to the audited patched version.
- Registry entries without working transport remain gaps; this release does not claim complete national-market coverage.

Earlier Egypt release history: [countries/eg/mcp/CHANGELOG.md](countries/eg/mcp/CHANGELOG.md).
