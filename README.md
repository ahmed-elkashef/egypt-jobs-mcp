# Job Market MCP

One source repository for country-based labour-market tools. Egypt and Germany are the first country packages. Public feeds, employer ATS readers and client-project adapters are shared. More countries can use the same contracts without copying another country's implementation.

The repository was renamed from `egypt-jobs-mcp`; its existing Git history and releases are preserved. It consolidates the authored Egypt adapters, the Germany BA derivative, the original StepStone implementation and the shared public-source server. Exact imported commits and retained licences are in [import provenance](docs/import-provenance.json) and [credits](ACKNOWLEDGMENTS.md).

## Install and run

Requires Node.js 20+ and Python 3.11+.

```sh
git clone https://github.com/ahmed-elkashef/job-market-mcp.git
cd job-market-mcp
python3 -m venv .venv
.venv/bin/python -m pip install -e packages/source-adapters -e countries/de/stepstone
npm ci --ignore-scripts
JOB_MARKET_PYTHON="$PWD/.venv/bin/python" npm start
```

`server.mjs` exposes the unified stdio MCP. Set `JOB_MARKET_PYTHON` to the absolute Python executable in your MCP client's environment; use the absolute `server.mjs` path as its Node argument. No sibling checkout or account login is needed for the public adapters. Account-based external services remain separately configured.

The original Egypt-only `node index.mjs` entrypoint remains available. Python imports/CLI names under `egypt_job_sources` are preserved for compatibility. `private: true` in the npm manifest prevents accidental npm publication; it does not describe GitHub repository visibility.

## Country packages and tools

| Package | Included implementation | Unified tool prefix |
| --- | --- | --- |
| [Egypt](countries/eg/README.md) | WUZZUF, Forasna, ArabJobs, Tanqeeb, Akhtaboot, Bayt and Mostaql readers; native public DOM recipes where HTTP is unavailable | `eg_` |
| [Germany](countries/de/README.md) | Structured BA jobs; salary, study and training; original StepStone, Interamt and public student-board readers | `de_ba_`, `de_stepstone_`, `de_public_` |
| [Shared](shared/README.md) | Native public feeds, complete snapshot/detail retrieval, direct ATS boards and public client-project reads | `shared_` |

Four catalogue tools work without acquiring jobs:

- `list_countries`: packages and actual local backend readiness.
- `list_country_sources`: national and shared sources, current implementation gaps and access conditions.
- `source_capabilities`: one source's supported routes, fixed arguments and native tool schemas.
- `plan_country_scan`: a plan for explicit geography and offset-aware `[from,to)` dates, retaining unresolved sources.

[The source registry](sources.json) currently contains 93 distinct source/channel entries. It is an open discovery register, **not proof that every Egyptian or German employer or vacancy is represented**. Entries explicitly distinguish implemented readers, access-limited routes, employer-seeded readers, credential requirements, external connectors, research gaps and statistical context. [Coverage](docs/coverage.md) explains the remaining work.

## End to end

1. Resolve the country and source capabilities before acquiring supply.
2. Enumerate genuine native geography/model partitions and pagination; do not hide title, role or skill filters in an inventory route.
3. Preserve each native response, IDs, source/observation dates, continuation and access errors in the consumer's private evidence store.
4. Hydrate complete descriptions and requirements, then reconcile duplicates, changed/reopened postings and uncertain publication clocks.
5. Evaluate eligibility or applicant fit in the consuming application. A read, source total, native terminal or registry entry never proves a complete frozen market.

The federation forwards full native responses without shortening job descriptions. It exposes an explicit read-only tool allowlist, namespaces tool identities and isolates backend failure. Unknown/new backend tools are not enabled automatically. Oversized results fail explicitly rather than returning truncated descriptions. Child processes are owned by the server and closed with it.

## Germany public boards

The original [Jobmensa, StudentJob and YoungCapital readers](countries/de/student-boards/README.md) enumerate complete public native pages and full visible job details without a browser. Current robots policy, exact native continuation and model/date/worker-country ambiguities remain explicit. It makes no account, contact or application action.

The original [public-board readers](countries/de/public-boards/README.md) also cover Absolventa, academics, stellenanzeigen.de, Yourfirm, GermanTechJobs and the permitted official government vacancy feed. Native full bodies, verified pagination and distinct clocks remain separate from coverage and applicant fit.

## Additional Germany API

Original Interamt capability/list/detail code is included under `countries/de/interamt`. Its public OpenAPI requires an approved API key; single-customer and MultiMandant scopes remain distinct. `de_public_interamt_capabilities` inspects this offline; `de_public_interamt_read` refuses before network without approved local access and an explicitly confirmed API base. No authenticated live access is claimed.

## Browser use and limits

API, feed and ordinary authorized HTTP routes are the default. A browser is a last transport option where a maintained source actually requires it. Forasna/Tanqeeb's existing runners remain explicit browser-dependent routes. StepStone checks its current route policy and does not turn denied pagination into a fake empty market. LinkedIn, Upwork and similar account services are external access boundaries, not anonymous scraper fallbacks.

A country package is complete only when every required registered source has tested discovery, native partitions, continuation, complete details, clock evidence and honest access results. Today's consolidation does **not** claim that the remaining Germany/Egypt research entries are implemented. [Architecture and workflow](docs/architecture.md) records the exact ownership and migration boundary.

## Verify

```sh
.venv/bin/python -m pip install -e 'packages/source-adapters[dev]' -e 'countries/de/stepstone[test]'
JOB_MARKET_PYTHON="$PWD/.venv/bin/python" EGYPT_JOBS_PYTHON="$PWD/.venv/bin/python" npm test
npm run check
.venv/bin/python scripts/test-python.py
```

Tests use synthetic data, mocked source requests and real local stdio MCP connections. The Python receiver test binds an owned temporary loopback port. Live probes are separate and bounded; no source census, account connection, application, message, bid, purchase or monitor starts from installation or testing. See [source policy](SOURCE_POLICY.md).
