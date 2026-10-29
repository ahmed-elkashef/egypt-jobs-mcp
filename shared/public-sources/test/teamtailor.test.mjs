import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {teamtailor,teamtailorTools,runTeamtailor} from '../teamtailor.mjs';

test('three original feed tools expose only explicit origin and exact GUID reads',()=>{
 assert.equal(teamtailorTools.length,3);
 for(const tool of teamtailorTools){assert.equal(tool.annotations.readOnlyHint,true);assert.equal(tool.inputSchema.additionalProperties,false);}
 assert.deepEqual(Object.keys(teamtailorTools[1].inputSchema.properties),['careers_origin']);
});
test('exact origin and GUID survive bridge arguments without local selection or interpolation',async()=>{
 const seen=[];const run=async args=>{seen.push(args);return {status:'ok'};};
 await teamtailor('teamtailor_inventory',{careers_origin:'https://example.teamtailor.com'},{run});
 await teamtailor('teamtailor_detail',{careers_origin:'https://example.teamtailor.com',job_id:'00000000-0000-4000-8000-000000000001'},{run});
 assert.deepEqual(seen,[['--careers-origin','https://example.teamtailor.com'],['--careers-origin','https://example.teamtailor.com','--job-id','00000000-0000-4000-8000-000000000001']]);
});
test('narrowing, credentials, arbitrary operations and malformed inputs never invoke a reader',async()=>{
 const run=()=>{throw Error('must not invoke');};
 for(const args of [{careers_origin:'x',query:'PR'},{careers_origin:'x',token:'secret'},{careers_origin:'x',offset:20},[],null]){
  const result=await teamtailor('teamtailor_inventory',args,{run});assert.equal(result.status,'source_limited');assert.equal(result.returned_count,null);
 }
 assert.equal((await teamtailor('teamtailor_detail',{careers_origin:'x',job_id:'/applications/new'},{run})).status,'source_limited');
 assert.equal((await teamtailor('teamtailor_capabilities',{careers_origin:'x'},{run})).status,'source_limited');
});
function processFixture(body,inspect=()=>{}){
 return (_cmd,_args,options)=>{
  inspect(options);const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>true;
  queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(body));child.emit('close',0);});return child;
 };
}
test('shared bounded reader preserves full feed bodies and isolates backend credentials',async()=>{
 const data={source:'teamtailor',status:'ok',returned_count:1,listings:[{description:'Full native body. '.repeat(10000)}]};
 const result=await runTeamtailor([],{env:{PATH:'/usr/bin',TEAMTAILOR_API_KEY:'never',THEMUSE_API_KEY:'not-this-source'},spawnProcess:processFixture(JSON.stringify(data),options=>{assert.deepEqual(options.env,{PATH:'/usr/bin'});assert.equal(options.shell,false);})});assert.deepEqual(result,data);
});
test('wrong-source and malformed IPC results have null counts rather than empty jobs',async()=>{
 for(const body of ['broken','[]',JSON.stringify({status:'ok',source:'workday',count:0})]){
  const result=await runTeamtailor([],{spawnProcess:processFixture(body)});assert.equal(result.status,'source_limited');assert.equal(result.returned_count,null);assert.ok(!('listings'in result));
 }
});
