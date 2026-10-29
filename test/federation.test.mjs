import test from 'node:test';
import assert from 'node:assert/strict';
import {Federation,loadRegistry,validateRegistry,countrySources,scanPlan,publicName,backendSpecs} from '../lib/federation.mjs';

const descriptor=(name,annotations)=>({name,description:'Synthetic read tool',inputSchema:{type:'object',properties:{}},annotations});
test('provider credentials stay scoped to their backend and arbitrary environment secrets are excluded',()=>{
  const specs=backendSpecs({PATH:'/bin',HOME:'/synthetic',INTERAMT_API_KEY:'synthetic',UNRELATED_SECRET:'never',THEMUSE_API_KEY:'muse'});
  assert.equal(specs.public_de.env.INTERAMT_API_KEY,'synthetic');
  assert.ok(!('INTERAMT_API_KEY'in specs.egypt.env));assert.ok(!('UNRELATED_SECRET'in specs.public_de.env));
  assert.equal(specs.public.env.THEMUSE_API_KEY,'muse');
});
function fake(tools,result={content:[],structuredContent:{description:'Full '.repeat(4000),coverage_complete:false}}){
  return {listTools:async()=>({tools}),callTool:async()=>result,close:async()=>{}};
}
test('complete country registry distinguishes working routes, access limits and discovery gaps',async()=>{
  const r=await loadRegistry();
  assert.deepEqual(r.countries.map(c=>c.code),['EG','DE']);
  assert.ok(countrySources(r,'DE').some(s=>s.id==='ba_jobs'));
  assert.ok(countrySources(r,'EG').some(s=>s.id==='wuzzuf'));
  assert.ok(!countrySources(r,'DE').some(s=>s.id==='wuzzuf'));
  assert.equal(r.sources.find(s=>s.id==='forasna').status,'access_limited');
  assert.equal(r.sources.find(s=>s.id==='interamt').status,'credential_required');
  assert.ok(countrySources(r,'DE').some(s=>s.id==='greenhouse'));
  assert.throws(()=>countrySources(r,'ZZ'));
});
test('registry rejects duplicate identities, invented tools and absent implemented routes',async()=>{
  const r=await loadRegistry();
  for(const corrupt of [
    x=>x.sources.push(x.sources[0]),
    x=>x.sources[0].routes[0].tool='send_application',
    x=>x.sources[0].routes=[],
  ]){const x=structuredClone(r);corrupt(x);assert.throws(()=>validateRegistry(x));}
});
test('country plan freezes exact aware bounds, retains gaps and never launches a source',async()=>{
  const r=await loadRegistry();
  const plan=scanPlan(r,{country:'DE',geography:'Germany, all published workplaces',from:'2026-10-01T00:00:00+02:00',to:'2026-10-08T00:00:00+02:00'});
  assert.equal(plan.status,'plan_only');assert.equal(plan.coverage_complete,false);
  assert.ok(plan.unresolved_sources.includes('interamt'));
  assert.ok(plan.source_partitions.some(s=>s.id==='ba_ausbildung'));
  assert.throws(()=>scanPlan(r,{country:'DE',geography:'DE',from:'2026-10-01',to:'2026-10-08'}));
  assert.throws(()=>scanPlan(r,{country:'DE',geography:'DE',from:'2026-10-08T00:00:00Z',to:'2026-10-01T00:00:00Z'}));
});
test('native namespaces cannot collide and new/unapproved backend tools stay unavailable',async()=>{
  const f=new Federation({specs:{egypt:{},ba:{},stepstone:{},public:{}},connect:async id=>fake([
    descriptor(id==='egypt'?'read_source_page':id==='ba'?'job_suche':id==='stepstone'?'get_capabilities':'get_public_inventory'),
    descriptor('send_application',{readOnlyHint:true}),
  ])});
  await f.initialize();
  assert.deepEqual(f.tools().map(t=>t.name).sort(),['de_ba_job_suche','de_stepstone_get_capabilities','eg_read_source_page','shared_get_public_inventory']);
  assert.ok(f.tools().every(t=>t.annotations.readOnlyHint));
  assert.equal((await f.call('send_application',{})).isError,true);
  assert.equal(publicName('egypt','read_remote_feed'),'shared_read_remote_feed');
  await f.close();
});
test('backend failure does not hide working country tools and is never zero supply',async()=>{
  const f=new Federation({specs:{egypt:{},ba:{}},connect:async id=>{if(id==='egypt')throw Error('secret path not exposed');return fake([descriptor('job_suche')]);}});
  await f.initialize();
  assert.equal(f.health().egypt.state,'unavailable');
  assert.ok(!JSON.stringify(f.health()).includes('secret'));
  assert.equal(f.tools().length,1);
  const missing=await f.call('eg_read_source_page',{});
  assert.equal(missing.structuredContent.coverage_complete,false);assert.ok(!('listings'in missing.structuredContent));
  await f.close();
});
test('proxy preserves complete descriptions, native errors and exact continuation',async()=>{
  const native={isError:false,content:[{type:'text',text:'Complete source'}],structuredContent:{description:'word '.repeat(5000),next_page:7,publication:'2026-10-02',coverage_complete:false}};
  const f=new Federation({specs:{ba:{}},connect:async()=>fake([descriptor('job_suche')],native)});
  await f.initialize();assert.deepEqual(await f.call('de_ba_job_suche',{}),native);await f.close();
});
test('legacy JSON-only native output gains equivalent structured content without losing original text',async()=>{
  const data={count:325,snapshot_id:'synthetic',jobs:[{description:'Full '.repeat(4000)}]};
  const text=JSON.stringify(data);
  const f=new Federation({specs:{public:{}},connect:async()=>fake([descriptor('get_public_inventory')],{content:[{type:'text',text}]})});
  await f.initialize();const result=await f.call('shared_get_public_inventory',{});
  assert.equal(result.content[0].text,text);assert.deepEqual(result.structuredContent,data);await f.close();
});
test('oversized complete source result becomes a limit without sliced listings',async()=>{
  const f=new Federation({specs:{ba:{}},connect:async()=>fake([descriptor('job_details')],{content:[],structuredContent:{description:'x'.repeat(10*1024*1024)}})});
  await f.initialize();const r=await f.call('de_ba_job_details',{});
  assert.equal(r.isError,true);assert.equal(r.structuredContent.code,'response_too_large');
  assert.ok(!('description'in r.structuredContent));await f.close();
});
test('changed destructive/read-write contract fails closed before publication',async()=>{
  const f=new Federation({specs:{ba:{}},connect:async()=>fake([descriptor('job_suche',{readOnlyHint:false})])});
  await f.initialize();assert.equal(f.tools().length,0);assert.equal(f.health().ba.state,'unavailable');await f.close();
});
