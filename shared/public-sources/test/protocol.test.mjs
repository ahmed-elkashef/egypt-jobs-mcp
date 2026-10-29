import {test} from 'node:test';
import assert from 'node:assert/strict';
import {tools,callTool,matchesNormalizedJob} from '../index.mjs';
test('16 tools retain all legacy names and expose complete capture/detail',async()=>{
  assert.equal(tools.length,16);for(const name of ['search_public_jobs','search_arbeitnow','search_remotive','search_remoteok','search_jobicy','search_himalayas','search_themuse','search_workable','fetch_workable_jobs','fetch_smartrecruiters_jobs','detect_company_ats','fetch_company_ats_jobs','fetch_personio_jobs','fetch_recruitee_jobs','get_public_inventory','get_public_job_from_snapshot'])assert.ok(tools.some(t=>t.name===name));
  const result=await callTool('unknown');assert.equal(result.isError,true);assert.equal(JSON.parse(result.content[0].text).jobs,null);
});

test('remote filter reads values rather than the remote property name',()=>{
 assert.equal(matchesNormalizedJob({remote:false,title:'Office work',location:'Berlin',description:'On site.'},{remote:true}),false);
 assert.equal(matchesNormalizedJob({remote:true,title:'Example'},{remote:true}),true);
 assert.equal(matchesNormalizedJob({remote:false,description:'No remote work is offered.'},{remote:true}),false);
 assert.equal(matchesNormalizedJob({description:'Remote role available'},{remote:true}),true);
});
