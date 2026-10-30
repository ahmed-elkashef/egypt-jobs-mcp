# Original native ROR directory reader

`shared_ror_release` resolves the official public concept
<https://zenodo.org/records/6347574> to its exact advertised version-specific
record. It returns native `Retry-After` as `record_read_not_before`; honour that
deadline before another request. Redirects are not followed. With an exact
discovered `record_id`, it reads the complete public HTML release metadata,
canonical/OG identity, advertised ZIP, MD5, global record count and licences.
It never requests the separately denied `/api/` route.

`shared_ror_directory` accepts that exact record, `country: DE | EG`, `offset`
and `limit` (1–500, default200). Cold cache independently checks policy for the
public record and its exact advertised file, then reads at most128MiB of ZIP.
The full published MD5 must match; the archive must have exactly the expected
bounded JSON and CSV members. The entire native JSON array must match the
declared count and contain unique typed ROR identities. Missing native country
data, unexpected status/type, malformed JSON, incomplete archives and checksum
drift refuse, without silently losing rows. No files are extracted or executed.

Every record with any native location in the selected country is retained,
including inactive/withdrawn records, all organisation types, historical names,
relationships, domains, links and native location/admin fields. The output adds
its original global-array index; it does not rewrite the source record.

Set the operator-owned absolute `JOB_MARKET_CAPTURE_DIR`. Verified source
metadata, the archive and complete DE/EG projections are atomically cached below
`ror/<record_id>/`. A manifest is published only after both complete projections
validate. A short local lease prevents duplicate cold downloads; an expired
lease is retained, without inspecting or signalling any process. Cache files
contain public directory data, never credentials or a browser session.

Follow exact `next_request`: same immutable record, country and archive SHA256,
plus the next native-array segment. Noninitial offsets require that digest.
Cached segments verify projection hashes and make zero provider requests.
Corrupt/missing cache data and digest mismatch refuse without a silent refetch,
reset or empty-country claim. The terminal flag refers to the end of this
country array, not proof that the caller visited earlier segments.

The 2026-10-30 qualification of native release v2.15 (2026-10-20), record23500708,
verified146716 distinct ROR records:6032 with German locations and291 with
Egyptian locations, including all native statuses. The39,263,398-byte archive
matched published MD5`5522990688eb1b94811a8145e131b41e` and SHA256
`7a7bf58d5ac18436ed98daf5da906913761d54869edf86d405e51966609dd133`.
These are dated research-directory memberships, not employer/vacancy totals.
No whole dataset or applicants are redistributed in this source repository.

`kind: organisation_directory` is deliberately distinct from vacancy inventory.
`source_result_count`, `vacancy_count` and original job publication remain null;
coverage, model-review, active-hiring, legal-employer and job-worksite flags are
false. Native active status concerns research activity. A headquarters or other
ROR location cannot establish a job's workplace, remote-worker countries,
language, eligibility, current vacancy or personal fit. Native aliases may be
historical. This directory covers research organisations, including commercial
ones represented by ROR; it is not all legal employers, subsidiaries or worksites.

Native licence references accompany every release and directory response: ROR
data CC0 and GeoNames attribution according to that actual release. The qualified
v2.15 page links CC BY4.0 for its GeoNames location data. Preserve those source
references rather than inferring a different licence from older documentation.

Original implementation using the repository's bounded anonymous HTTP helper,
standard-library JSON/ZIP/checksum/cache operations and lxml. No source script,
implementation example, source-site code, account, key, cookie, subscription,
application or contact is used. Technical references:
<https://ror.readme.io/docs/data-dump>,
<https://ror.readme.io/docs/zenodo>,
<https://ror.readme.io/docs/ror-data-structure>.
The whole immutable dump avoids filter-only API pagination ambiguities.

Synthetic Python and Node tests exercise policy-before-content, denied routes,
canonical metadata, strict UTF8, checksum/count reconciliation, country unions,
all statuses/types, preserved records, cache integrity/continuation, leases,
argument/environment boundaries and non-promoting typed failures. A consumer
still owns employer discovery, actual workplace inventories, original clocks,
personal decisions and honest country/week coverage.
