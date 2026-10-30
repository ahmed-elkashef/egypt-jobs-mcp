# Country source coverage

As of 30 October 2026, MCP v0.4.24 source contracts. This is implementation/access
coverage, not a live vacancy census; each access observation retains its date.

| Implementation/access state | Sources/channel groups |
| --- | --- |
| access_limited | 13 |
| context_only | 4 |
| credential_required | 3 |
| external_connector | 3 |
| implemented | 38 |
| requires_employer_seed | 15 |
| research_required | 24 |

The registry has 100 unique entries: 43 apply to Egypt and
85 to Germany, including shared entries. Counts overlap; they are
not vacancies, employers or currently available transports.

## Remaining implementation and access

Germany still has additional major/local/specialist/student boards, state and
municipal portals, institutional/staffing discovery and a national employer
census gap. Berlin is one qualified state portal, with an unfiltered supply
scope and a broader student-entry scope; it does not close that group.
Karriere.NRW and Interamt require approved credentials/provider scopes.
Hessen's current official portal robots request redirects to an application
shell; its vacancy/API reads remain unqualified. These are dated exact-route
observations, not a whole-government access verdict.

Egypt still has official bulletins/government hiring, remaining regional/national
boards, university/student channels and employer-directory discovery gaps.
Forasna/Tanqeeb retain browser transport where anonymous HTTP fails. Shared
account/offline/referral channels have separate access boundaries. Native
provider support requires independently verified employer seeds and does not
establish all-employer discovery.

## Current source register

| Source | Scope | State | Category |
| --- | --- | --- | --- |
| [WUZZUF](https://wuzzuf.net/) | EG | implemented | national_board |
| [Forasna](https://forasna.com/) | EG | access_limited | national_board |
| [ArabJobs](https://www.arabjobs.com/) | EG | implemented | national_board |
| [Tanqeeb Egypt](https://egypt.tanqeeb.com/) | EG | access_limited | national_board |
| [Akhtaboot Egypt](https://www.akhtaboot.com/en/egypt/jobs) | EG | implemented | national_board |
| [Bayt Egypt](https://www.bayt.com/en/egypt/jobs/) | EG | access_limited | national_board |
| [Jobzella](https://www.jobzella.com/) | EG | research_required | national_board |
| [GulfTalent](https://www.gulftalent.com/) | EG | research_required | regional_board |
| [Egypt Ministry of Labour vacancy bulletins](https://www.manpower.gov.eg/) | EG | research_required | official_vacancies |
| [Egypt Government Jobs Portal](https://jobs.caoa.gov.eg/) | EG | research_required | official_vacancies |
| [University and student career channels](https://careercenter.aucegypt.edu/) | EG | research_required | student_channels |
| [Employer directories, chambers and industrial zones](https://www.fei.org.eg/) | EG | research_required | employer_discovery |
| [Local, informal, referral and closed community channels](https://www.ilo.org/) | EG | research_required | offline_boundary |
| [Mostaql client projects](https://mostaql.com/projects) | EG, DE | implemented | freelance_demand |
| [Bundesagentur Jobsuche](https://www.arbeitsagentur.de/jobsuche/) | DE | implemented | official_vacancies |
| [BA Ausbildung](https://www.arbeitsagentur.de/bildung/ausbildung) | DE | implemented | apprenticeships |
| [BA Entgeltatlas](https://web.arbeitsagentur.de/entgeltatlas/) | DE | implemented | salary_context |
| [BA Studienangebote](https://www.arbeitsagentur.de/bildung/studium) | DE | implemented | education_context |
| [BA Studienfelder](https://www.arbeitsagentur.de/bildung/studium) | DE | implemented | education_context |
| [BA Weiterbildung / mein NOW](https://mein-now.de/) | DE | implemented | training_context |
| [BA coaching](https://www.arbeitsagentur.de/) | DE | implemented | training_context |
| [StepStone Germany](https://www.stepstone.de/) | DE | access_limited | national_board |
| [Indeed Germany](https://de.indeed.com/) | DE | research_required | national_board |
| [XING Jobs](https://www.xing.com/jobs) | DE | access_limited | national_board |
| [meinestadt.de](https://jobs.meinestadt.de/) | DE | access_limited | local_board |
| [stellenanzeigen.de](https://www.stellenanzeigen.de/) | DE | implemented | national_board |
| [Jobware](https://www.jobware.de/) | DE | implemented | national_board |
| [Kimeta](https://www.kimeta.de/) | DE | research_required | aggregator |
| [Monster Germany](https://www.monster.de/) | DE | research_required | national_board |
| [jobvector](https://www.jobvector.de/) | DE | access_limited | specialist_board |
| [Yourfirm](https://www.yourfirm.de/) | DE | implemented | smb_board |
| [Jobs.de](https://www.jobs.de/) | DE | implemented | national_board |
| [jobtensor](https://jobtensor.com/) | DE | access_limited | specialist_board |
| [Absolventa](https://www.absolventa.de/) | DE | implemented | graduate_board |
| [academics](https://www.academics.de/) | DE | implemented | research_board |
| [EURAXESS](https://euraxess.ec.europa.eu/jobs) | DE | access_limited | research_board |
| [Jobmensa](https://www.jobmensa.de/) | DE | implemented | student_board |
| [Stellenwerk](https://www.stellenwerk.de/) | DE | research_required | student_board |
| [StudentJob Germany](https://www.studentjob.de/) | DE | implemented | student_board |
| [Zenjob](https://www.zenjob.com/de/) | DE | implemented | temporary_work |
| [YoungCapital Germany](https://www.youngcapital.de/) | DE | implemented | student_board |
| [Ausbildung.de](https://www.ausbildung.de/) | DE | research_required | apprenticeships |
| [Azubiyo](https://www.azubiyo.de/) | DE | research_required | apprenticeships |
| [AUBI-plus](https://www.aubi-plus.de/) | DE | research_required | apprenticeships |
| [IHK apprenticeship channels](https://www.ihk.de/) | DE | research_required | chamber_channels |
| [Handwerk native Radar offers and qualified chamber primaries](https://www.handwerk.de/infos-zur-ausbildung/lehrstelle-finden) | DE | implemented | chamber_channels |
| [JOIN](https://join.com/) | DE | requires_employer_seed | smb_board |
| [GermanTechJobs](https://germantechjobs.de/) | DE | implemented | specialist_board |
| [Berlin Startup Jobs](https://berlinstartupjobs.com/) | DE | implemented | regional_board |
| [EnglishJobs.de](https://englishjobs.de/) | DE | access_limited | national_board |
| [Instaffo](https://instaffo.com/) | DE | research_required | matching_platform |
| [get in Engineering](https://www.get-in-engineering.de/) | DE | implemented | specialist_board |
| [service.bund.de vacancies](https://www.service.bund.de/) | DE | access_limited | public_sector |
| [Interamt](https://gate.interamt.de/interamtApi/api-doc/index.html) | DE | credential_required | public_sector |
| [Karriere.NRW](https://developer.karriere.nrw/) | DE | credential_required | state_public_sector |
| [State and municipal career portals](https://www.berlin.de/karriereportal/) | DE | research_required | public_sector |
| [Universities, hospitals and research institutions](https://www.hochschulkompass.de/hochschulen/downloads.html) | DE | research_required | employer_discovery |
| [Staffing and temporary-work employer boards](https://personaldienstleister.de/der-gvp/mitglieder/gvp-mitglieder/) | DE | research_required | employer_discovery |
| [National/local employer directory discovery](https://www.unternehmensregister.de/) | DE | research_required | employer_discovery |
| [CAPMAS](https://www.capmas.gov.eg/) | EG | context_only | statistics_context |
| [BA labour-market statistics API](https://statistik.arbeitsagentur.de/DE/Navigation/Service/API/API-Start-Nav.html) | DE | context_only | statistics_context |
| [Destatis / GENESIS](https://www.destatis.de/) | DE | context_only | statistics_context |
| [ILO labour-market statistics](https://ilostat.ilo.org/) | * | context_only | statistics_context |
| [LinkedIn](https://www.linkedin.com/jobs/) | * | external_connector | external_account_service |
| [Trackly](https://trackly.ai/) | * | external_connector | external_account_service |
| [Official Upwork MCP](https://www.upwork.com/ai/mcp) | * | external_connector | external_account_service |
| [Arbeitnow](https://www.arbeitnow.com/api/job-board-api) | * | implemented | public_job_feed |
| [Remotive](https://remotive.com/api/remote-jobs) | * | implemented | public_job_feed |
| [Remote OK](https://remoteok.com/api) | * | implemented | public_job_feed |
| [Himalayas](https://himalayas.app/api) | * | implemented | public_job_feed |
| [The Muse](https://www.themuse.com/developers/api/v2) | * | implemented | public_job_feed |
| [We Work Remotely](https://weworkremotely.com/) | * | implemented | public_job_feed |
| [Working Nomads](https://www.workingnomads.com/) | * | implemented | public_job_feed |
| [Jobicy](https://jobicy.com/) | * | implemented | public_job_feed |
| [Greenhouse](https://developers.greenhouse.io/job-board.html) | * | requires_employer_seed | direct_ats |
| [Lever](https://github.com/lever/postings-api) | * | requires_employer_seed | direct_ats |
| [Ashby](https://developers.ashbyhq.com/docs/public-job-posting-api) | * | requires_employer_seed | direct_ats |
| [Personio](https://developer.personio.de/docs/retrieving-open-job-positions) | * | requires_employer_seed | direct_ats |
| [Recruitee](https://docs.recruitee.com/) | * | requires_employer_seed | direct_ats |
| [Workable](https://help.workable.com/) | * | requires_employer_seed | direct_ats |
| [SmartRecruiters](https://developers.smartrecruiters.com/) | * | requires_employer_seed | direct_ats |
| [Workday](https://www.workday.com/) | * | requires_employer_seed | direct_ats |
| [Teamtailor](https://docs.teamtailor.com/) | * | requires_employer_seed | direct_ats |
| [SAP SuccessFactors](https://www.sap.com/products/hcm/recruiting-software.html) | * | requires_employer_seed | direct_ats |
| [Oracle Recruiting](https://www.oracle.com/human-capital-management/recruiting/) | * | requires_employer_seed | direct_ats |
| [onlyfy](https://help.xing.com/hc/de/articles/31499221281309-Job-Feed-Integration) | * | requires_employer_seed | direct_ats |
| [d.vinci](https://www.dvinci.de/) | * | requires_employer_seed | direct_ats |
| [Freelancer public client projects](https://developers.freelancer.com/) | * | implemented | freelance_demand |
| [Optional Upwork marketplace API](https://www.upwork.com/developer) | * | credential_required | freelance_demand |
| [Malt](https://www.malt.de/) | DE | research_required | freelance_demand |
| [freelancermap](https://www.freelancermap.de/) | DE | research_required | freelance_demand |
| [Randstad Professional (formerly GULP) jobs and projects](https://www.gulp.de/) | DE | research_required | mixed_jobs_and_projects |
| [Khamsat](https://khamsat.com/) | EG | research_required | freelance_demand |
| [HeyJobs](https://www.heyjobs.co/de-de/) | DE | access_limited | national_board |
| [Studierendenwerk Frankfurt official student portal](https://stellenmarkt.swffm.de/) | DE | access_limited | student_board |
| [Original Jobshop/talentsconnect native career reader](https://www.jobs-fraport.com/) | DE | requires_employer_seed | direct_ats |
| [Frankfurt Airport Retail public career board](https://frankfurt-airport-retail.de/far/de/karriere-start/jobs) | DE | implemented | direct_employer |
| [SAP modern public careers front](https://jobs.sap.com/en/jobs/) | DE | implemented | direct_employer |
| [MeinPraktikum native internship and student-job market](https://www.meinpraktikum.de/) | DE | implemented | student_board |
| [Berlin state portal native public offers](https://www.berlin.de/karriereportal/) | DE | implemented | public_sector |

## Dated implementation notes

Jobmensa public list/detail routes were added in v0.4.2 with live policy checks, native continuation and synthetic regressions. This changes implementation status only; it does not close any national or historical coverage claim.

StudentJob and YoungCapital native list/detail readers were added in v0.4.3. External redirect records are retained and can remain access-limited under current robots. Their presence does not mean original-employer body access or applicant fit was verified.

Six original native public-board/feed/API readers were added in v0.4.4. service.bund.de remains access_limited: its permitted RSS snapshot does not cover the frozen week and its ordinary search route was denied.


v0.4.5 adds original Jobs.de native DTO/range/detail reading, Jobware whole
advertisement sitemap and separately policy-checked native iframe bodies, and
BerlinStartupJobs complete category discovery, native pagination and full bodies.
Its dated Berlin diagnostic traversed every one of 12 native categories and
returned136 distinct native URLs. EnglishJobs has original metadata/continuation
reading but remains access_limited because its signed outbound routes are denied;
no full-body transport is claimed. Jobtensor native search returned HTTP403; no
challenge, account or bypass was attempted. See the separate dated proof for
counts and limits; none of this proves a frozen country week or applicant fit.



v0.4.6 adds original anonymous XING inventory/body/discovery parsing. Native
semantic search/range echoes, promoted external records, ambiguous literal
locations and the observed 2,000-result retrieval cap remain explicit. Advertised
sitemaps include expired adverts. Large whole URI partitions use immutable private
consumer segments, **not** native pages or active-job counts. Meinestadt ordinary
reference/advertised-sitemap403, EURAXESS search robots denial and Jobvector
robots403 are dated route-specific access limits; other legitimate provider
routes remain discovery questions. HeyJobs was discovered as actual external
primary cards and is explicitly registered for further verification.


v0.4.7 adds original get in Engineering anonymous native SSR/open-API continuation
and full content, plus Zenjob primary shift pages, native continuation and full
visible details including notes beyond schema description. This does not verify
student contracts, remote eligibility or source-original dates. HeyJobs native
list/detail202 limits are explicit despite permitted directory/sitemap200.
Instaffo's FAQ excludes internships/working-student roles; its public general job
board remains a broader research/implementation entry, not a login-only claim.


v0.4.8 adds the official Frankfurt student portal native list/body and finite
employer discovery contracts. All56 native references and six employer profiles
were traversed in a dated test.48 visible HTML bodies and seven published PDF
text alternatives are qualified separately; one PDF-only ad remains limited.
No denied PDF/viewer fetch or rewrite occurred. Source, date, start/model conflict,
portal worksite and employer/frozen-coverage ambiguities remain explicit.


Handwerk implementation is limited to the explicit native postcode/radius offer
scope and two independently qualified ODAV primary origins. Actual Radar pages
have variable, overlapping records and no verified exact total; follow literal
next requests with the original page ceiling and reconcile native IDs. Inline
fields can omit standalone requirements. Other chamber/WP/redirect primaries,
university recognition, country/employer discovery and historical week coverage
remain separate work. Training firms are organisation context, never vacancies.
See [the original reader contract](handwerk-native-readers.md).


v0.4.23 adds the original Berlin state-portal native inventory and whole public
advert reader. Actual numbered continuation preserves the student filter while
`weiter` can drop it. All43 student-category records were observed over3 native
metadata pages; unfiltered618 supply was sampled58 rows across first/next/last,
not fully acquired. School/academic/professional models remain distinct, and
the unfiltered ambiguity complement remains required. A portal advert may have
an outside-Berlin worksite, conflicting deadlines and a separately numbered
employer original. See [the source contract](berlin-state-native-readers.md).


v0.4.24 corrects Berlin native advert UTF-8 decoding. HTTP Content-Type must
explicitly declare UTF-8 and bytes must decode strictly before HTML parsing.
The earlier native metadata fields, IDs and counts remain valid; affected advert
wording requires corrected reads. Exact same-advert German PDF references can
sit outside the main body and are retained unverified. No source/coverage or
human fit gate is promoted by this correction.
