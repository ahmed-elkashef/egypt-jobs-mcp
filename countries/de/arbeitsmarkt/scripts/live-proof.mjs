import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { writeFile, mkdir } from 'node:fs/promises';

// A generic public Berlin query. Never write raw job bodies or contacts to a
// published test receipt. Opt in with npm run test:live; no scheduled probing.
const root = fileURLToPath(new URL('../', import.meta.url));
const client = new Client({ name: 'ba-live-proof', version: '1.1.0' });
const transport = new StdioClientTransport({ command: process.execPath,
  args: [fileURLToPath(new URL('../src/index.js', import.meta.url))], cwd: root });
const query = { wo: '10115', umkreis: 25, veroeffentlicht_seit: 7, size: 100 };
const receipt = { tested_at: new Date().toISOString(), scope: 'Bounded live MCP diagnostics, not full-market or interval coverage',
  query, tools: [], checks: [], error: null };
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
async function page(offering, number) {
  const response = await client.callTool({ name: 'job_suche', arguments: { ...query, angebotsart: offering, page: number } });
  if (response.isError) throw new Error(JSON.stringify(response.structuredContent ?? response.content));
  const data = response.structuredContent;
  assert.equal(data.kind, 'ba_job_search_page');
  assert.equal(data.api_version, 'v6');
  assert.equal(data.pagination.page, number);
  assert.equal(data.pagination.size, 100);
  assert.equal(data.pagination.consistent, true);
  assert.ok(data.jobs.length > 0);
  assert.equal(data.request.angebotsart, offering);
  for (const job of data.jobs) {
    assert.ok(job.reference_number);
    assert.deepEqual(job.workplaces, job.raw.stellenlokationen ?? (job.raw.arbeitsort ? [{ adresse: job.raw.arbeitsort, legacy: true }] : []));
    assert.equal(job.original_publication.time_zone_inferred, false);
  }
  receipt.checks.push({ offering_type: offering, requested_page: number, returned: data.jobs.length,
    pagination: data.pagination, resolved_location: data.resolved_location,
    multi_workplace_records: data.jobs.filter(job => job.workplaces.length > 1).length,
    calendar_date_records: data.jobs.filter(job => job.original_publication.precision === 'calendar_date').length,
    source_response_sha256: hash(data.raw_response), preserved_workplaces: true });
  return data;
}
try {
  await client.connect(transport);
  receipt.tools = (await client.listTools()).tools.map(tool => tool.name).sort();
  assert.equal(receipt.tools.length, 9);
  const first = await page(1, 1);
  const second = await page(1, 2);
  await page(34, 1);
  receipt.work_page_overlap = second.jobs.filter(job => first.jobs.some(other => other.reference_number === job.reference_number)).length;
  const response = await client.callTool({ name: 'job_details', arguments: { hashId: first.jobs[0].hashId } });
  if (response.isError) throw new Error(JSON.stringify(response.structuredContent ?? response.content));
  const details = response.structuredContent;
  assert.equal(details.api_version, 'v4');
  assert.equal(details.job.description_available, true);
  assert.ok(details.job.description.length > 0);
  receipt.detail = { description_characters: details.job.description.length,
    workplaces: details.job.workplaces.length, source_response_sha256: hash(details.raw_response),
    preserved_full_source_body: true, reference_sha256: hash(first.jobs[0].reference_number) };
  receipt.status = 'PASS';
} catch (error) {
  receipt.status = 'FAIL'; receipt.error = error.message; process.exitCode = 1;
} finally {
  await client.close();
  await mkdir(new URL('../.live-test/', import.meta.url), { recursive: true });
  await writeFile(new URL('../.live-test/latest.json', import.meta.url), `${JSON.stringify(receipt, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
}
