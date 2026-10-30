# Architecture and migration

## Ownership

One repository owns reusable code, source contracts, country discovery registers, synthetic fixtures, protocol tests and release proof. A consuming private application owns people, exact frozen runs, raw evidence, candidate decisions, packages, manual tracker progress and notifications. None of that private state is included here.

Country packages own national sources and country-specific discovery/partition semantics. Shared implementations own cross-country feeds/ATS/client-project transport. The registry links these without claiming that a global feed is locally eligible or that one aggregator is a whole labour market.

Shared ROR release/country-directory readers belong in `shared/ror`, not a
German-specific adapter. Their complete immutable DE/EG research-organisation
records remain typed discovery context, including native inactive/withdrawn
records. The verified full dump, checksum-bound local segments, source licences
and directory-versus-vacancy boundaries are documented in
[ROR contracts](../shared/ror/README.md).

## Execution

The unified server starts five owned stdio backends: Egypt, German BA, German StepStone shared public sources and the new original Interamt reader. Each executable is inside this checkout. Python source paths are bound to this checkout, with a caller-selected Python runtime. No sibling checkout is a runtime dependency.

The federation discovers only an explicit audited read-tool allowlist, preserves native schemas and complete results, namespaces tools and exposes backend readiness. A failing optional backend does not erase the country registry or working tools. New backend tools are not inherited automatically. Stderr is drained locally, not copied into a public tool result. Complete oversized responses become a source limit, never sliced job bodies. Shutdown closes the owned subprocesses.

The four catalogue tools do no acquisition. Source routes are transparent native tools plus fixed arguments. A scan plan preserves explicit geography and aware `[from,to)` bounds and includes unresolved sources; it never starts a scan, monitor or personal workflow.

## Existing Egypt path

The Python package owns source parsing, native pagination, full descriptions, source identity, date precision and failure semantics. Its public DOM receiver accepts scoped public content with immutable receipt hashes; it does not control or export a browser session. The maintained browser runner drives genuine native controls through an authorized caller-injected browser and saves evidence through the local handoff. It is a distinct transport, not an HTTP implementation or permission to bypass a denial.

Personal intake/lease/window/hours controls from a consuming application are not part of this source server. They should continue to wrap acquisition in that application. Renaming this source repository does not change a running source process, installed wheel, account, application interval or tracker row.

## Compatibility and releases

The existing root `index.mjs` continues Egypt-only stdio. `server.mjs` is the unified entrypoint. Original Python module and CLI names remain supported. Existing tags/releases stay in the renamed repository; old dependency URLs are not rewritten blindly. The four source repositories imported here remain untouched historical origins; no deletion, archive or visibility change is part of this migration. Future reusable development belongs here, and consumers should migrate through a tested release rather than editing live configuration silently.

Exact source commits and original licence files are retained. Vendor code is clearly marked as derived; original code is not misattributed. The npm private flag prevents registry publication and is independent of GitHub visibility.

## Adapter acceptance

A new source needs discovery evidence, exact native geography/models, stable identity, complete list/detail parsing, real continuation/exhaustion semantics, original/update/expiry/observation clocks, explicit access/terms/rate limits, synthetic tests and a bounded live protocol proof. Browser fallback is allowed only after permitted API/feed/HTTP possibilities are investigated and its remaining requirement is explicit. Failed, inaccessible, capped and unimplemented states cannot become successful empty markets.

A maintained register is open-ended: country completion is evidence against a declared source/employer scope, never an unsupported promise about all formal, informal, referral or closed hiring.
