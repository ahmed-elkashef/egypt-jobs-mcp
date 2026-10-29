import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {workday,workdayTools,runWorkday} from '../workday.mjs';

test('original tools expose three explicit read contracts without account or selection inputs',()=>{
  assert.equal(workdayTools.length,3);
  for(const tool of workdayTools){assert.equal(tool.annotations.readOnlyHint,true);assert.equal(tool.inputSchema.additionalProperties,false);}
  assert.deepEqual(Object.keys(workdayTools[1].inputSchema.properties),['board_url','offset','limit','first_page_total']);
});
test('native pagination and exact paths survive bridge arguments without shell interpolation',async()=>{
  const seen=[];const run=async argv=>{seen.push(argv);return {status:'ok'};};
  await workday('workday_inventory',{board_url:'https://example.wd3.myworkdayjobs.com/External',offset:40,first_page_total:100},{run});
  await workday('workday_detail',{board_url:'https://example.wd3.myworkdayjobs.com/External',external_path:'/job/City/Role_12'},{run});
  assert.deepEqual(seen,[['--board-url','https://example.wd3.myworkdayjobs.com/External','--offset','40','--limit','20','--first-page-total','100'],['--board-url','https://example.wd3.myworkdayjobs.com/External','--external-path','/job/City/Role_12']]);
});
test('unknown narrowing, credential, malformed and oversized pagination inputs never invoke a reader',async()=>{
  const run=()=>{throw Error('must not invoke');};
  for(const args of [{board_url:'x',query:'PR'},{board_url:'x',token:'secret'},{board_url:'x',offset:true},{board_url:'x',limit:21},{board_url:'x',offset:-1},{board_url:'x',offset:20},{board_url:'x',offset:20,first_page_total:20},null,[]]){
    const result=await workday('workday_inventory',args,{run});assert.equal(result.status,'source_limited');assert.equal(result.count,null);assert.ok(!('jobs'in result));
  }
  assert.equal((await workday('workday_capabilities',{offset:0},{run})).status,'source_limited');
});
function processFixture(result,{code=0,envProof}={}){
  return (_command,_argv,options)=>{
    envProof?.(options);
    const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>true;
    queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(result));child.emit('close',code);});return child;
  };
}
test('bridge preserves full source bodies and strips unrelated backend credentials from child environment',async()=>{
  const data={source:'workday',status:'ok',source_description:'full '.repeat(10000),continuation:{offset:20}};
  const result=await runWorkday([],{env:{PATH:'/usr/bin',THEMUSE_API_KEY:'not-for-this-reader',COOKIE:'never'},spawnProcess:processFixture(JSON.stringify(data),{envProof:options=>{assert.deepEqual(options.env,{PATH:'/usr/bin'});assert.equal(options.shell,false);}})});
  assert.deepEqual(result,data);
});
test('bridge failures and malformed responses remain null-count limits',async()=>{
  for(const fixture of [processFixture('broken'),processFixture('{}'),processFixture('[]'),processFixture('secret',{code:1})]){
    const result=await runWorkday([],{spawnProcess:fixture});assert.equal(result.status,'source_limited');assert.equal(result.count,null);assert.ok(!('jobs'in result));
  }
});
test('bridge refuses an over-bound response without returning sliced evidence',async()=>{
  const result=await runWorkday([],{spawnProcess:processFixture('x'.repeat(8*1024*1024+1))});
  assert.equal(result.error,'complete_response_exceeds_bridge_bound');assert.equal(result.count,null);assert.ok(!('source_description'in result));
});
