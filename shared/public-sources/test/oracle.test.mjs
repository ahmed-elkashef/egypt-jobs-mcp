import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {oracle, oracleTools, runOracle} from '../oracle.mjs';

test('Oracle routes are explicit read-only source operations with no role queries', () => {
  assert.equal(oracleTools.length, 3);
  for (const tool of oracleTools) {
    assert.equal(tool.annotations.readOnlyHint, true);
    assert.equal(tool.inputSchema.additionalProperties, false);
  }
  assert.deepEqual(oracleTools[1].inputSchema.properties.country.enum, ['DE']);
  assert.ok(!('keyword' in oracleTools[1].inputSchema.properties));
});
test('country and frozen continuation reach fixed reader arguments', async () => {
  const seen = [];
  const run = async argv => {seen.push(argv); return {status: 'ok'};};
  await oracle('oracle_inventory', {board_url: 'board', country: 'DE', page: 2, first_page_total: 50}, {run});
  await oracle('oracle_detail', {job_url: 'job'}, {run});
  assert.deepEqual(seen, [
    ['--board-url', 'board', '--country', 'DE', '--page', '2', '--first-page-total', '50'],
    ['--job-url', 'job'],
  ]);
});
test('unknown operations candidate credentials and unbound pages never invoke reader', async () => {
  const run = () => {throw Error('must not invoke');};
  for (const args of [null, [], {board_url: 'x', keyword: 'PR'}, {board_url: 'x', candidateNumber: 'x'},
    {board_url: 'x', cookie: 'x'}, {board_url: 'x', country: 'EG'}, {board_url: 'x', page: 2},
    {board_url: 'x', page: true}, {board_url: 'x', first_page_total: 1.5}]) {
    const result = await oracle('oracle_inventory', args, {run});
    assert.equal(result.returned_count, null);
    assert.equal(result.status, 'source_limited');
  }
  assert.equal((await oracle('apply', {}, {run})).status, 'source_limited');
  assert.equal((await oracle('oracle_capabilities', {token: 'x'}, {run})).status, 'source_limited');
});
function childFixture(body, inspect = () => {}) {
  return (_command, _args, options) => {
    inspect(options);
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.kill = () => true;
    queueMicrotask(() => {child.stdout.emit('data', Buffer.from(body)); child.emit('close', 0);});
    return child;
  };
}
test('complete public body variants survive IPC while credentials stay outside child env', async () => {
  const value = {status: 'ok', source: 'oracle', description: 'Complete. '.repeat(20000),
    native_public_sections: {ExternalDescriptionStr: {text: 'Full body.'}}, native_job_id: '210000001', native_requisition_id: 300000001};
  const result = await runOracle([], {
    env: {PATH: '/usr/bin', ORACLE_TOKEN: 'never', THEMUSE_API_KEY: 'other-source'},
    spawnProcess: childFixture(JSON.stringify(value), options => {
      assert.deepEqual(options.env, {PATH: '/usr/bin'});
      assert.equal(options.shell, false);
    }),
  });
  assert.deepEqual(result, value);
});
test('broken or wrong-source IPC is unknown supply, never an empty market', async () => {
  for (const value of ['broken', '[]', JSON.stringify({status: 'ok', source: 'successfactors', returned_count: 0})]) {
    const result = await runOracle([], {spawnProcess: childFixture(value)});
    assert.equal(result.status, 'source_limited');
    assert.equal(result.returned_count, null);
  }
});
