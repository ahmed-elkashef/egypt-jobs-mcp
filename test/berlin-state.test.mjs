import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {statePortal,runStatePortal} from '../countries/de/public-services/state-portals.mjs';
import {ALLOWED} from '../lib/federation.mjs';
const scope={provider:'berlin',scope:'student_entry'};
function capture(){const calls=[];return{calls,run:async argv=>{calls.push(argv);return{status:'ok'};}};}
test('Berlin native initial scope has no role query or artificial personal-use gate',async()=>{
 const p=capture();await statePortal('state_portal_inventory',scope,p);
 assert.deepEqual(p.calls,[['state_inventory','--provider','berlin','--scope','student_entry','--start','0']]);
});
test('Berlin continuation carries original total and native offset',async()=>{
 const p=capture();await statePortal('state_portal_inventory',{...scope,start:20,first_page_total:43},p);
 assert.deepEqual(p.calls,[['state_inventory','--provider','berlin','--scope','student_entry','--start','20','--first-page-total','43']]);
});
test('missing or contradictory native total refuses before spawn',async()=>{
 for(const args of [{...scope,start:20},{...scope,first_page_total:43},{...scope,start:20,first_page_total:20},{...scope,start:20,first_page_total:true}]){
  const p=capture();const r=await statePortal('state_portal_inventory',args,p);assert.equal(p.calls.length,0);assert.equal(r.returned_count,null);
 }
});
test('unknown providers roles fields and operations cannot broaden a reader',async()=>{
 for(const args of [{...scope,provider:'hessen'},{...scope,scope:'internships'},{...scope,keyword:'PR'},{...scope,url:'https://example.invalid'},{...scope,personal_noncommercial_use:true}]){
  const p=capture();await statePortal('state_portal_inventory',args,p);assert.equal(p.calls.length,0);
 }
 const p=capture();await statePortal('apply',scope,p);assert.equal(p.calls.length,0);
});
test('offsets and boundaries are integers without coercion',async()=>{
 for(const start of ['20',true,null,-1,1000001,1.5]){const p=capture();await statePortal('state_portal_inventory',{...scope,start,first_page_total:43},p);assert.equal(p.calls.length,0);}
});
test('exact public advert URI is a separate argument and cannot take list scope',async()=>{
 const p=capture(),url='https://www.karriereportal-stellen.berlin.de/Role-de-j1.html';
 await statePortal('state_portal_detail',{provider:'berlin',url},p);
 assert.deepEqual(p.calls,[['state_detail','--provider','berlin','--url',url]]);
 const q=capture();await statePortal('state_portal_detail',{...scope,url},q);assert.equal(q.calls.length,0);
});
test('only two read-only state operations federate',()=>{
 assert.ok(ALLOWED.public_de.has('state_portal_inventory'));assert.ok(ALLOWED.public_de.has('state_portal_detail'));
 assert.ok(!ALLOWED.public_de.has('state_portal_apply'));
});
test('native process bridge binds correct provider and count envelope',async()=>{
 const spawnProcess=()=>{const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>{};
  queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(JSON.stringify({status:'ok',source:'berlin_state_jobs',returned_count:1})));child.emit('close',0);});return child;};
 const r=await runStatePortal(['state_inventory'],{spawnProcess,env:{}});assert.equal(r.source,'berlin_state_jobs');assert.equal(r.status,'ok');
});
