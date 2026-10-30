import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {runNativeReader} from '../shared/public-sources/native-reader.mjs';
function reader(payload,code=2){return()=>{const child=new EventEmitter();child.stdout=new EventEmitter();child.kill=()=>{};queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(typeof payload==='string'?payload:JSON.stringify(payload)));child.emit('close',code);});return child;};}
const valid={status:'source_limited',source:'aubi_plus',returned_count:null,coverage_complete:false,reviewed_by_model:false,error:'Native counter moved',evidence:{observed_total:51,first_page_total:52}};
const invoke=(payload,code=2)=>runNativeReader('fixed-reader.py',[],{source:'aubi_plus',countField:'returned_count',spawnProcess:reader(payload,code),env:{}});
test('typed source limit on exit2 retains exact reason and evidence',async()=>{
 assert.deepEqual(await invoke(valid),valid);
});
test('nonzero success or promoting payload cannot become a source result',async()=>{
 for(const patch of [{status:'ok'},{coverage_complete:true},{reviewed_by_model:true},{returned_count:0}]){const result=await invoke({...valid,...patch});assert.equal(result.error,'native_reader_failed');assert.equal(result.returned_count,null);}
});
test('wrong source missing envelope malformed or array failure remains generic',async()=>{
 for(const payload of [{...valid,source:'elsewhere'},{status:'source_limited',source:'aubi_plus'},'not JSON',[valid]]){const result=await invoke(payload);assert.equal(result.error,'native_reader_failed');assert.equal(result.coverage_complete,false);}
});
test('other failure exit codes cannot preserve even typed-looking stdout',async()=>{
 const result=await invoke(valid,1);assert.equal(result.error,'native_reader_failed');assert.equal(result.returned_count,null);
});
