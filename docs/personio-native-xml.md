# Personio native descriptions and posting links

Version 0.4.19 extends the existing `shared_get_public_inventory` contract. An explicitly verified employer subdomain remains required. The documented `language` parameter supports `de` and `en`; omission preserves the German XML default. This selects a description translation, independently of career-page display language, country and job working-language requirements. Missing translations remain records. Reconcile native IDs across feeds and supplement missing descriptions; never add language-feed counts as distinct vacancies.

```json
{"source":"personio","subdomain":"verified-employer","language":"en","metadata_only":true}
```

Retrieve complete captured description fields through `shared_get_public_job_from_snapshot` in the same MCP process. The snapshot operation makes no new provider request. No keyword, title, department, candidate or country filter is added.

If the source omits its URL field, a positive native numeric job ID can identify the documented `/job/{id}` route on the actual successful XML origin. The existing `.de` to `.com` fallback preserves the locale. The returned `url_basis` distinguishes this route from an explicit source URL; malformed native IDs never become fabricated paths. Employer identity and existing native URL fields remain unchanged.

Personio explicitly excludes its separately configured **About us** section from XML. The connector labels that limitation instead of claiming XML is the entire rendered page. Source description locale, `createdAt` and description availability establish neither working-language eligibility, original publication time nor human review. Complete current feeds establish no historical week or country/employer census.

The qualification used a board linked by its employer's official careers page. Its 309 XML IDs exactly matched 309 posting links observed on the native HTML board. Three records had empty German XML descriptions while their primary pages contained English role descriptions. Locale variants must preserve source membership and are not duplicate jobs. These dated observations qualify the route; they do not establish applicant fit or a live market count.

Primary documentation: [XML integration and default language](https://support.personio.de/hc/en-us/articles/207576365-Integrate-jobs-from-Personio-into-your-website-via-XML), [XML fields](https://developer.personio.de/docs/retrieving-open-job-positions), [independent career-page and job-language logic](https://support.personio.de/hc/en-us/articles/4409392549777-Summary-of-Personio-career-page-language-logic).
