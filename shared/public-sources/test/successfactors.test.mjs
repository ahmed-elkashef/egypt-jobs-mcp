import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {successfactors, successfactorsTools, runSuccessfactors} from '../successfactors.mjs';

test('native SAP RMK tools accept only explicit readonly discovery/list/detail', () => {
  assert.equal(successfactorsTools.length, 3);
  for (const tool of successfactorsTools) {
    assert.equal(tool.annotations.readOnlyHint, true);
    assert.equal(tool.inputSchema.additionalProperties, false);
  }
  assert.deepEqual(successfactorsTools[1].inputSchema.properties.country.enum, ['DE', 'EG']);
  assert.ok(!('query' in successfactorsTools[1].inputSchema.properties));
});
test('frozen continuation and raw geography reach fixed reader arguments', async () => {
  const seen = [];
  const run = async argv => {seen.push(argv); return {status: 'ok'};};
  await successfactors('successfactors_inventory', {board_url: 'https://careers.sap.com/search/', country: 'DE', page: 2, first_page_total: 122}, {run});
  await successfactors('successfactors_detail', {job_url: 'https://careers.sap.com/job/Example/123456789/'}, {run});
  assert.deepEqual(seen, [
    ['--board-url', 'https://careers.sap.com/search/', '--country', 'DE', '--page', '2', '--first-page-total', '122'],
    ['--job-url', 'https://careers.sap.com/job/Example/123456789/'],
  ]);
});
test('role queries credentials unknown operations and unbound continuation never invoke reader', async () => {
  const run = () => {throw Error('must not invoke');};
  const invalid = [
    {board_url: 'x', query: 'PR'}, {board_url: 'x', token: 'secret'}, {board_url: 'x', page: 2},
    {board_url: 'x', country: 'ZZ'}, {board_url: 'x', page: true}, {board_url: 'x', first_page_total: false},
    {board_url: 'x', toString: 'unexpected'}, null, [],
  ];
  for (const args of invalid) {
    const result = await successfactors('successfactors_inventory', args, {run});
    assert.equal(result.status, 'source_limited');
    assert.equal(result.returned_count, null);
  }
  assert.equal((await successfactors('apply', {}, {run})).status, 'source_limited');
  assert.equal((await successfactors('successfactors_capabilities', {country: 'DE'}, {run})).status, 'source_limited');
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
test('complete job variants and raw student/fulltime dimensions survive IPC without credentials', async () => {
  const value = {status: 'ok', source: 'successfactors', description: 'Full source. '.repeat(10000), native_display_fields: {'Career Status': 'Student', 'Employment Type': 'Limited Full Time'}};
  const result = await runSuccessfactors([], {
    env: {PATH: '/usr/bin', SUCCESSFACTORS_TOKEN: 'never', THEMUSE_API_KEY: 'not-this-source'},
    spawnProcess: childFixture(JSON.stringify(value), options => {
      assert.deepEqual(options.env, {PATH: '/usr/bin'});
      assert.equal(options.shell, false);
    }),
  });
  assert.deepEqual(result, value);
});
test('wrong-source or malformed IPC is unknown supply, never a successful empty market', async () => {
  for (const body of ['broken', '[]', JSON.stringify({status: 'ok', source: 'jobshop', returned_count: 0})]) {
    const result = await runSuccessfactors([], {spawnProcess: childFixture(body)});
    assert.equal(result.status, 'source_limited');
    assert.equal(result.returned_count, null);
    assert.ok(!('listings' in result));
  }
});
