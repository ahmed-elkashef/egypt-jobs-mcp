import test from 'node:test';
import assert from 'node:assert/strict';
import { JobsClient, normalizeJob, normalizePage, searchJobs, getJob, registerJobs } from '../src/jobs.js';

const request = { wo: 'Berlin', page: 2, size: 100, angebotsart: 1 };
const listing = { referenznummer: 'TEST-2-S', stellenangebotsTitel: 'Synthetic opportunity', firma: 'Synthetic employer',
  datumErsteVeroeffentlichung: '2026-10-01', aktuelleVeroeffentlichungsdatum: '2026-10-09',
  modifikationsTimestamp: '2026-10-10T05:00:00Z', eintrittsdatum: '2027-01-01',
  stellenlokationen: [{ adresse: { ort: 'Berlin', plz: '10115' }, geokoordinaten: { lat: 52.5, lon: 13.4 } },
    { adresse: { ort: 'Another city' }, geokoordinaten: { lat: 48.1, lon: 11.6 } }],
  arbeitszeitVollzeit: false, arbeitszeitTeilzeitFlexibel: true, homeofficemoeglich: false,
  quereinstiegGeeignet: true, angebotsart: 'ARBEIT', unknownFutureField: { retained: true } };

test('all workplaces, false flags, dates and unknown fields survive normalization without inferred dates', () => {
  const entry = { stelle: listing, entfernung: 3.4 }; const job = normalizeJob(entry);
  assert.deepEqual(job.workplaces, listing.stellenlokationen);
  assert.equal(job.hours_flags.arbeitszeitVollzeit, false);
  assert.equal(job.homeoffice_possible, false);
  assert.equal(job.career_change_eligible, true);
  assert.equal(job.offering_type, 'ARBEIT');
  assert.equal('employment_type' in job, false);
  assert.equal(job.source_distance, 3.4);
  assert.equal(job.original_publication.raw, '2026-10-01');
  assert.equal(job.original_publication.precision, 'calendar_date');
  assert.equal(job.original_publication.original_instant_verified, false);
  assert.equal(job.native_dates.eintrittsdatum, '2027-01-01');
  assert.deepEqual(job.raw_entry, entry);
});

test('a start date or update timestamp never substitutes for publication', () => {
  assert.equal(normalizeJob({ eintrittsdatum: '2030-01-01', modifikationsTimestamp: '2026-10-01T05:00:00Z' })
    .original_publication.raw, null);
});

test('native v6 offering kind is preserved ahead of legacy aliases without inventing a precise model', () => {
  for (const kind of ['ARBEIT', 'PRAKTIKUM_TRAINEE', 'FUTURE_NATIVE_KIND']) {
    const job = normalizeJob({ stellenangebotsart: kind, angebotsart: 'legacy-value' });
    assert.equal(job.offering_type, kind);
    assert.equal(job.raw.stellenangebotsart, kind);
    assert.equal('employment_type' in job, false);
  }
});

test('legacy listing envelopes and all legacy workplace fields survive', () => {
  const page = normalizePage({ stellenangebote: [{ titel: 'Legacy', arbeitsort: { ort: 'Berlin', plz: '10115' } }] }, request);
  assert.equal(page.jobs[0].workplaces[0].adresse.plz, '10115');
  assert.equal(page.pagination.reported_total, null);
  assert.equal(page.pagination.exhausted_by_reported_total, null);
});

test('page 2 retains native pagination and never claims frozen or market coverage', () => {
  const page = normalizePage({ ergebnisliste: [{ stelle: listing }], page: 2, size: 100, maxErgebnisse: 250,
    woOutput: { bereinigterOrt: 'Berlin', geokoordinaten: { lat: 52.5, lon: 13.4 } } }, request);
  assert.equal(page.pagination.next_page, 3);
  assert.equal(page.pagination.exhausted_by_reported_total, false);
  assert.equal(page.pagination.exact_interval_coverage, false);
  assert.equal(page.pagination.snapshot_stable, false);
  assert.equal(page.resolved_location.bereinigterOrt, 'Berlin');
});

test('known zero and final page differ from inconsistent empty or absent listing envelopes', () => {
  const zero = normalizePage({ ergebnisliste: [], maxErgebnisse: 0 }, { page: 1, size: 25 });
  assert.equal(zero.pagination.exhausted_by_reported_total, true);
  const bad = normalizePage({ ergebnisliste: [], maxErgebnisse: 300, page: 2, size: 100 }, request);
  assert.equal(bad.pagination.consistent, false);
  assert.equal(bad.pagination.exhausted_by_reported_total, null);
  assert.throws(() => normalizePage({ error: 'upstream failed' }, request), /listing array absent/);
  const final = normalizePage({ ergebnisliste: [{ stelle: listing }], maxErgebnisse: 101, page: 2, size: 100 }, request);
  assert.equal(final.pagination.exhausted_by_reported_total, true);
  assert.equal(final.pagination.next_page, null);
});

test('provider page mismatch, invalid totals and nonintegral values never prove pagination exhaustion', () => {
  for (const data of [
    { ergebnisliste: [], maxErgebnisse: 0, page: 1, size: 100 },
    { ergebnisliste: [], maxErgebnisse: true },
    { ergebnisliste: [], maxErgebnisse: 0.5 },
  ]) {
    assert.equal(normalizePage(data, request).pagination.exhausted_by_reported_total, null);
  }
});

test('native work and internship partitions use v6 and exact age/page/size without hidden title filters', async () => {
  for (const offering of [1, 34]) {
    let observed;
    const client = { async request(endpoint, params) { observed = { endpoint, params };
      return { ergebnisliste: [], maxErgebnisse: 0, page: 2, size: 100 }; } };
    const result = await searchJobs(client, { ...request, angebotsart: offering, veroeffentlicht_seit: 7 });
    assert.equal(observed.endpoint, 'pc/v6/jobs');
    assert.equal(observed.params.angebotsart, String(offering));
    assert.equal(observed.params.veroeffentlichtseit, '7');
    assert.equal(observed.params.page, '2');
    assert.equal(observed.params.size, '100');
    assert.equal('was' in observed.params, false);
    assert.equal(result.request.angebotsart, offering);
  }
});

test('invalid pages, sizes and offering types are rejected before a network request', async () => {
  const client = { request() { throw new Error('network must not be reached'); } };
  for (const input of [{ page: 0 }, { page: 1.5 }, { size: 101 }, { size: 0 }, { angebotsart: 99 }]) {
    await assert.rejects(searchJobs(client, input), error => error.name === 'ZodError');
  }
});

test('full detail body, all workplaces and a safe encoded hash path are preserved', async () => {
  const body = '<p>Complete synthetic text.</p>\nSecond paragraph without truncation.';
  let path; const source = { ...listing, stellenangebotsBeschreibung: body };
  const result = await getJob({ async request(endpoint) { path = endpoint; return source; } }, { hashId: 'ab/c+d==' });
  assert.equal(path, 'pc/v4/jobdetails/ab%2Fc%2Bd%3D%3D');
  assert.equal(result.job.description, body);
  assert.equal(result.job.description_available, true);
  assert.deepEqual(result.raw_response, source);
  assert.equal(result.job.workplaces.length, 2);
  assert.equal(normalizeJob(listing).description_available, false);
});

test('429 errors retain retry advice and MCP isError; they never look like an empty page', async () => {
  let calls = 0;
  const client = new JobsClient({ fetchImpl: async () => { calls++; return new Response('rate limited', {
    status: 429, headers: { 'retry-after': '60' } }); } });
  let handler; registerJobs({ registerTool(name, schema, callback) { if (name === 'job_suche') handler = callback; } }, client);
  const response = await handler({});
  assert.equal(response.isError, true);
  assert.equal(response.structuredContent.status, 429);
  assert.equal(response.structuredContent.retry_after, '60');
  assert.equal(response.structuredContent.coverage_complete, false);
  assert.equal(calls, 1);
});

test('timeouts/network failures surface as MCP errors without automatic retries', async () => {
  const client = new JobsClient({ fetchImpl: async () => { throw new Error('synthetic timeout'); } });
  let handler; registerJobs({ registerTool(name, schema, callback) { if (name === 'job_suche') handler = callback; } }, client);
  const result = await handler({}); assert.equal(result.isError, true);
  assert.match(result.structuredContent.message, /synthetic timeout/);
});
