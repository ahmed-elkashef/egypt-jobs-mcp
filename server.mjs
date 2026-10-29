#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema,ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { Federation,loadRegistry,countrySources,scanPlan,READ_ONLY } from './lib/federation.mjs';

const registry=await loadRegistry();
const federation=await new Federation().initialize();
const server=new Server({name:'job-market-mcp',version:'0.4.1'},{capabilities:{tools:{}}});
const object=(properties={},required=[])=>({type:'object',properties,required,additionalProperties:false});
const country={type:'string',enum:['EG','DE']};
const catalogue=[
  {name:'list_countries',description:'List country packages and current backend readiness. No source network reads.',inputSchema:object()},
  {name:'list_country_sources',description:'List the maintained national and shared source registry, implemented routes and unresolved gaps. This is not proof of every vacancy or employer.',inputSchema:object({country},['country'])},
  {name:'source_capabilities',description:'Inspect one source, its native tools, access limits, evidence dates and implementation state without acquiring jobs.',inputSchema:object({source_id:{type:'string'}},['source_id'])},
  {name:'plan_country_scan',description:'Prepare a source-complete scan plan for an explicit country/geography and offset-aware frozen interval. Makes no source calls and starts no application, monitor or scan.',inputSchema:object({country,geography:{type:'string'},from:{type:'string'},to:{type:'string'}},['country','geography','from','to'])},
].map(t=>({...t,annotations:{...READ_ONLY,openWorldHint:false}}));
const json=data=>({content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data});
server.setRequestHandler(ListToolsRequestSchema,async()=>({tools:[...catalogue,...federation.tools()]}));
server.setRequestHandler(CallToolRequestSchema,async({params})=>{
  const args=params.arguments??{};
  try {
    if(params.name==='list_countries')return json({countries:registry.countries,backend_status:federation.health(),limits:registry.limits});
    if(params.name==='list_country_sources')return json({country:args.country,sources:countrySources(registry,args.country),coverage_complete:false,limits:registry.limits});
    if(params.name==='source_capabilities'){
      const source=registry.sources.find(s=>s.id===args.source_id);
      if(!source)throw new Error('Unknown source ID');
      const names=new Set((source.routes??[]).map(r=>r.public_tool));
      return json({source,tools:federation.tools().filter(t=>names.has(t.name)),backend_status:federation.health(),coverage_complete:false});
    }
    if(params.name==='plan_country_scan')return json(scanPlan(registry,args));
    return federation.call(params.name,args);
  }catch(error){const data={status:'invalid_request',error:error.message,coverage_complete:false};return {...json(data),isError:true};}
});
const transport=new StdioServerTransport(process.stdin,process.stdout,{maxBufferSize:64*1024*1024});
await server.connect(transport);
let closing;
const close=()=>closing??=(async()=>{await federation.close();await server.close();})();
const originalClose=transport.onclose;
transport.onclose=()=>{originalClose?.();void close();};
for(const signal of ['SIGINT','SIGTERM'])process.once(signal,()=>{void close().finally(()=>process.exit(0));});
