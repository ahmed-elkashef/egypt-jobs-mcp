import test from 'node:test';
import assert from 'node:assert/strict';
import {read,endpoint,capabilities} from '../countries/de/interamt/client.mjs';
const base='https://www.interamt.de/koop/rest/v1/import';
const env={INTERAMT_API_BASE:base,INTERAMT_API_KEY:'synthetic-test-key'};
test('official API stays read-only and does not describe one customer as all German vacancies',()=>{
  assert.deepEqual(capabilities().methods,['GET']);assert.match(capabilities().scope,/one authorized customer/);
  assert.equal(endpoint({operation:'detail',id:42},base),base+'/Stellenangebote/42');
  for(const input of [{operation:'delete',id:1},{operation:'detail',id:'../1'},{operation:'agency_list',id:3}])assert.throws(()=>endpoint(input,base));
  assert.throws(()=>endpoint({operation:'agency_list'},'https://example.invalid/private'));
});
test('missing approved access or explicit deployment refuses before any network',async()=>{
  let calls=0;const fetchImpl=async()=>{calls++;throw Error('must not fetch');};
  assert.equal((await read({operation:'agency_list'},{env:{},fetchImpl})).status,'credential_required');
  assert.equal((await read({operation:'agency_list'},{env:{INTERAMT_API_KEY:'synthetic'},fetchImpl})).status,'configuration_required');
  assert.equal((await read({operation:'delete'},{env,fetchImpl})).status,'invalid_request');assert.equal(calls,0);
});
test('all native fields and large full descriptions survive a customer array',async()=>{
  const raw={stellenangebote:Array.from({length:350},(_,id)=>({id,Beschreibung:{body:'Full text '.repeat(500)},unknown:{keep:true}}))};
  let calls=0;
  const result=await read({operation:'agency_list'},{env,fetchImpl:async(url,opts)=>{
    calls++;assert.equal(opts.method,'GET');assert.equal(opts.redirect,'manual');assert.equal(opts.headers['X-API-Key'],env.INTERAMT_API_KEY);
    assert.equal(url,base+'/Stellenangebote');return new Response(JSON.stringify(raw),{headers:{'content-type':'application/json'}});
  }});
  assert.equal(calls,1);assert.deepEqual(result.raw_response,raw);assert.equal(result.native_returned_count,350);
  assert.equal(result.coverage_complete,false);assert.ok(!JSON.stringify(result).includes('synthetic-test-key'));
});
test('empty native array differs from missing envelope; 401/429/redirect are errors without retry',async()=>{
  const valid=await read({operation:'agency_list'},{env,fetchImpl:async()=>new Response('{"stellenangebote":[]}',{headers:{'content-type':'application/json'}})});
  assert.equal(valid.status,'ok');assert.equal(valid.native_returned_count,0);
  const malformed=await read({operation:'agency_list'},{env,fetchImpl:async()=>new Response('{}',{headers:{'content-type':'application/json'}})});
  assert.equal(malformed.code,'missing_inventory');
  for(const status of [301,401,429]){
    let calls=0;const result=await read({operation:'agency_list'},{env,fetchImpl:async()=>{calls++;return new Response('ignored',{status,headers:{'retry-after':'60'}});}});
    assert.equal(calls,1);assert.equal(result.http_status,status);assert.equal(result.coverage_complete,false);assert.equal(result.retry_after,'60');
  }
});
test('oversized and malformed JSON never return partial success',async()=>{
  const big=await read({operation:'agency_list'},{env,maxBytes:3,fetchImpl:async()=>new Response('{"stellenangebote":[]}',{headers:{'content-type':'application/json'}})});
  assert.equal(big.code,'response_too_large');assert.ok(!('raw_response'in big));
  const bad=await read({operation:'detail',id:5},{env,fetchImpl:async()=>new Response('{',{headers:{'content-type':'application/json'}})});
  assert.equal(bad.code,'invalid_json');
});
