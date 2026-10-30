# German student markets and organisation discovery

These original readers add the native MeinPraktikum market and two official
organisation directories to the German tools. They do not enumerate every
German vacancy or certify a completed week. No source dataset, source frontend
implementation, applicant record or live nonce is bundled in this repository.

Each call requires `personal_noncommercial_use: true`. Set this only for
personal, noncommercial job research. MeinPraktikum's [terms](https://www.meinpraktikum.de/statisch/nutzungsbedingungen)
restrict use to noncommercial purposes. The HRK [download page](https://www.hochschulkompass.de/hochschulen/downloads.html)
permits personal use; other uses need its permission. This source restriction
is separate from the software's MIT licence.

## Student market

`de_public_meinpraktikum_inventory` accepts `scope` (`internships` or
`working_student`), optional positive `page` and the explicit use flag. There
is no title, skill, employer or interest query. The two scopes reproduce the
source's complete native study-model controls. The internship scope also
includes school, overseas and thesis categories; evaluate actual records
before applying person-specific exclusions.

The first-party anonymous read service uses POST and returns HTTP201 with
`statusCode: 200` in its search envelope. This is a search operation. No
application, account, subscription or write-service endpoint is called.
Native pages start at 1 and increment by 1. The qualified format returns 10
records per page and an exact `eq` total. Count/row conflicts, unknown total
semantics and out-of-range pages refuse explicitly. First, second and final
pages were independently observed for both scopes on 30 October 2026: the source
reported 4,166 internship-group records and 2,311 student-job-group records.
These are dated format observations, not current guarantees or vacancy counts.
The complete inventories were not acquired in that protocol qualification.

A search record is a parent job group with multiple location-vacancy records.
Every native child UUID, slug and location is preserved. A child URL must
reconcile its own UUID; its ID is different from the parent group's ID. Slug
text can retain an older employer/year while the current advert title changes.
The SSR internship preview and live API first page differed in the dated
captures; no cache cause or ordering equivalence is asserted. Pagination uses
the actual API pages.

`de_public_meinpraktikum_detail` accepts only an independently obtained exact
public vacancy `url` and the use flag. It reconciles the selected child with
the parent group, native route, visible title and source schema. It preserves
the complete qualified primary advert container, full native role Markdown,
company fields and separate native clocks. The primary container is selected
through its single h1 ancestor and the independently qualified current
component token; a changed template has no whole-page or field-only fallback.
Application controls, script/state blocks and attributes are removed. User
hydration and nested credential/session fields are excluded. No media is
requested; nontext requirements remain unverified. Source dates and generic
study labels are not original-publication, worker-country or fit verdicts.

## Organisation directories

`de_public_organisation_directory` accepts `directory`, optional `page` and
the use flag:

- `higher_education` reads the exact currently advertised HRK TSV download.
  It is one file, not provider pagination. Native IDs and selected organisation
  fields preserve source spelling and homepage strings. The qualified dated
  file contained 390 institutions, 30 with a Hesse main address. This does not
  enumerate every campus, hospital, research employer or institution job.
- `staffing_members` reads the ordinary GVP public member-metadata filter with
  native pages. The source's anonymous public CSRF nonce stays in memory and
  is used only for that fixed read operation. No user login/cookies, protected
  member-detail route, challenge solving or quota bypass occurs. First, next
  and final metadata pages were observed against a native total 4,260 on
  30 October 2026; that was not a complete 426-page acquisition. Metadata exposes
  organisation labels, not verified employment sites or company homepage URLs.

The broad registry entries `public_institutions` and `staffing` remain
`research_required`: a useful directory route does not complete employer
employment-source discovery. A directory response has kind
`organisation_directory` and must never enter a vacancy/application pipeline.

Transport checks exact origins, methods and paths, current robots, bounded
whole responses and declared request intervals. The two qualified REST/TXT
origins returned robots404; the scoped handling follows [RFC9309 section2.3.1.3](https://www.rfc-editor.org/rfc/rfc9309.html#section-2.3.1.3).
Denied routes, authentication, throttles, server failures and unknown origins
never use that exception. Redirects, source scripts and media are not followed.
