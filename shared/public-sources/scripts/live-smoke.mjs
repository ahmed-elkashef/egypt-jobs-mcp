import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
const entry=fileURLToPath(new URL('../index.mjs',import.meta.url));
const client=new Client({name:'public-source-verification',version:'1.0'});
const transport=new StdioClientTransport({command:process.execPath,args:[entry],stderr:'pipe'});
const result={checked_at:new Date().toISOString(),tool_count:0,probes:[]};
const parse=r=>JSON.parse(r.content.find(x=>x.type==='text').text);
try {
  await client.connect(transport);result.tool_count=(await client.listTools()).tools.length;
  for(const args of [{source:'arbeitnow',page:1},{source:'arbeitnow',page:2},{source:'remotive'},{source:'remoteok'},{source:'himalayas',country:'Germany',page:1},{source:'personio',subdomain:'dosb'},{source:'themuse',page:0,location:'Germany'}]) {
    const response=await client.callTool({name:'get_public_inventory',arguments:args},undefined,{timeout:30000});const value=parse(response);
    if(response.isError) {result.probes.push({source:args.source,page:args.page??null,status:'source_limited',error:value.error});continue;}
    const d=value.data;let proof=null;
    if(d.jobs.length){const longest=d.jobs.reduce((a,b)=>(a.description_characters>b.description_characters?a:b));const full=parse(await client.callTool({name:'get_public_job_from_snapshot',arguments:{snapshot_id:d.snapshot_id,source_id:longest.id,record_index:longest.record_index}},undefined,{timeout:10000})).data;
      proof={description_characters:full.job.description.length,html_characters:full.job.description_html.length,sha256:createHash('sha256').update(full.job.description_html).digest('hex'),publication_precision:full.job.publication.precision};}
    result.probes.push({source:args.source,page:args.page??null,status:'success',raw_count:d.raw_count,count:d.count,quarantine_count:d.quarantine.length,next:d.pagination.next,provider_total:d.pagination.total,detail:proof});
  }
  console.log(JSON.stringify(result,null,2));
} finally {await client.close();}
