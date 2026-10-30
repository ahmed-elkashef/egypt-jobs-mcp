import test from 'node:test';
import assert from 'node:assert/strict';
import {ausbildung} from '../countries/de/public-services/ausbildung.mjs';
import {ALLOWED} from '../lib/federation.mjs';
const binding={source:'ausbildung_de',catalogue:'https://www.ausbildung.de/schuelerpraktikum/stellen/',
 protocol_sha256:'2a3916610a6dcb25d4ff77510fd21b01119f1685d8bf530a59035f430567d40c',resultsCount:41,vacanciesCount:123,countryEntryCode:'DE'};
const url='https://www.ausbildung.de/schuelerpraktikum/stellen/synthetic-internship-00000000-0000-4000-8000-000000000001/';
function capture(){const calls=[];return {calls,run:async argv=>{calls.push(argv);return {status:'ok'};}};}
test('Ausbildung initial whole native scope has no career degree geography or duration query',async()=>{
 const p=capture();await ausbildung('ausbildung_inventory',{},p);assert.deepEqual(p.calls,[['inventory','--from','0']]);
});
test('Ausbildung native increment binds exact acquired result and place counters',async()=>{
 const p=capture();await ausbildung('ausbildung_inventory',{from:20,native_binding:binding},p);
 assert.deepEqual(p.calls,[['inventory','--from','20','--native-binding',JSON.stringify(binding)]]);
});
test('Ausbildung offsets reject null coercion fractional nonnative and past bound values before spawn',async()=>{
 for(const from of [null,true,'20',-20,1,20.5,60,10000000]){
  const p=capture(),r=await ausbildung('ausbildung_inventory',{from,native_binding:binding},p);
  assert.equal(p.calls.length,0);assert.equal(r.returned_count,null);
 }
});
test('Ausbildung resume refuses missing null changed protocol and injected server action references',async()=>{
 for(const native_binding of [undefined,null,{}, {...binding,protocol_sha256:'0'.repeat(64)},
  {...binding,resultsCount:true},{...binding,read_function:'apply'}, {...binding,countryEntryCode:'AT'}]){
  const p=capture();await ausbildung('ausbildung_inventory',{from:20,native_binding},p);assert.equal(p.calls.length,0);
 }
 for(const native_binding of [null,binding]){
  const p=capture();await ausbildung('ausbildung_inventory',{native_binding},p);assert.equal(p.calls.length,0);
 }
});
test('Ausbildung source cannot accept role model arbitrary action cookie or query arguments',async()=>{
 for(const args of [{query:'communications'},{role:'HR'},{internshipKinds:['Pflichtpraktikum']},
  {where:'Frankfurt'},{duration:6},{action:'apply'},{cookie:'forbidden'},{limit:1}]){
  const p=capture();await ausbildung('ausbildung_inventory',args,p);assert.equal(p.calls.length,0);
 }
});
test('Ausbildung detail accepts only exact public native advert without application or query controls',async()=>{
 const p=capture();await ausbildung('ausbildung_detail',{url},p);assert.deepEqual(p.calls,[['detail','--url',url]]);
 for(const bad of [url+'bewerben/',url+'?from=20',url+'#apply',url+'\n',url.replace('.de/','.de.evil.invalid/')]){
  const q=capture();await ausbildung('ausbildung_detail',{url:bad},q);assert.equal(q.calls.length,0);
 }
 const q=capture();await ausbildung('ausbildung_detail',{url,from:0},q);assert.equal(q.calls.length,0);
});
test('Ausbildung unknown candidate write operations refuse before native reader',async()=>{
 for(const name of ['apply','ausbildung_apply','subscribe','save','login']){
  const p=capture();await ausbildung(name,{},p);assert.equal(p.calls.length,0);
 }
});
test('federation exposes only two original Ausbildung public read routes',()=>{
 assert.ok(ALLOWED.public_de.has('ausbildung_inventory'));assert.ok(ALLOWED.public_de.has('ausbildung_detail'));
 assert.ok(!ALLOWED.public_de.has('ausbildung_apply'));
});
