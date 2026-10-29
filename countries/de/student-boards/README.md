# Public student boards

Original read-only readers cover Jobmensa and the StudentJob/YoungCapital family.
They check current robots policy before every resource read. Unknown layouts,
changed partitions, oversized responses and access failures produce explicit
limited results with a null listing count, never a successful empty market.

## MCP

- `de_public_jobmensa_capabilities`, `de_public_jobmensa_page`, `de_public_jobmensa_detail`.
- `de_public_student_boards_capabilities`.
- `de_public_student_board_page`, `de_public_student_board_detail`,
  `de_public_student_board_resolve_external`, each with source `studentjob` or `youngcapital`.

Only exact public origins and observed native paths/query fields are accepted.
No title, career, education or keyword inventory filters are supported. Jobmensa
supports its observed contract-category facets. StudentJob/YoungCapital accept
observed native job-type IDs and verify the actual selected controls. An explicit
sort must be echoed by the native page. Pagination follows actual native links,
retains the partition and cannot silently skip a page. Redirects cannot change
requested page, partition or vacancy identity.

StudentJob/YoungCapital preserve every primary native card, including promoted
cards and external marketplace redirects. External records are not dropped and
are not assigned invented native body URLs or employers. Their redirect route
can be denied by current robots; that is an access result. The optional resolver
performs only a permitted HEAD and returns a Location without fetching the target.
A target still needs separate identity and policy verification. No denied-route
GET/browser/proxy workaround is implemented.

Detail results retain the complete visible native description and extra facts,
plus the original JobPosting. Native working-student labels can conflict with
schema INTERN; schema identifier can be a placeholder. The numeric listing URL
ID remains the source identity, while contradictory fields remain evidence.
Germany-market pages include foreign worksites. Neither source-country headings
nor contract facets establish applicant eligibility, hours, remote-worker country,
academic recognition or a current hiring state. No fit decision is automated.

Set `JOB_MARKET_CAPTURE_DIR` to an explicitly private local directory to retain
content-addressed complete anonymous HTML. Raw pages, form nonces, real vacancy
corpora, applicant data and credentials must not enter this public repository.
Code licensing does not grant permission to republish job content.

These transports do not establish a frozen historical week or complete market.
They make no login, save, account, email, application, subscription or contact action.
Synthetic regressions run with the other retained Python suites. Bounded live
engineering evidence is recorded separately in `docs/*live-proof.json`.
