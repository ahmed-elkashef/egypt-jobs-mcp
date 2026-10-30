import test from 'node:test';
import assert from 'node:assert/strict';
import {gulp} from '../countries/de/public-services/gulp.mjs';
import {ALLOWED} from '../lib/federation.mjs';
function capture(){const calls=[];return{calls,run:async argv=>{calls.push(argv);return{status:'ok'};}};}
test('GULP initial whole source uses native page zero without role filters',async()=>{
 const p=capture();await gulp('gulp_inventory',{},p);assert.deepEqual(p.calls,[['inventory','--page','0']]);
});
test('GULP continuation binds acquired native counter and in-range zero-based page',async()=>{
 const p=capture();await gulp('gulp_inventory',{page:1,first_page_total:21},p);
 assert.deepEqual(p.calls,[['inventory','--page','1','--first-page-total','21']]);
});
test('GULP continuation rejects missing false null fractional and out-of-range counters before spawn',async()=>{
 for(const args of [{page:1},{first_page_total:21},{first_page_total:null},{page:1,first_page_total:true},
  {page:1,first_page_total:null},{page:1,first_page_total:20},{page:2,first_page_total:21},
  {page:1,first_page_total:21.5},{page:1,first_page_total:10000001}]){
  const p=capture(),r=await gulp('gulp_inventory',args,p);assert.equal(p.calls.length,0);assert.equal(r.returned_count,null);
 }
});
test('GULP native page rejects coercion negative fractional and capped values',async()=>{
 for(const page of [true,'1',null,-1,0.5,500000]){const p=capture();await gulp('gulp_inventory',{page},p);assert.equal(p.calls.length,0);}
});
test('GULP role geography work-model language remote and arbitrary API inputs cannot restrict supply',async()=>{
 for(const args of [{query:'marketing'},{country:'DE'},{jobType:'internship'},{language:'EN'},
  {remote:true},{limit:1},{url:'https://www.gulp.de/gulp2/rest/internal/projects/jobs/search'}]){
  const p=capture();await gulp('gulp_inventory',args,p);assert.equal(p.calls.length,0);
 }
});
test('GULP detail accepts only exact native public C identity with no controls or state',async()=>{
 const url='https://www.gulp.de/gulp2/g/jobs/C00000001',p=capture();await gulp('gulp_detail',{url},p);
 assert.deepEqual(p.calls,[['detail','--url',url]]);
 for(const bad of [url+'\n',url+'?language=DE',url+'/bewerbung-ohne-profil',url.replace('www.gulp.de','www.gulp.de.evil.invalid'),url.replace('/C','/%43')]){
  const q=capture();await gulp('gulp_detail',{url:bad},q);assert.equal(q.calls.length,0);
 }
 const q=capture();await gulp('gulp_detail',{url,page:0},q);assert.equal(q.calls.length,0);
});
test('GULP unknown and candidate write operations refuse',async()=>{
 for(const name of ['apply','save','gulp_apply','login']){const p=capture();await gulp(name,{},p);assert.equal(p.calls.length,0);}
});
test('federation exposes only original GULP inventory and detail read routes',()=>{
 assert.ok(ALLOWED.public_de.has('gulp_inventory'));assert.ok(ALLOWED.public_de.has('gulp_detail'));
 assert.ok(!ALLOWED.public_de.has('gulp_apply'));
});
