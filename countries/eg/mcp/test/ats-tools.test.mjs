import test from 'node:test';
import assert from 'node:assert/strict';
import { registerAtsSources } from '../ats-tools.mjs';

test('ATS registration enforces exact board and provider pagination/detail contracts',async ()=>{
  const registered=new Map(); const calls=[];
  registerAtsSources({registerTool:(name,config,run)=>registered.set(name,{config,run})},async (...args)=>{calls.push(args);return {invocation:args};});
  assert.equal(registered.size,3);
  assert.ok([...registered.values()].every(v=>v.config.annotations.readOnlyHint===true));
  await registered.get('ats_source_capabilities').run({});
  assert.deepEqual(calls.pop(),[['--capabilities'],undefined,'egypt_job_sources.ats']);
  await registered.get('read_employer_board').run({source:'lever',board:'observed-board',region:'eu',skip:100,limit:100});
  assert.deepEqual(calls.pop(),[['--source','lever','--board','observed-board','--region','eu','--skip','100','--limit','100'],undefined,'egypt_job_sources.ats']);
  for(const args of [{source:'ashby',region:'eu',skip:0,limit:100},{source:'greenhouse',region:'global',skip:1,limit:100}]) {
    const result=await registered.get('read_employer_board').run({...args,board:'observed-board'});
    assert.equal(result.isError,true);assert.equal(result.structuredContent.status,'source_limited');
    assert.ok(!('listings'in result.structuredContent));
  }
  assert.equal(calls.length,0);
  const tool=registered.get('read_employer_board').config.inputSchema;
  for(const invalid of ['../secret','https://host','board?query','board/name']) assert.equal(tool.board.safeParse(invalid).success,false);
  assert.deepEqual(registered.get('read_employer_job_detail').config.inputSchema.source.options,['greenhouse','lever']);
  await registered.get('read_employer_job_detail').run({source:'greenhouse',board:'observed-board',region:'global',job_id:'123'});
  assert.deepEqual(calls.pop(),[['--source','greenhouse','--board','observed-board','--job-id','123'],undefined,'egypt_job_sources.ats']);
});

test('Lever commitments use exact repeated parameters and reject malformed or cross-source filters',async ()=>{
  const registered=new Map(); const calls=[];
  registerAtsSources({registerTool:(name,config,run)=>registered.set(name,{config,run})},async (...args)=>{calls.push(args);return {invocation:args};});
  const tool=registered.get('read_employer_board');
  const labels=['Observed part time & remote','التزام تجريبي'];
  assert.deepEqual(tool.config.inputSchema.commitments.parse(labels),labels);
  for(const invalid of [[],[''],[' '],[' leading'],['line\nbreak'],['same','same'],[true],['x'.repeat(201)],Array.from({length:21},(_,i)=>String(i))]) {
    assert.equal(tool.config.inputSchema.commitments.safeParse(invalid).success,false);
    const result=await tool.run({source:'lever',board:'observed-board',region:'global',skip:9,limit:50,commitments:invalid});
    assert.equal(result.isError,true);
  }
  for(const source of ['greenhouse','ashby']) {
    const result=await tool.run({source,board:'observed-board',region:'global',skip:0,limit:100,commitments:labels});
    assert.equal(result.isError,true); assert.ok(!('listings' in result.structuredContent));
  }
  assert.equal(calls.length,0);
  await tool.run({source:'lever',board:'observed-board',region:'global',skip:9,limit:50,commitments:labels});
  assert.deepEqual(calls.pop(),[['--source','lever','--board','observed-board','--region','global','--skip','9','--limit','50','--commitment',labels[0],'--commitment',labels[1]],undefined,'egypt_job_sources.ats']);
  assert.match(tool.config.description,/observed in this employer board taxonomy/);
});
