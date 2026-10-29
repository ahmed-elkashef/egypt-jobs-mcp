// Derived project: Greyt GmbH upstream is retained under vendor/; see CREDITS.md.
import { z } from 'zod';

export const JOB_SEARCH_SCHEMA = {
  was: z.string().optional().describe('Optional source search term; omit for an unfiltered inventory.'),
  wo: z.string().optional().describe('Source locality or postcode. Inspect resolved_location before counting coverage.'),
  umkreis: z.number().finite().nonnegative().optional().describe('Source radius in kilometres.'),
  angebotsart: z.union([z.literal(1), z.literal(2), z.literal(4), z.literal(34)]).default(1)
    .describe('1=Arbeit, 2=Selbständigkeit, 4=Ausbildung, 34=Praktikum. Separate partitions; 1 is not all offerings.'),
  arbeitszeit: z.string().optional().describe('Native hours flags, e.g. vz/tz/ho/mj. No inferred worker fit.'),
  befristung: z.union([z.literal(1), z.literal(2)]).optional().describe('Native 1=fixed-term, 2=indefinite.'),
  veroeffentlicht_seit: z.number().int().nonnegative().optional().describe('Native age in days; not an exact publication instant filter.'),
  page: z.number().int().min(1).default(1).describe('One-based source page; there is no frozen snapshot/cursor.'),
  size: z.number().int().min(1).max(100).default(25).describe('Native page size 1–100.'),
};
export const searchInput = z.object(JOB_SEARCH_SCHEMA);
export const detailInput = z.object({ hashId: z.string().min(1).max(1024) });
export const READ_ONLY = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true };

export class ProviderError extends Error {
  constructor(status, message, retryAfter = null) {
    super(message);
    this.name = 'ProviderError';
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

export class JobsClient {
  constructor({ fetchImpl = globalThis.fetch, timeoutMs = 30000 } = {}) {
    this.fetch = fetchImpl;
    this.timeoutMs = timeoutMs;
  }
  async request(endpoint, params = {}) {
    const url = new URL(`https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/${endpoint}`);
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
    }
    const response = await this.fetch(url, {
      method: 'GET', headers: { 'X-API-Key': 'jobboerse-jobsuche', Accept: 'application/json' },
      signal: AbortSignal.timeout(this.timeoutMs),
    });
    if (!response.ok) {
      throw new ProviderError(response.status, `BA HTTP ${response.status} ${response.statusText}`,
        response.headers.get('retry-after'));
    }
    return response.json();
  }
}

const numberOrNull = value => ['number', 'string'].includes(typeof value) && String(value).trim() !== '' &&
  Number.isSafeInteger(Number(value)) ? Number(value) : null;
const first = (...values) => values.find(value => value !== undefined && value !== null) ?? null;

export function publication(job) {
  const fields = ['datumErsteVeroeffentlichung', 'veroeffentlichtAm'];
  const field = fields.find(key => job[key] !== undefined && job[key] !== null);
  const value = field ? job[field] : job.veroeffentlichungszeitraum?.von ?? null;
  const sourceField = field ?? (value !== null ? 'veroeffentlichungszeitraum.von' : null);
  const precision = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? 'calendar_date'
    : typeof value === 'string' && /T.*(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? 'offset_timestamp' : 'unknown';
  return { raw: value, source_field: sourceField, precision, time_zone_inferred: false,
    original_instant_verified: false };
}

export function normalizeJob(entry) {
  const job = entry.stelle ?? entry;
  const reference = first(job.referenznummer, job.refnr, job.referenzNr);
  const hashId = job.hashId ?? (reference === null ? null : Buffer.from(String(reference), 'utf8').toString('base64'));
  const workplaces = Array.isArray(job.stellenlokationen) ? job.stellenlokationen
    : job.arbeitsort ? [{ adresse: job.arbeitsort, legacy: true }] : [];
  const nativeDates = Object.fromEntries(Object.entries(job).filter(([key]) =>
    /datum|timestamp|veroeffentlich|eintritt|beginn|ende/i.test(key)));
  const hoursFlags = Object.fromEntries(Object.entries(job).filter(([key]) => /^arbeitszeit/.test(key)));
  const descriptionField = ['stellenangebotsBeschreibung', 'stellenbeschreibung', 'beschreibung', 'description']
    .find(key => typeof job[key] === 'string' && job[key].length > 0);
  return {
    reference_number: reference, hashId,
    title: first(job.stellenangebotsTitel, job.titel), employer: first(job.firma, job.arbeitgeber),
    workplaces, source_distance: first(entry.entfernung, job.entfernung),
    hours_flags: hoursFlags, homeoffice_possible: first(job.homeofficemoeglich, job.homeOfficeMoeglich),
    career_change_eligible: first(job.quereinstiegGeeignet, job.fuerQuereinstiegGeeignet),
    offering_type: first(job.angebotsart, job.angebotsArt),
    original_publication: publication(job), native_dates: nativeDates,
    description: descriptionField ? job[descriptionField] : null,
    description_source_field: descriptionField ?? null,
    description_available: Boolean(descriptionField),
    raw: job, raw_entry: entry,
  };
}

export function normalizePage(data, request) {
  const entries = data.ergebnisliste ?? data.stellenangebote;
  if (!Array.isArray(entries)) throw new ProviderError(null, 'Unrecognized BA search envelope: listing array absent');
  const returnedPage = numberOrNull(data.page) ?? request.page;
  const returnedSize = numberOrNull(data.size) ?? request.size;
  const reportedTotal = numberOrNull(data.maxErgebnisse ?? data.total);
  const consistent = returnedPage === request.page && returnedSize > 0 && entries.length <= returnedSize &&
    (reportedTotal === null || reportedTotal >= 0) && !(entries.length === 0 && reportedTotal > (returnedPage - 1) * returnedSize);
  const exhausted = consistent && reportedTotal !== null ? returnedPage * returnedSize >= reportedTotal : null;
  return {
    kind: 'ba_job_search_page', api_version: 'v6', request,
    resolved_location: data.woOutput ?? null,
    pagination: {
      page: returnedPage, size: returnedSize, returned_count: entries.length,
      page_reported_by_source: numberOrNull(data.page) !== null,
      size_reported_by_source: numberOrNull(data.size) !== null,
      reported_total: reportedTotal, consistent, exhausted_by_reported_total: exhausted,
      next_page: consistent && reportedTotal !== null && !exhausted ? returnedPage + 1 : null,
      exact_interval_coverage: false, snapshot_stable: false,
    },
    jobs: entries.map(normalizeJob), raw_response: data,
    limits: [
      'One page only. Follow all pages and offering-type partitions needed by your scope.',
      'Reported totals describe this mutable source response; they do not certify all German vacancies or a frozen interval.',
      'Publication dates may be calendar dates; no original instant or timezone is invented.',
      'Search order is source-controlled and may be distance order, not newest-first.',
      'Empty/malformed/inconsistent pages and provider errors never count as exhausted supply.',
    ],
  };
}

export async function searchJobs(client, input) {
  const args = searchInput.parse(input);
  const params = Object.fromEntries(Object.entries(args).filter(([, value]) => value !== undefined)
    .map(([key, value]) => [key === 'veroeffentlicht_seit' ? 'veroeffentlichtseit' : key, String(value)]));
  return normalizePage(await client.request('pc/v6/jobs', params), args);
}

export async function getJob(client, input) {
  const args = detailInput.parse(input);
  const data = await client.request(`pc/v4/jobdetails/${encodeURIComponent(args.hashId)}`);
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new ProviderError(null, 'Unrecognized BA detail response');
  return { kind: 'ba_job_details', api_version: 'v4', hashId: args.hashId, job: normalizeJob(data),
    raw_response: data, limits: ['Source text is preserved verbatim. Retrieval is not candidate fit or confirmation that a posting is currently open.'] };
}

function failed(error) {
  const data = { kind: 'ba_provider_error', status: error.status ?? null,
    message: error instanceof Error ? error.message : String(error), retry_after: error.retryAfter ?? null,
    coverage_complete: false, retried: false };
  return { isError: true, structuredContent: data, content: [{ type: 'text', text: JSON.stringify(data) }] };
}

function successful(data) {
  // JSON text keeps compatibility with clients which do not read structuredContent.
  return { structuredContent: data, content: [{ type: 'text', text: JSON.stringify(data) }] };
}

export function registerJobs(server, client) {
  server.registerTool('job_suche', {
    description: 'Read one BA v6 job page with all workplaces, native dates/flags and explicit pagination evidence. Omit was to enumerate without keyword filtering. Offering types 1 and 34 are separate partitions.',
    inputSchema: JOB_SEARCH_SCHEMA, annotations: READ_ONLY,
  }, async input => { try { return successful(await searchJobs(client, input)); } catch (error) { return failed(error); } });
  server.registerTool('job_details', {
    description: 'Retrieve and preserve a full native BA detail record using hashId from job_suche. Uses the working v4 details route; description may be absent and is never fabricated.',
    inputSchema: detailInput.shape, annotations: READ_ONLY,
  }, async input => { try { return successful(await getJob(client, input)); } catch (error) { return failed(error); } });
}
