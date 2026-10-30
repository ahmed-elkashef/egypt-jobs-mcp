import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {ror, rorTools, runRor} from '../ror.mjs';

test('ROR release resolver and immutable metadata have narrow read-only schemas', async () => {
  assert.deepEqual(rorTools.map(t => t.name), ['ror_release', 'ror_directory']);
  for (const tool of rorTools) {
    assert.equal(tool.annotations.readOnlyHint, true);
    assert.equal(tool.inputSchema.additionalProperties, false);
  }
  let invoked;
  const run = async argv => {invoked = argv; return {status: 'ok'};};
  await ror('ror_release', {}, {run});
  assert.deepEqual(invoked, ['release']);
  await ror('ror_release', {record_id: '23500708'}, {run});
  assert.deepEqual(invoked, ['release', '--record-id', '23500708']);
});

test('ROR exact country snapshot continuation reaches only fixed original reader', async () => {
  let invoked;
  await ror('ror_directory', {record_id: '23500708', country: 'EG', offset: 200, limit: 200, snapshot_sha256: 'a'.repeat(64)}, {
    run: async argv => {invoked = argv; return {status: 'ok'};}
  });
  assert.deepEqual(invoked, ['directory','--record-id','23500708','--country','EG','--offset','200','--limit','200','--snapshot-sha256','a'.repeat(64)]);
});

test('ROR explicit null offset cannot silently reset an immutable country segment', async () => {
  const result = await ror('ror_directory', {record_id:'23500708',country:'DE',offset:null}, {
    run:()=>assert.fail('null offset must refuse before reader or cache access')
  });
  assert.equal(result.status,'source_limited');assert.equal(result.organization_count,null);
  assert.equal(result.coverage_complete,false);
});

test('ROR explicit null limit cannot silently become the default country segment', async () => {
  const result = await ror('ror_directory', {record_id:'23500708',country:'EG',limit:null}, {
    run:()=>assert.fail('null limit must refuse before reader or cache access')
  });
  assert.equal(result.status,'source_limited');assert.equal(result.organization_count,null);
  assert.equal(result.coverage_complete,false);
});

test('ROR rejects role queries URLs concept aliases coercions and unbound offsets without executing', async () => {
  const run = () => {assert.fail('invalid input must not spawn reader');};
  for (const [name,args] of [
    ['ror_release',{url:'https://zenodo.org/api/records/6347574'}],
    ['ror_release',{record_id:'6347574'}], ['ror_release',{record_id:'23500708;echo'}],
    ['ror_directory',{record_id:'23500708',country:'DE',query:'marketing'}],
    ['ror_directory',{record_id:'23500708',country:'US'}],
    ['ror_directory',{record_id:'23500708',country:'DE',offset:1}],
    ['ror_directory',{record_id:'23500708',country:'DE',offset:'0'}],
    ['ror_directory',{record_id:'23500708',country:'DE',limit:501}],
    ['ror_directory',{record_id:'23500708',country:'DE',snapshot_sha256:'../x'}],
    ['ror_release',null], ['unknown',{}]
  ]) {
    const result = await ror(name,args,{run});
    assert.equal(result.status,'source_limited'); assert.equal(result.organization_count,null);
    assert.equal(result.coverage_complete,false);
  }
});

test('ROR reader receives only runtime and nonsecret capture environment, no server credentials', async () => {
  let observed;
  const spawnProcess = (command,argv,options) => {
    observed={command,argv,options};
    const child=new EventEmitter(); child.stdout=new EventEmitter(); child.kill=()=>{};
    queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(JSON.stringify({status:'ok',source:'ror',kind:'organisation_directory',organization_count:0,coverage_complete:false})));child.emit('close',0);});
    return child;
  };
  await runRor(['directory','--record-id','23500708','--country','DE'], {spawnProcess,env:{PATH:'/bin',EGYPT_JOBS_PYTHON:'/runtime/python',JOB_MARKET_CAPTURE_DIR:'/private/source-cache',THEMUSE_API_KEY:'not-exported',UPWORK_ACCESS_TOKEN:'not-exported'}});
  assert.equal(observed.command,'/runtime/python');
  assert.equal(observed.options.env.JOB_MARKET_CAPTURE_DIR,'/private/source-cache');
  assert.equal(observed.options.env.THEMUSE_API_KEY,undefined);
  assert.equal(observed.options.env.UPWORK_ACCESS_TOKEN,undefined);
  assert.equal(observed.options.shell,false);
  assert.ok(observed.argv[0].endsWith('/shared/ror/reader.py'));
});

test('ROR typed exit2 limit preserves exact source evidence and unknown count', async () => {
  const payload={status:'source_limited',source:'ror',organization_count:null,coverage_complete:false,reviewed_by_model:false,error:'robots_denies_exact_ROR_public_route'};
  const spawnProcess=()=>{
    const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>{};
    queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(JSON.stringify(payload)));child.emit('close',2);});return child;
  };
  assert.deepEqual(await runRor(['release'],{spawnProcess}),payload);
});

test('ROR failed reader cannot promote completeness or reviewed directory data', async () => {
  const spawnProcess=()=>{
    const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>{};
    queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(JSON.stringify({status:'ok',source:'ror',organization_count:3,coverage_complete:true,reviewed_by_model:true})));child.emit('close',2);});return child;
  };
  const result=await runRor(['release'],{spawnProcess});
  assert.equal(result.status,'source_limited');assert.equal(result.organization_count,null);
  assert.equal(result.coverage_complete,false);assert.equal(result.reviewed_by_model,false);
});
