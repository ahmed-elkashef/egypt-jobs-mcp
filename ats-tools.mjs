import { z } from 'zod';

const annotations = {readOnlyHint:true,destructiveHint:false,openWorldHint:true};
const source = z.enum(['greenhouse','lever','ashby']);
const board = z.string().min(1).max(100).regex(/^[A-Za-z0-9][A-Za-z0-9._-]*$/);
const region = z.enum(['global','eu']).default('global');

function limitation(error) {
  const data={status:'source_limited',error,coverage_complete:false,reviewed_by_model:false};
  return {content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data,isError:true};
}

export function registerAtsSources(server, invoke) {
  server.registerTool('ats_source_capabilities',{
    description:'Offline official Greenhouse, Lever and Ashby board contracts. Employer boards must be explicitly identified from a source census or declared employer directory; these readers are not an Egypt or global employer universe.',
    inputSchema:{},annotations
  },async ()=>invoke(['--capabilities'],undefined,'egypt_job_sources.ats'));

  server.registerTool('read_employer_board',{
    description:'Read a public board identified by its exact official employer board token. Preserves stable IDs, complete returned descriptions, native date/location/model/compensation fields and honest pagination. No keyword, role, skills, salary or candidate filter. Greenhouse/Ashby expose whole-board snapshots; Lever uses documented skip/limit pages. Board completeness is distinct from frozen-week or geographic coverage. Failed reads are source_limited, never zero jobs.',
    inputSchema:{source,board,region,skip:z.number().int().min(0).max(1000000).default(0),limit:z.number().int().min(1).max(100).default(100)},annotations
  },async ({source,board,region,skip,limit})=>{
    if(source!=='lever' && (region!=='global' || skip!==0 || limit!==100)) return limitation('Only Lever accepts region/skip/limit; other sources return their official whole-board response.');
    return invoke(['--source',source,'--board',board,...(source==='lever'?['--region',region,'--skip',String(skip),'--limit',String(limit)]:[])],undefined,'egypt_job_sources.ats');
  });

  server.registerTool('read_employer_job_detail',{
    description:'Read one exact public Greenhouse or Lever posting by source board token and source ID, checking returned identity and retaining full native text. Ashby has no documented individual public detail endpoint; use its complete board response. No application form, candidate data or contact.',
    inputSchema:{source:z.enum(['greenhouse','lever']),board,region,job_id:z.string().min(1).max(200).regex(/^[A-Za-z0-9_-]+$/)},annotations
  },async ({source,board,region,job_id})=>{
    if(source!=='lever' && region!=='global') return limitation('Only Lever accepts a regional endpoint.');
    return invoke(['--source',source,'--board',board,'--job-id',job_id,...(source==='lever'?['--region',region]:[])],undefined,'egypt_job_sources.ats');
  });
}
