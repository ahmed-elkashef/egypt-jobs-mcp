# Germany student boards

Original Jobmensa public list and full JobPosting reader. Source adapters remain
separate from applicant fit, country coverage and application actions.

The reader checks the current robots policy before each page and follows only
the exact public HTTPS origin. Supported native list query fields are contract
categories, city coordinates/location/radius and source page. Career keywords,
unknown categories, duplicate parameters, arbitrary paths and foreign redirects
are refused. Continuation comes from actual page links and cannot change the
partition. A native terminal is a candidate display endpoint, not a frozen
historical census. Native categories may include mixed or promoted contracts.

Unified read-only tools:

- `de_public_jobmensa_capabilities`
- `de_public_jobmensa_page`
- `de_public_jobmensa_detail`

CLI from the repository root:

```sh
.venv/bin/python countries/de/student-boards/jobmensa.py --capabilities
.venv/bin/python countries/de/student-boards/jobmensa.py --operation page --url 'https://www.jobmensa.de/jobs-suchen?categories=internship'
```

`JOB_MARKET_CAPTURE_DIR` optionally saves full source HTML in content-addressed
machine-local storage before parsing. Keep it outside version control: full HTML
may contain ephemeral form or tracking material. Results retain a source hash,
all visible native cards, counter, real continuation, original full detail HTML
and JSON-LD. A returned body is not a complete qualification review. Dates,
hours, employment type, workplace and worker-country fields remain separate;
contradictions are not silently resolved. Apply links are never followed.

Live source tests belong in a consumer's private evidence store. Public tests
use synthetic fixtures and mock policy access; no job datasets or applicant
information belongs in this repository. No browser, account, contact,
subscription or submission action is implemented.
