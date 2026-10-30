import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {jobshop,jobshopTools,runJobshop} from '../jobshop.mjs';

test('original jobshop tools expose explicit native page and full-ad reads only',()=>{
 assert.equal(jobshopTools.length,3);
 for(const tool of jobshopTools){assert.equal(tool.annotations.readOnlyHint,true);assert.equal(tool.inputSchema.additionalProperties,false);}
 assert.deepEqual(Object.keys(jobshopTools[1].inputSchema.properties),['career_origin']);
});
test('complete inventory and exact native posting URI survive without local filtering',async()=>{
 const seen=[];const run=async args=>{seen.push(args);return {status:'ok'};};
 await jobshop('jobshop_inventory',{career_origin:'https://www.jobs-fraport.com'},{run});
 await jobshop('jobshop_detail',{job_url:'https://www.jobs-fraport.com/offer-redirect/?offerApiId=MTAwNDY=&showApplicationForm=false'},{run});
 assert.deepEqual(seen,[['--career-origin','https://www.jobs-fraport.com'],['--job-url','https://www.jobs-fraport.com/offer-redirect/?offerApiId=MTAwNDY=&showApplicationForm=false']]);
});
test('qualified Haema origin and acquired canonical URI reach only the fixed native read CLI',async()=>{
 const seen=[];const run=async args=>{seen.push(args);return {status:'ok'};};
 const origin='https://karriere.haema.de',url=origin+'/jobs/synthetic-internship/00000000-0000-4000-8000-000000000001';
 await jobshop('jobshop_inventory',{career_origin:origin},{run});await jobshop('jobshop_detail',{job_url:url},{run});
 assert.deepEqual(seen,[['--career-origin',origin],['--job-url',url]]);
});
test('Haema three-section primary evidence crosses IPC intact with every guard flag unchanged',async()=>{
 const data={source:'jobshop',status:'ok',career_origin:'https://karriere.haema.de',native_primary_cms_section_count:3,
  native_primary_cms_sections:[{ordinal:0,text:'Whole role'},{ordinal:1,text:'Whole promise'},{ordinal:2,text:'Whole company context'}],
  coverage_complete:false,full_posting_reviewed:false,hydration_credentials_exported_or_used:false};
 const result=await runJobshop([],{spawnProcess:processFixture(JSON.stringify(data))});assert.deepEqual(result,data);
});
test('credentials role selection pagination and arbitrary operations never invoke reader',async()=>{
 const run=()=>{throw Error('must not invoke');};
 for(const args of [{career_origin:'x',query:'PR'},{career_origin:'x',token:'secret'},{career_origin:'x',page:1},{career_origin:9},[],null]){
  const result=await jobshop('jobshop_inventory',args,{run});assert.equal(result.status,'source_limited');assert.equal(result.returned_count,null);
 }
 assert.equal((await jobshop('jobshop_capabilities',{career_origin:'x'},{run})).status,'source_limited');
 assert.equal((await jobshop('apply',{job_url:'x'},{run})).status,'source_limited');
});
function processFixture(body,inspect=()=>{}){
 return (_cmd,_args,options)=>{
  inspect(options);const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>true;
  queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(body));child.emit('close',0);});return child;
 };
}
test('native bridge preserves complete primary body and export variants without account credentials',async()=>{
 const data={source:'jobshop',status:'ok',description:'Complete native body. '.repeat(10000),native_cms_sections:[{text:'Full context section'}]};
 const result=await runJobshop([],{env:{PATH:'/usr/bin',ONLYFY_API_KEY:'never',THEMUSE_API_KEY:'not-this-source'},spawnProcess:processFixture(JSON.stringify(data),options=>{assert.deepEqual(options.env,{PATH:'/usr/bin'});assert.equal(options.shell,false);})});assert.deepEqual(result,data);
});
test('malformed or wrong-source IPC retains null counts instead of fabricated empty jobs',async()=>{
 for(const body of ['broken','[]',JSON.stringify({status:'ok',source:'dvinci',returned_count:0})]){
  const result=await runJobshop([],{spawnProcess:processFixture(body)});assert.equal(result.status,'source_limited');assert.equal(result.returned_count,null);assert.ok(!('listings'in result));
 }
});
