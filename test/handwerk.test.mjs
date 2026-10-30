import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {germanDiscovery, runDiscovery} from '../countries/de/public-services/discovery.mjs';
import {ALLOWED} from '../lib/federation.mjs';

const use = {personal_noncommercial_use:true};
const scope = {...use, scope:'internships', postal_code:'12345'};
function capture() {
  const calls=[];
  return {calls,run:async argv=>{calls.push(argv);return {status:'ok'};}};
}

test('native Handwerk first search preserves explicit model and objective geo only', async()=>{
  const p=capture();
  await germanDiscovery('handwerk_inventory',scope,p);
  assert.deepEqual(p.calls,[['hand_inventory','--scope','internships','--postal-code','12345',
    '--radius-km','25','--page','1','--personal-noncommercial-use']]);
});

test('native Handwerk continuation carries its actual initial page ceiling', async()=>{
  const p=capture();
  await germanDiscovery('handwerk_inventory',{...scope,page:2,first_native_pages:7,radius_km:100},p);
  assert.deepEqual(p.calls,[['hand_inventory','--scope','internships','--postal-code','12345',
    '--radius-km','100','--page','2','--first-native-pages','7','--personal-noncommercial-use']]);
});

test('missing contradictory or forged continuation ceiling refuses before spawn', async()=>{
  for(const args of [{...scope,page:2},{...scope,page:2,first_native_pages:true},
    {...scope,page:2,first_native_pages:1},{...scope,first_native_pages:3}]) {
    const p=capture();
    const r=await germanDiscovery('handwerk_inventory',args,p);
    assert.equal(p.calls.length,0);
    assert.equal(r.status,'source_limited');
    assert.equal(r.returned_count,null);
  }
});

test('Handwerk does not expose firm directories WS or career-query acquisition', async()=>{
  for(const args of [{...scope,scope:'working_student'},{...scope,scope:'atlas'},
    {...scope,query:'PR'},{...scope,employer:'Example'},{...scope,url:'https://example.invalid'}]) {
    const p=capture();
    await germanDiscovery('handwerk_inventory',args,p);
    assert.equal(p.calls.length,0);
  }
});

test('Handwerk geographic bounds are typed without postcode or radius coercion', async()=>{
  for(const args of [{...scope,postal_code:12345},{...scope,postal_code:'1234'},
    {...scope,radius_km:'25'},{...scope,radius_km:null},{...scope,radius_km:0},{...scope,radius_km:1001}]) {
    const p=capture();
    await germanDiscovery('handwerk_inventory',args,p);
    assert.equal(p.calls.length,0);
  }
});

test('explicit personal acknowledgement precedes every Handwerk operation', async()=>{
  for(const name of ['handwerk_inventory','handwerk_detail']) {
    const p=capture();
    await germanDiscovery(name,{...scope,personal_noncommercial_use:false},p);
    assert.equal(p.calls.length,0);
  }
});

test('independent standalone chamber primary URL remains one exact process argument', async()=>{
  const p=capture();
  const url='https://www.hwk-wiesbaden.de/44,0,jobboardofferdetail.html?id=1';
  await germanDiscovery('handwerk_detail',{...use,url},p);
  assert.deepEqual(p.calls,[['hand_detail','--url',url,'--personal-noncommercial-use']]);
  for(const name of ['handwerk_inventory','handwerk_detail'])assert.ok(ALLOWED.public_de.has(name));
  assert.ok(!ALLOWED.public_de.has('handwerk_apply'));
});

test('native bridge expects Handwerk provider identity for both original readers', async()=>{
  for(const operation of ['hand_inventory','hand_detail']) {
    const spawnProcess=()=>{
      const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>{};
      queueMicrotask(()=>{
        child.stdout.emit('data',Buffer.from(JSON.stringify({status:'ok',source:'handwerk',returned_count:1})));
        child.emit('close',0);
      });return child;
    };
    const r=await runDiscovery([operation],{spawnProcess,env:{}});
    assert.equal(r.status,'ok');assert.equal(r.source,'handwerk');
  }
});
