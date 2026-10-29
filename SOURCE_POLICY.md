# Source and action policy

This repository publishes reusable read-only code and synthetic tests. It contains no harvested vacancy corpus, candidate profiles, application tracker, private workflow state or credentials. Native provider terms, content rights, authentication, robot policy and rate limits remain source-specific.

The root MCP exposes a fixed allowlist of audited read operations. It never applies, messages, bids, pays, opens accounts, changes a profile or runs arbitrary provider queries/mutations. A newly added backend tool does not become available automatically. Credentials, cookies and account sessions remain in the caller's local environment; they are never included in tool discovery or published proof.

Prefer official APIs, documented feeds, permitted public HTTP and verified employer ATS contracts. Respect denials, CAPTCHA, authentication and rate limits. There is no fingerprint impersonation, proxy rotation, cookie extraction, private account API fallback or automatic challenge workaround. Preserve `Retry-After` and explicit source limitations. Browser-dependent sources remain labelled as such rather than advertised as browser-free.

Inventory, original publication/renewal/start/expiry dates, complete details, exact interval membership, source traversal and applicant review are separate. Never invent missing descriptions, dates, countries, worker eligibility, salary units or zero-result success. Never add source totals into a supposed national market size. Education/training supply and freelancer profiles are not vacancy/client demand.

Provider-specific policies remain with the components: [Egypt](countries/eg/mcp/SOURCE_POLICY.md), [Python sources](packages/source-adapters/SOURCE_POLICY.md), [StepStone](countries/de/stepstone/README.md), [BA](countries/de/arbeitsmarkt/README.md) and [shared feeds](shared/public-sources/README.md).
