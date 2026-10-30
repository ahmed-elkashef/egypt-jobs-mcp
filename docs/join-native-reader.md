# Original JOIN employer board reader

Version 0.4.18 adds `source: "join"` to the existing read-only German public-board inventory/detail tools. Pass an exact employer board URL identified from an official source. There is no default country or employer census and no title, category, experience, keyword or candidate filter.

```json
{"source":"join","url":"https://join.com/companies/join"}
```

Follow the exact returned `pagination.next_url`. Freeze both `source_result_count` and `native_total_including_general_context`, reconcile unique native job IDs and retain all page receipts. A complete current response does not establish a historical week or original publication.

## Two public data layouts

The original parser reads complete anonymous HTML and its typed `__NEXT_DATA__` JSON as data. Both observed `initialState` and `pageData` layouts are supported, including the native dynamic page route. Company identity, exact source query/filter echo, pagination types, native row counts and rendered job anchors must agree. Competing layouts, missing data, reset pages, mismatched counts and hidden filters fail explicitly. The reader exports only public job/company fields; it does not export account/hydration state.

## Vacancies and general application context

The source pagination total includes an enabled spontaneous-application slot. That slot is recorded separately as general context and never becomes a vacancy or application candidate. The native UI can have an extra final page: it repeats the preceding native job rows as cached source data. `native_cached_noncurrent_rows` retains those rows, while `listings` stays empty on that virtual page. Every actual job appears once across source continuation.

The captured engineering test observed four actual vacancies and one context slot on JOIN's own board. A separate vendor-advertised 1KOMMA5 board exposed 135 actual vacancies across 27 real pages and a 28th virtual page, with a native UI total of 136. All native pages were traversed through the real MCP; these are dated source-format observations, not national counts. Crucially, the employer's current official careers page points to Personio. The JOIN format sample is not substituted for that primary employer source, and cross-provider requisition identity is not inferred.

## Full primary content and identifiers

The complete native primary job HTML must also be present in rendered source text. Preserve it separately from the JobPosting schema description, public company context and structured employment/location/date facts. A schema summary never replaces the primary. Internal job ID, current URL publication ID and earlier requested URL ID are distinct. Only an advertised, connected chain of same-company numeric job redirects can establish the canonical public URL.

Native creation/update dates, source schema dates, `Employee`, full-time, country, onsite/hybrid and remote-region labels remain source facts. They do not establish an original publication instant, an exact student contract, Germany-based remote work permission or applicant fit. Source closed status is retained separately.

## Boundaries and validation

Runtime requests are anonymous first-party robots and HTML GETs. No credentials, cookies, source scripts, images, candidate/account routes, general-application pages, submissions, contact or subscriptions are supported. Source client code was inspected only as text during independent protocol discovery; none was executed or copied into this implementation.

Twenty-six synthetic Python regressions cover both layouts, the virtual page, native identity/count conflicts, hidden filters, primary/schema separation, nested company state, source clock/eligibility uncertainty, policy refusal and scoped redirects. The three supported clean CI combinations also run the existing source suites. Actual probe receipts contain only aggregate/hashes in the public repository; consuming applications keep raw job evidence privately.
