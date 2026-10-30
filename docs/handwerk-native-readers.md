# Original native Handwerk readers

`de_public_handwerk_inventory` reads one complete public Radar offering page
with explicit personal noncommercial use. The fixed native GET fields come
from the ordinary HTML search and paging forms. No frontend implementation,
source script, account, cookie, consent widget or application service is used.
The independently checked source policy denies its script directory; this
reader never requests those scripts.

Required arguments are `scope` (`internships` or `apprenticeships`),
`postal_code` (five digits) and `personal_noncommercial_use: true`.
`radius_km` defaults to 25; its integer 1..1000 restriction is a client bound,
not proof of national membership. `page` defaults to 1. There is no career,
degree, employer or skill query. The native training-firm switch is not exposed
as vacancy supply. A postcode/radius circle does not establish Hesse, German,
employer or weekly coverage.

For example, `postal_code: "60323"` identifies a public Frankfurt query anchor;
it is not a candidate address or a commute preference. Enumerate and reconcile
every authorised geographic partition and its ambiguity complement separately.

Follow the returned `next_request` exactly. Continuation requires the original
`first_native_pages` ceiling; an absent or changed ceiling refuses acquisition.
Actual first/next/third pages returned 15/30/45 records, with 15 overlapping IDs
between the second and third pages. The bounded final page returned 4. These
observations establish neither a fixed page size nor an exact source total.
The reader preserves all rows and reports `source_result_count: null`.
Reconcile source IDs across pages; do not multiply pages by a nominal size,
sum duplicates or assume a cause for the variable result sets.

Native `data-resultid` is distinct from local marker indexes and matches the
inline `detail_<resultid>` block. Every record preserves its complete native
metadata text, clean inline HTML/text and independently advertised primary
reference. Continuation HTML repeats an identical blank switch input; the
reader retains those occurrences and refuses conflicting values. It never
silently picks a page or scope from conflicting fields.

A genuine zero-result query is recognised only with the complete native form,
unchanged filters, result container and visible native empty-result message.
A script string, generic empty page, login text, changed continuation or missing
native structure cannot become an empty market. Empty scopes still make no
country, historical or personal-fit claim.

## Standalone primaries

`de_public_handwerk_detail` requires an independently obtained exact public URI
and the same personal-use acknowledgement. Current qualified routes are:

- `https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=<native-id>`
- `https://www.hwk-ufr.de/78,0,jobboardofferdetail.html?id=<native-id>`

The source origin, numeric ID, complete primary main, current header and both
native canonical/OpenGraph URLs are guarded. No application, vCard, map, contact or account endpoint is requested.
Other chamber/WordPress/redirect references remain data and are never followed
automatically. A Radar ID and another provider's opaque primary key can differ;
retain both and verify their lineage before attachment.

Inline fields are not a verified complete standalone advert. Actual primary
headers added a full-time internship condition omitted by the central fields.
The complete primary main can also contain related jobs, firm context, maps
and general occupation information. Preserve those as context, rather than
turning every statement into this role's mandatory requirements.

Source internship labels, minimum school qualifications and generic vocational
descriptions do not establish university recognition or personal eligibility.
Full-time internships and working-student arrangements are distinct. Start
dates and observation are not original publication or reopening clocks.
Nontext media, actual application materials and individual fit remain unverified.

Only synthetic fixtures are bundled. Personal-use source research stays outside
this repository. The source provider's imprint disclaims completeness and
currency; an accessible reader never closes national or frozen-week coverage.
