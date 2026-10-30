# Original SAP SuccessFactors RMK reader

This anonymous reader qualifies the employer's actual legacy board at
https://careers.sap.com/search/. SAP's current
https://jobs.sap.com/en/jobs/ front explicitly links to this older site.
The two fronts are separate supplies; this implementation does not claim the
new front, reconcile their counts, or enumerate other SuccessFactors employers.

The original code supports:

- shared_successfactors_capabilities: offline origin and protocol contracts.
- shared_successfactors_inventory: all roles on a native page, optionally
  within the verified Germany (DE) or Egypt (EG) country partition.
  The source range, total, page count, row identities, native country heading,
  sort and advertised next links must agree. Later pages require the frozen
  first-page total. No job-title, department, career-status or language filter
  is accepted.
- shared_successfactors_detail: an exact returned legacy URI, its complete
  description, separate full job display and raw sidebar fields. The native
  URL-site ID and employer requisition ID are distinct.

The currently qualified search component has 25 rows per page. Other employer
origins and configurations require independent qualification. Missing ranges,
recommendation/Top Jobs fallbacks, unknown zero-result templates, ignored
filters, changed totals and unsupported routes fail with null counts; no
partial page or inaccessible source is reported as an empty market.

Native posted dates and schema clocks are evidence rather than verified first
publication instants. Career Status: Student and
Employment Type: Limited Full Time can coexist; they remain separate source
facts. Neither label establishes internship/working-student eligibility,
Germany-based remote permission or individual fit. Additional locations may
appear outside the primary list location.

Every read checks the origin's robots policy. Only the qualified search and
returned job routes are requested; redirects are refused. No application,
talent-community, alert, account, cookie, key, script/CDN or contact operation
is implemented. Responses and IPC output are bounded without clipping bodies.

The [dated live proof](../../docs/successfactors-live-proof.json) records actual
unified MCP reads on 30 October 2026. Global first/second/last pages reconcile
against 608 current legacy jobs; all five German pages reconcile 122 unique
metadata identities and Egypt's one page reconciles four. Three complete
primary descriptions and all identity/clock contracts passed; the modern-front,
unbound-continuation and application-route requests were correctly refused.
These are separate current partitions, not historical weeks or national
coverage. All 622 local repository tests pass (135 Node and 487 Python), including
29 new Python and five new Node cases. Clean release CI, publication and
installed-runtime qualification remain separate deployment receipts.
