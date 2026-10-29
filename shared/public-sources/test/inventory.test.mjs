import { test } from 'node:test';
import assert from 'node:assert/strict';
import { InventoryClient, normalizeRecord, publication, requestText, SourceError, errorResult } from '../inventory.mjs';
const reply = (body, status=200, headers={}) => new Response(typeof body==='string'?body:JSON.stringify(body),{status,headers});
const row = i => ({slug:`synthetic-${i}`,title:'Synthetic example',company_name:'Example',description:'<p>Full &amp; unchanged</p>',created_at:1700000000});
test('325 native rows survive; continuation above former page25 cap is exact',async()=>{
  let requests=0;const client=new InventoryClient({fetchImpl:async url=>{requests++;assert.match(url,/page=26/);return reply({data:Array.from({length:325},(_,i)=>row(i)),links:{next:'https://www.arbeitnow.com/api/job-board-api?page=27'}});}});
  const data=await client.inventory({source:'arbeitnow',page:26});assert.equal(data.count,325);assert.equal(data.raw_count,325);assert.deepEqual(data.pagination.next,{page:27});assert.equal(data.jobs[0].description,undefined);
  const full=client.detail({snapshot_id:data.snapshot_id,source_id:'synthetic-0'});assert.equal(full.job.description,'Full & unchanged');assert.equal(requests,1);
});
test('full text over2500 characters and original HTML remain in captured detail',async()=>{
  const html='<p>'+('Meaningful text '.repeat(2500))+'</p>';const client=new InventoryClient({fetchImpl:async()=>reply({jobs:[{id:1,title:'Example',description:html,publication_date:'2026-10-01T12:00:00+02:00'}]})});
  const data=await client.inventory({source:'remotive'});const full=client.detail({snapshot_id:data.snapshot_id,source_id:'1'});assert.equal(full.job.description_html,html);assert.equal(full.job.source_data.description,html);assert.ok(full.job.description.length>30000);assert.equal(full.job.publication.instant,'2026-10-01T10:00:00.000Z');assert.ok(data.provider_notices.length);
});
test('Himalayas string country restrictions remain exact; missing restrictions do not become worldwide',()=>{
  const raw={guid:'example',locationRestrictions:['United States','Canada'],timezoneRestrictions:['America/New_York'],employmentType:'Contract',pubDate:1700000000};const job=normalizeRecord('himalayas',raw);assert.equal(job.location,'United States, Canada');assert.deepEqual(job.locationRestrictions,raw.locationRestrictions);assert.equal(job.employment_type,'Contract');assert.equal(normalizeRecord('himalayas',{guid:'unknown'}).location,null);
});
test('native Muse page0 and next-page counts survive zero values',async()=>{
  const client=new InventoryClient({fetchImpl:async url=>{assert.match(url,/page=0/);return reply({results:[],page:0,total:0,page_count:1});}});const data=await client.inventory({source:'themuse',page:0});assert.equal(data.pagination.page,0);assert.equal(data.pagination.total,0);assert.equal(data.count,0);assert.equal(data.pagination.next,null);
});
test('HTTP403 and429 remain errors with retry metadata, never empty successful markets',async()=>{
  for(const status of [403,429]){const client=new InventoryClient({fetchImpl:async()=>reply('denied',status,{'retry-after':'60'})});await assert.rejects(client.inventory({source:'themuse'}),error=>{assert.equal(error.http_status,status);const result=errorResult(error);assert.equal(result.jobs,null);assert.equal(result.error.retry_after,'60');return true;});}
});
test('timeout aborts a hung request without retry',async()=>{
  let calls=0;await assert.rejects(requestText('https://example.invalid',{timeout:10,fetchImpl:async(_,options)=>{calls++;return new Promise((_,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('aborted'))));}}),error=>error.code==='timeout');assert.equal(calls,1);
});
test('malformed response is distinct from a real empty feed',async()=>{
  await assert.rejects(new InventoryClient({fetchImpl:async()=>reply({error:'no data'})}).inventory({source:'arbeitnow'}),error=>error.code==='malformed_response');assert.equal((await new InventoryClient({fetchImpl:async()=>reply({data:[],links:{next:null}})}).inventory({source:'arbeitnow'})).count,0);
});
test('snapshots expire and returned objects cannot mutate captured originals',async()=>{
  let now=1700000000000;const client=new InventoryClient({clock:()=>now,ttlMs:10,fetchImpl:async()=>reply({data:[row(1)]})});const data=await client.inventory({source:'arbeitnow',metadata_only:false});data.jobs[0].source_data.title='changed';assert.equal(client.detail({snapshot_id:data.snapshot_id,source_id:'synthetic-1'}).job.title,'Synthetic example');now+=10;assert.throws(()=>client.detail({snapshot_id:data.snapshot_id,source_id:'synthetic-1'}),error=>error.code==='snapshot_unavailable');
});
test('Personio nested sections, schedule, contract, date precision and namespace survive',async()=>{
  const xml='<workzag-jobs><position><id>7</id><name>Example</name><office>Berlin</office><schedule>part-time</schedule><employmentType>permanent</employmentType><createdAt>2026-10-01</createdAt><jobDescriptions><jobDescription><name>Responsibilities</name><value><![CDATA[<p>Deliver a full example.</p>]]></value></jobDescription><jobDescription><name>Requirements</name><value><![CDATA[<p>Accurate data.</p>]]></value></jobDescription></jobDescriptions></position></workzag-jobs>';
  // Missing the actual provider root must not silently become an empty board.
  await assert.rejects(new InventoryClient({fetchImpl:async()=>reply(xml.replaceAll("workzag-jobs","unexpected-root"))}).inventory({source:'personio',subdomain:'example'}),error=>error.code==='malformed_response');
  const client=new InventoryClient({fetchImpl:async()=>reply(xml.replaceAll('workzag-jobs','workzag_jobs'))});const data=await client.inventory({source:'personio',subdomain:'example'});const job=client.detail({snapshot_id:data.snapshot_id,source_id:'7'}).job;assert.match(job.description,/Requirements\nAccurate data/);assert.equal(job.schedule,'part-time');assert.equal(job.board_id,'example');assert.equal(job.publication.precision,'calendar_date');assert.equal(job.publication.instant,null);
});
test('duplicate and missing IDs are explicit and lossless through record_index',async()=>{
  const client=new InventoryClient({fetchImpl:async()=>reply({data:[row(1),{...row(1),title:'Changed'}, {...row(2),slug:null}]})});const data=await client.inventory({source:'arbeitnow'});assert.equal(data.raw_count,3);assert.equal(data.count,2);assert.equal(data.quarantine.length,1);assert.equal(data.duplicate_ids[0].count,2);assert.throws(()=>client.detail({snapshot_id:data.snapshot_id,source_id:'synthetic-1'}),error=>error.code==='ambiguous_source_id');assert.equal(client.detail({snapshot_id:data.snapshot_id,source_id:'synthetic-1',record_index:1}).job.title,'Changed');
});
test('unsafe continuation, malformed page and board injection are rejected',async()=>{
  const client=new InventoryClient({fetchImpl:async()=>reply({data:[row(1)],links:{next:'https://other.invalid/path?page=2'}})});await assert.rejects(client.inventory({source:'arbeitnow'}),error=>error.code==='invalid_continuation');await assert.rejects(client.inventory({source:'personio',subdomain:'example.invalid/path'}),error=>error.code==='invalid_argument');await assert.rejects(client.inventory({source:'himalayas',page:1.5}),error=>error.code==='invalid_argument');
});
test('no invented publication instants or updates promoted to original publication',()=>{
  assert.equal(publication('2026-10-01').instant,null);assert.equal(publication('2026-10-01T12:00:00').precision,'timezone_unconfirmed');assert.equal(publication(NaN).precision,'invalid');assert.equal(normalizeRecord('remotive',{id:1,updatedAt:'2026-10-01T00:00:00Z'}).publication.raw,null);
});
test('memory limits fail explicitly rather than silently discard native rows',async()=>{
  const client=new InventoryClient({maxBytes:1,fetchImpl:async()=>reply({data:[row(1)]})});await assert.rejects(client.inventory({source:'arbeitnow'}),error=>error.code==='capacity_limit');
});

test('legacy native Himalayas selectors are actually forwarded',async()=>{
 const client=new InventoryClient({fetchImpl:async url=>{const u=new URL(url);assert.equal(u.searchParams.get('worldwide'),'true');assert.equal(u.searchParams.get('seniority'),'Entry-level');assert.equal(u.searchParams.get('sort'),'oldest');return reply({jobs:[],totalCount:0,offset:0,limit:20});}});
 await client.inventory({source:'himalayas',worldwide:true,seniority:'Entry-level',sort:'oldest'});
});

test('quarantined missing-ID bodies remain inspectable without invented identity',async()=>{
 const client=new InventoryClient({fetchImpl:async()=>reply({data:[{title:'Example',description:'Complete unkeyed body'}]})});const data=await client.inventory({source:'arbeitnow'});assert.equal(data.count,0);assert.equal(data.quarantine.length,1);const d=client.detail({snapshot_id:data.snapshot_id,record_index:0});assert.equal(d.job.id,null);assert.equal(d.job.description,'Complete unkeyed body');
});
test('contradictory native pagination is an error, not a wrong-page success',async()=>{
 for(const [args,body] of [[{source:'arbeitnow',page:5},{data:[],meta:{current_page:4},links:{next:'https://www.arbeitnow.com/api/job-board-api?page=4'}}],[{source:'themuse',page:3},{results:[],page:1,page_count:10}],[{source:'himalayas',page:3},{jobs:[],offset:0,limit:20,totalCount:100}]]) await assert.rejects(new InventoryClient({fetchImpl:async()=>reply(body)}).inventory(args),e=>e.code==='invalid_continuation');
});
test('description objects are errors; created dates retain their exact basis',()=>{
 assert.throws(()=>normalizeRecord('arbeitnow',{slug:'a',description:{html:'not a native string'}}),e=>e.code==='malformed_response');assert.equal(normalizeRecord('arbeitnow',row(1)).publication.basis,'provider_created_at');
});

test('RemoteOK stable IDs remain records even with missing titles; Personio error is not empty',async()=>{
 const data=await new InventoryClient({fetchImpl:async()=>reply([{legal:'notice'},{id:'1',description:'Complete job body'}])}).inventory({source:'remoteok'});assert.equal(data.raw_count,1);assert.equal(data.count,1);assert.equal(data.provider_notices.length,1);
 await assert.rejects(new InventoryClient({fetchImpl:async()=>reply('<workzag_jobs><error>Forbidden</error></workzag_jobs>')}).inventory({source:'personio',subdomain:'example'}),e=>e.code==='malformed_response');
});
