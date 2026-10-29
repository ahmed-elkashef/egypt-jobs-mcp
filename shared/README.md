# Shared sources

Country packages reference the same public feed and employer-board implementations rather than copying a global adapter into every country.

- [public-sources/](public-sources/): complete native Arbeitnow/Remotive/RemoteOK/Himalayas/The Muse/Personio/Recruitee responses, process-local snapshot/detail reads and retained legacy tools with their explicit limits.
- [Python source adapters](../packages/source-adapters/): preserved `egypt_job_sources.remote`, `.ats`, `.freelance` and `.public_apis` interfaces for global feeds, exact Greenhouse/Lever/Ashby boards and public client projects. Their historical Python namespace is retained for installed-client compatibility; it is not an Egypt-only scope restriction.

Exact employer tokens must come from a maintained country employer census. An ATS parser and an example board do not enumerate a country's employers. Global/remote labels do not prove a worker can do the job from Egypt or Germany. Snapshot expiry, history windows, full-text limits, attribution, provider permissions and original-time uncertainty remain in every source contract.

LinkedIn, authenticated native Upwork, Trackly and other account services are represented as external connectors. This repository does not copy accounts or sessions or automatically obtain access.
