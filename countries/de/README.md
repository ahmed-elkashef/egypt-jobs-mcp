# Germany

The Germany package consolidates original StepStone implementation and the maintained BA derivative, including its nine existing job/salary/education/training/coaching tools. Country tools are applicant-neutral and preserve original source evidence.

- [arbeitsmarkt/](arbeitsmarkt/): structured Jobsuche v6 list, full v4 detail and all workplaces/dates, with salary, Ausbildung, study, training and coaching families. Original Greyt GmbH distribution and notices remain intact. Five retained non-job families require their own current live verification; jobs success does not certify them.
- [stepstone/](stepstone/): independent complete HTML/native-record parser, current robots-aware HTTP access, exact geography/query preservation, resumable checkpoints and explicit errors. The new module entrypoint and read-only annotations make the same implementation available through the unified MCP.
- [student-boards/](student-boards/): original Jobmensa public list/detail reader, exact native partitions and pagination, current robots checks, complete native structured descriptions and explicit source limits. Its three read-only tools run through [public-services/](public-services/), alongside the credential-gated Interamt API.
- Shared ATS, native public feeds and full snapshot/detail retrieval are registered once; country eligibility is not inferred from a global feed label.

For vacancy inventory, BA work, internship, apprenticeship and self-employment offerings are distinct partitions. Native age filters are not exact publication instants, resolved geography must be inspected, and distance ordering does not justify early date stopping.

The German universe register also includes public-sector/state/municipal portals, major/local/specialist boards, universities/research/hospitals, students/apprenticeships, staffing, direct-employer discovery and freelance client demand. Statistical context and education/training remain separate from vacancies. These branches are not silently reduced to BA or StepStone.

Original additional adapters are still required for the registry's research entries. Interamt and Karriere.NRW publish API surfaces; access/authorization must be established rather than defaulting to browser scraping. Account matching platforms and denied routes remain explicit external limits. [Coverage](../../docs/coverage.md) identifies the exact gap categories.

Original shared [d.vinci publication tools](../../shared/dvinci/README.md) read
complete compact metadata and full native bodies for explicit employer portals.
They do not narrow acquisition by candidate interests or infer student/remote
eligibility from configurable employer labels. Two tested portals are examples,
not a German employer census or historical weekly supply.
