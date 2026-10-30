import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {dvinci,dvinciTools,runDvinci} from '../dvinci.mjs';

test('three original public publication tools expose only explicit portal and exact ID reads',()=>{
 assert.equal(dvinciTools.length,3);
 for(const tool of dvinciTools){assert.equal(tool.annotations.readOnlyHint,true);assert.equal(tool.inputSchema.additionalProperties,false);}
 assert.deepEqual(Object.keys(dvinciTools[1].inputSchema.properties),['portal_url','include_body']);
});
test('metadata full-array and exact detail arguments preserve caller scope without interpolation',async()=>{
 const seen=[];const run=async args=>{seen.push(args);return {status:'ok'};};
 await dvinci('dvinci_inventory',{portal_url:'https://example.dvinci-hr.com/portal/German'},{run});
 await dvinci('dvinci_inventory',{portal_url:'https://example.dvinci-hr.com',include_body:true},{run});
 await dvinci('dvinci_detail',{portal_url:'https://example.dvinci-hr.com',publication_id:'123'},{run});
 assert.deepEqual(seen,[['--portal-url','https://example.dvinci-hr.com/portal/German'],['--portal-url','https://example.dvinci-hr.com','--include-body'],['--portal-url','https://example.dvinci-hr.com','--job-id','123']]);
});
test('narrowing credentials arbitrary operations and malformed publication arguments refuse before reader',async()=>{
 const run=()=>{throw Error('must not invoke');};
 for(const args of [{portal_url:'x',query:'PR'},{portal_url:'x',token:'secret'},{portal_url:'x',offset:20},{portal_url:'x',include_body:'yes'},[],null]){
  const result=await dvinci('dvinci_inventory',args,{run});assert.equal(result.status,'source_limited');assert.equal(result.returned_count,null);
 }
 for(const publication_id of ['01','0','../10','10?apply=1','9007199254740992',10,true])assert.equal((await dvinci('dvinci_detail',{portal_url:'x',publication_id},{run})).status,'source_limited');
 assert.equal((await dvinci('dvinci_capabilities',{portal_url:'x'},{run})).status,'source_limited');
 assert.equal((await dvinci('apply',{portal_url:'x'},{run})).status,'source_limited');
});
function processFixture(body,inspect=()=>{}){
 return (_cmd,_args,options)=>{
  inspect(options);const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>true;
  queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(body));child.emit('close',0);});return child;
 };
}
test('bounded native bridge preserves long full publications and does not pass account credentials',async()=>{
 const data={source:'dvinci',status:'ok',returned_count:1,listings:[{description:'Full rendered publication. '.repeat(10000)}]};
 const result=await runDvinci([],{env:{PATH:'/usr/bin',DVINCI_API_KEY:'never',THEMUSE_API_KEY:'not-this-source'},spawnProcess:processFixture(JSON.stringify(data),options=>{assert.deepEqual(options.env,{PATH:'/usr/bin'});assert.equal(options.shell,false);})});assert.deepEqual(result,data);
});
test('wrong-source and malformed IPC retain null counts rather than empty publications',async()=>{
 for(const body of ['broken','[]',JSON.stringify({status:'ok',source:'teamtailor',count:0})]){
  const result=await runDvinci([],{spawnProcess:processFixture(body)});assert.equal(result.status,'source_limited');assert.equal(result.returned_count,null);assert.ok(!('listings'in result));
 }
});
