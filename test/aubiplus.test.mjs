import test from 'node:test';
import assert from 'node:assert/strict';
import {aubiPlus} from '../countries/de/public-services/aubiplus.mjs';
import {ALLOWED} from '../lib/federation.mjs';
function capture(){const calls=[];return{calls,run:async argv=>{calls.push(argv);return{status:'ok'};}};}
test('AUBI initial all source is explicit native scope with no role fields',async()=>{
 const p=capture();await aubiPlus('aubiplus_inventory',{},p);
 assert.deepEqual(p.calls,[['inventory','--scope','all','--page','1']]);
});
test('native student scopes do not require an artificial personal-use gate',async()=>{
 for(const scope of ['student_internship','working_student']){const p=capture();await aubiPlus('aubiplus_inventory',{scope},p);assert.deepEqual(p.calls,[['inventory','--scope',scope,'--page','1']]);}
});
test('continuation carries exact acquired URI and original native counter',async()=>{
 const p=capture(),url='https://www.aubi-plus.de/suchmaschine/suche/?fLand%5B0%5D=deutschland&fTyp%5B0%5D=werkstudent&seite=2';
 await aubiPlus('aubiplus_inventory',{scope:'working_student',page:2,first_page_total:52,continuation_url:url},p);
 assert.deepEqual(p.calls,[['inventory','--scope','working_student','--page','2','--first-page-total','52','--continuation-url',url]]);
});
test('missing contradictory or ill-typed continuation refuses before spawn',async()=>{
 for(const args of [{page:2},{first_page_total:52},{continuation_url:'https://example.invalid'},{page:2,first_page_total:true,continuation_url:'https://example.invalid'},{page:2,first_page_total:52}]){const p=capture(),r=await aubiPlus('aubiplus_inventory',args,p);assert.equal(p.calls.length,0);assert.equal(r.returned_count,null);}
});
test('role queries geography extra fields unknown operations and scope refuse',async()=>{
 for(const args of [{keyword:'PR'},{scope:'marketing'},{country:'EG'},{personal_noncommercial_use:true},{scope:[]},{url:'https://example.invalid'}]){const p=capture();await aubiPlus('aubiplus_inventory',args,p);assert.equal(p.calls.length,0);}
 const p=capture();await aubiPlus('apply',{},p);assert.equal(p.calls.length,0);
});
test('page values are bounded native integers without coercion',async()=>{
 for(const page of [true,'2',null,0,-1,10001,1.5]){const p=capture();await aubiPlus('aubiplus_inventory',{page},p);assert.equal(p.calls.length,0);}
});
test('exact advert URI remains separate from inventory arguments',async()=>{
 const p=capture(),url='https://www.aubi-plus.de/praktikum/example-role-1/';await aubiPlus('aubiplus_detail',{url},p);assert.deepEqual(p.calls,[['detail','--url',url]]);
 const q=capture();await aubiPlus('aubiplus_detail',{url,scope:'working_student'},q);assert.equal(q.calls.length,0);
});
test('federation allows only the two original read-only AUBI operations',()=>{
 assert.ok(ALLOWED.public_de.has('aubiplus_inventory'));assert.ok(ALLOWED.public_de.has('aubiplus_detail'));assert.ok(!ALLOWED.public_de.has('aubiplus_apply'));
});
