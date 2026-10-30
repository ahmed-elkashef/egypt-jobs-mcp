import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {onlyfy,onlyfyTools,runOnlyfy} from '../onlyfy.mjs';

test('original onlyfy tools expose explicit native page and full-ad reads only',()=>{
 assert.equal(onlyfyTools.length,3);
 for(const tool of onlyfyTools){assert.equal(tool.annotations.readOnlyHint,true);assert.equal(tool.inputSchema.additionalProperties,false);}
 assert.deepEqual(Object.keys(onlyfyTools[1].inputSchema.properties),['board_url','page','first_page_total']);
});
test('native page continuation and exact job URI survive bridge arguments without local filtering',async()=>{
 const seen=[];const run=async args=>{seen.push(args);return {status:'ok'};};
 await onlyfy('onlyfy_inventory',{board_url:'https://example.onlyfy.jobs/en',page:2,first_page_total:69},{run});
 await onlyfy('onlyfy_detail',{job_url:'https://example.onlyfy.jobs/en/job/nativehandle001?career_page_search=page%3D2'},{run});
 assert.deepEqual(seen,[['--board-url','https://example.onlyfy.jobs/en','--page','2','--first-page-total','69'],['--job-url','https://example.onlyfy.jobs/en/job/nativehandle001?career_page_search=page%3D2']]);
});
test('credentials narrowing malformed pagination and arbitrary operations never invoke reader',async()=>{
 const run=()=>{throw Error('must not invoke');};
 for(const args of [{board_url:'x',query:'PR'},{board_url:'x',token:'secret'},{board_url:'x',page:0},{board_url:'x',page:true},{board_url:'x',first_page_total:-1},{board_url:'x',first_page_total:'69'},[],null]){
  const result=await onlyfy('onlyfy_inventory',args,{run});assert.equal(result.status,'source_limited');assert.equal(result.returned_count,null);
 }
 assert.equal((await onlyfy('onlyfy_capabilities',{board_url:'x'},{run})).status,'source_limited');
 assert.equal((await onlyfy('apply',{job_url:'x'},{run})).status,'source_limited');
});
function processFixture(body,inspect=()=>{}){
 return (_cmd,_args,options)=>{
  inspect(options);const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>true;
  queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(body));child.emit('close',0);});return child;
 };
}
test('native bridge preserves complete primary body and export variants without account credentials',async()=>{
 const data={source:'onlyfy',status:'ok',description:'Complete native body. '.repeat(10000),native_body_variants:[{text:'Full export variant'}]};
 const result=await runOnlyfy([],{env:{PATH:'/usr/bin',ONLYFY_API_KEY:'never',THEMUSE_API_KEY:'not-this-source'},spawnProcess:processFixture(JSON.stringify(data),options=>{assert.deepEqual(options.env,{PATH:'/usr/bin'});assert.equal(options.shell,false);})});assert.deepEqual(result,data);
});
test('malformed or wrong-source IPC retains null counts instead of fabricated empty jobs',async()=>{
 for(const body of ['broken','[]',JSON.stringify({status:'ok',source:'dvinci',returned_count:0})]){
  const result=await runOnlyfy([],{spawnProcess:processFixture(body)});assert.equal(result.status,'source_limited');assert.equal(result.returned_count,null);assert.ok(!('listings'in result));
 }
});
