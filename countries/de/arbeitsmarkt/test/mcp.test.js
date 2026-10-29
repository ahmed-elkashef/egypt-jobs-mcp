import test from 'node:test';
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { createServer } from '../src/server.js';

test('actual MCP protocol preserves all nine tools across six families and structured job results', async () => {
  const server = createServer({ jobsuche: { async request(endpoint) {
    if (endpoint === 'pc/v6/jobs') return { ergebnisliste: [{ stelle: { referenznummer: 'TEST-1',
      stellenangebotsTitel: 'Synthetic', stellenlokationen: [] } }], maxErgebnisse: 1, page: 1, size: 25 };
    return { stellenangebotsBeschreibung: 'Complete synthetic detail.' };
  } }, entgeltatlas: { async request() { throw new Error('synthetic salary service failure'); } } });
  const client = new Client({ name: 'integration-test', version: '1.0.0' });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  try {
    const { tools } = await client.listTools();
    assert.deepEqual(tools.map(tool => tool.name).sort(), ['ausbildung_suche', 'coaching_suche',
      'gehalt_regionen', 'gehalt_suche', 'job_details', 'job_suche', 'studienfelder',
      'studium_suche', 'weiterbildung_suche'].sort());
    assert.equal(tools.every(tool => tool.annotations.readOnlyHint === true), true);
    const page = await client.callTool({ name: 'job_suche', arguments: {} });
    assert.equal(page.structuredContent.jobs[0].reference_number, 'TEST-1');
    assert.equal(JSON.parse(page.content[0].text).kind, 'ba_job_search_page');
    const detail = await client.callTool({ name: 'job_details', arguments: { hashId: 'TEST' } });
    assert.equal(detail.structuredContent.job.description, 'Complete synthetic detail.');
    const failed = await client.callTool({ name: 'gehalt_regionen', arguments: {} });
    assert.equal(failed.isError, true);
  } finally { await client.close(); await server.close(); }
});
