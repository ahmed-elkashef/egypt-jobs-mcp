// Explicit, bounded engineering proof. Never run as a sourcing census or in CI.
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import {fileURLToPath} from 'node:url';
import {writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const client=new Client({name:'country-source-live-proof',version:'0.4.0'});
const sharedOnly=process.argv.includes('--shared-only');
const env=Object.fromEntries(['PATH','HOME','TMPDIR','LANG','JOB_MARKET_PYTHON','EGYPT_JOBS_PYTHON'].filter(k=>process.env[k]).map(k=>[k,process.env[k]]));
const transport=new StdioClientTransport({command:process.execPath,args:[fileURLToPath(new URL('../server.mjs',import.meta.url))],env,stderr:'pipe'});
transport.stderr?.on('data',()=>{});
const proof={as_of:new Date().toISOString(),purpose:'Bounded live stdio proof; no full-market or interval coverage claim.',
  account_credentials_supplied:false,raw_job_data_published:false,calls:[]};
async function call(name,args){
  let result;
  try{result=await client.callTool({name,arguments:args},undefined,{timeout:65000});}
  catch{proof.calls.push({name,state:'protocol_or_transport_failure'});return null;}
  const native=result.structuredContent??{};
  const data=native.status==='success'&&native.data?native.data:native;
  proof.calls.push({name,arguments:args,isError:result.isError??false,status:data.status??data.kind??'native_result',
    code:data.code??null,sha256:createHash('sha256').update(JSON.stringify(result)).digest('hex'),
    bytes:Buffer.byteLength(JSON.stringify(result)),returned_count:data.count??data.pagination?.returned_count??data.listings?.length??null,
    description_characters:data.job?.description?.length??null,coverage_complete:false});
  return result.isError?null:data;
}
try{
  await client.connect(transport);
  proof.tool_count=(await client.listTools()).tools.length;
  if(!sharedOnly){
  const egypt=await call('eg_read_source_page',{source:'wuzzuf',page:1});
  const first=egypt?.listings?.[0];
  if(first?.url)await call('eg_read_source_detail',{source:'wuzzuf',url:first.url});
  const ba=await call('de_ba_job_suche',{wo:'10115',umkreis:25,angebotsart:1,page:1,size:2,veroeffentlicht_seit:7});
  if(ba){
    await call('de_ba_job_suche',{wo:'10115',umkreis:25,angebotsart:1,page:2,size:2,veroeffentlicht_seit:7});
    if(ba.jobs?.[0]?.hashId)await call('de_ba_job_details',{hashId:ba.jobs[0].hashId});
  }
  await call('de_ba_job_suche',{wo:'10115',umkreis:25,angebotsart:34,page:1,size:2,veroeffentlicht_seit:7});
  await call('de_stepstone_get_capabilities',{});
  await call('de_public_interamt_read',{operation:'agency_list'});
  }
  const shared=await call('shared_get_public_inventory',{source:'arbeitnow',page:1});
  if(shared?.snapshot_id&&shared.jobs?.[0]?.id)await call('shared_get_public_job_from_snapshot',{snapshot_id:shared.snapshot_id,source_id:shared.jobs[0].id,record_index:shared.jobs[0].record_index});
}finally{await client.close();}
// Arguments contain only public diagnostic geography/IDs, never credential data.
await writeFile(new URL(sharedOnly?'../docs/shared-live-proof.json':'../docs/live-proof.json',import.meta.url),JSON.stringify(proof,null,2)+'\n');
console.log(JSON.stringify({tool_count:proof.tool_count,calls:proof.calls.map(({name,isError,status,returned_count,description_characters})=>({name,isError,status,returned_count,description_characters}))}));
