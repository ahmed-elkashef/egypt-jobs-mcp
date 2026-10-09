import test from 'node:test';
import assert from 'node:assert/strict';
import { registerExpandedSources } from '../expanded-tools.mjs';

function registered() {
  const definitions = new Map();
  const calls = [];
  registerExpandedSources({registerTool(name, config, handler) { definitions.set(name, {config, handler}); }},
    async (...args) => { calls.push(args); return {structuredContent:{status:'ok'}}; });
  return {definitions,calls};
}

test('aware Freelancer activity interval forwards exact dates without changing offset',async () => {
  const {definitions,calls} = registered();
  const tool = definitions.get('read_freelance_projects');
  const lower='2026-01-01T02:00:00+02:00', upper='2026-01-03T00:00:00Z';
  assert.equal(tool.config.inputSchema.from_time.parse(lower),lower);
  assert.throws(()=>tool.config.inputSchema.from_time.parse('2026-01-01T00:00:00'));
  await tool.handler({source:'freelancer',limit:100,offset:98,from_time:lower,to_time:upper});
  assert.deepEqual(calls, [[['--source','freelancer','--limit','100','--offset','98','--from-time',lower,'--to-time',upper],undefined,'egypt_job_sources.freelance']]);
  assert.match(tool.config.description,/UPDATE activity/);
  assert.match(tool.config.description,/billing limit/);
});

test('partial dates and cross-source dates are refused without invoking backend',async () => {
  const {definitions,calls}=registered();
  const handler=definitions.get('read_freelance_projects').handler;
  for (const args of [
    {source:'freelancer',limit:100,offset:0,from_time:'2026-01-01T00:00:00Z'},
    {source:'freelancer',limit:100,offset:0,to_time:'2026-01-03T00:00:00Z'},
    {source:'upwork',limit:10,offset:0,from_time:'2026-01-01T00:00:00Z',to_time:'2026-01-03T00:00:00Z'},
  ]) {
    const refused=await handler(args);
    assert.equal(refused.isError,true);
    assert.equal(refused.structuredContent.coverage_complete,false);
    assert.ok(!('listings' in refused.structuredContent));
  }
  assert.equal(calls.length,0);
});
