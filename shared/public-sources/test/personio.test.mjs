import {test} from 'node:test';
import assert from 'node:assert/strict';
import {personio, personioTools} from '../personio.mjs';

test('Personio exact primary advert route is read-only and requires one URL', () => {
  assert.equal(personioTools.length, 1);
  assert.equal(personioTools[0].annotations.readOnlyHint, true);
  assert.deepEqual(personioTools[0].inputSchema.required, ['job_url']);
  assert.equal(personioTools[0].inputSchema.additionalProperties, false);
});
test('Personio native URL is forwarded as one argument to the fixed original reader', async () => {
  const url = 'https://example.jobs.personio.de/job/67?language=en';
  const result = await personio('personio_detail', {job_url:url}, {run: async argv => {
    assert.deepEqual(argv, ['--job-url', url]);
    return {source:'personio',status:'ok',returned_count:1,full_posting_reviewed:false};
  }});
  assert.equal(result.status, 'ok');
  assert.equal(result.full_posting_reviewed, false);
});
test('Personio malformed or narrowing arguments never invoke a reader or become empty ads', async () => {
  for (const args of [null, [], {}, {job_url:7}, {job_url:''}, {job_url:'x'.repeat(4097)}, {job_url:'https://example.jobs.personio.de/job/67',country:'DE'}]) {
    const result = await personio('personio_detail', args, {run: async () => assert.fail('must not invoke')});
    assert.equal(result.status, 'source_limited');assert.equal(result.returned_count, null);
  }
});
test('Personio unknown operation is a null-count refusal', async () => {
  const result = await personio('personio_apply', {job_url:'https://example.jobs.personio.de/job/67'}, {run:async () => assert.fail('must not invoke')});
  assert.equal(result.status, 'source_limited');assert.equal(result.source_result_count, null);
});
