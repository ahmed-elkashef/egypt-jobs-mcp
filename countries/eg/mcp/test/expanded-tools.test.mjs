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

test('native API page zero and exact continuation reach complete-body backend',async()=>{
  const {definitions,calls}=registered();
  const tool=definitions.get('read_public_api_jobs');
  assert.equal(tool.config.inputSchema.page.parse(0),0);
  await tool.handler({source:'themuse',page:0,testing:true});
  await tool.handler({source:'arbeitnow',next_url:'https://www.arbeitnow.com/api/job-board-api?page=2',testing:false});
  assert.deepEqual(calls,[
    [['themuse','--page','0','--testing'],undefined,'egypt_job_sources.public_apis'],
    [['arbeitnow','--next-url','https://www.arbeitnow.com/api/job-board-api?page=2'],undefined,'egypt_job_sources.public_apis']
  ]);
  assert.match(tool.config.description,/registered app/);
});

test('invalid API pagination and cross-source testing are refused without transport',async()=>{
  const {definitions,calls}=registered();
  const handler=definitions.get('read_public_api_jobs').handler;
  for(const args of [
    {source:'arbeitnow',page:0,testing:false},
    {source:'arbeitnow',page:1,testing:true},
    {source:'themuse',page:0,next_url:'https://www.themuse.com/api/public/jobs?page=1',testing:true}
  ]) assert.equal((await handler(args)).isError,true);
  assert.equal(calls.length,0);
});

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
