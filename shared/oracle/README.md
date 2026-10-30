# Original Oracle Candidate Experience reader

This independently authored reader supports the external JPMC site CX_1001,
linked from the official JPMorganChase careers page. The native public shell
advertises its API base and site number. Its advertised public Oracle client
identifies the anonymous search and complete-description GET contracts.
Discovery read the client as text; no vendor JavaScript was executed or copied
into this implementation.

The three shared tools are oracle_capabilities, oracle_inventory and
oracle_detail. Capabilities is offline. Inventory accepts the exact qualified
board URI, an optional DE country partition, a page and a frozen first-page
total for continuation. Omitting country reads the complete external site.
It accepts no candidate, keyword, role, department or date filter.

The native search response contains one search item. Its outer count,
hasMore, limit and offset are container metadata. The actual job inventory
uses that item's TotalJobsCount, Limit, Offset and requisitionList. Every page
must reconcile the requested site, native country location ID, default order,
complete row count, unique identities and frozen first total. Unknown,
partial, changed or denied responses have null counts. An explicit validated
zero-job search differs from a missing search container.

Detail uses the returned public posting URI and its native ById finder.
It retains the complete external primary description, responsibilities,
qualifications, corporate description and organization description separately,
including empty optional sections. Safe rendered HTML and source public
fields remain available. Internal descriptions, hiring-manager fields,
application controls and their values are excluded from the output. Native
job and requisition IDs are different identifiers.

Only this source uses a narrowly qualified robots policy: its robots resource
currently returns 403 while the publicly advertised job shell and anonymous
job API return 200. RFC9309 section 2.3.1.3 treats an unavailable robots resource
separately from content access. Actual content denial is never retried through
another route; throttling, inaccessible policy and malformed rules stop.
Existing shared HTTP policy and older readers are unchanged.

The dated native discovery reconciled all 50 Germany postings across two
25-row pages. A global first page advertised 7,257 jobs; that global inventory
was not exhausted. Three full bodies were checked. These are source and
protocol observations, not a national employer census, a frozen historical
week, applicant fit or proof of permission to work remotely from Germany.
The separately numbered CX_1002 and other employer sites require their own
authoritative discovery and qualification.

Raw posting dates, Campus/regular labels and part/full-time schedules are not
precise student eligibility rules. The visible body controls enrollment,
graduation, hours, deadlines and language requirements.

Primary references:

- https://www.jpmorganchase.com/careers
- https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs
- https://docs.oracle.com/en/cloud/saas/human-resources/farws/op-recruitingcejobrequisitions-get.html
- https://www.rfc-editor.org/rfc/rfc9309.html

The subsequent [actual unified MCP proof](../../docs/oracle-live-proof.json)
reconciles all 50 Germany IDs and global pages 1, 2 and 291 against the later
native total of 7,266. It reads three complete public bodies and correctly
refuses an unqualified site, unbound continuation and application URI. The
global inventory remains partial. All 650 local repository tests pass
(140 Node, 510 Python); release CI and installed-runtime qualification are
separate deployment receipts. Public proof contains aggregates and hashes.
