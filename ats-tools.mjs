import { z } from 'zod';

const annotations = {readOnlyHint:true,destructiveHint:false,openWorldHint:true};
const source = z.enum(['greenhouse','lever','ashby']);
const board = z.string().min(1).max(100).regex(/^[A-Za-z0-9][A-Za-z0-9._-]*$/);
const region = z.enum(['global','eu']).default('global');
const commitment = z.string().min(1).max(200).refine(value=>value===value.trim() && !/\p{C}/u.test(value), 'Use an exact nonempty observed commitment label.');
const commitments = z.array(commitment).min(1).max(20).refine(values=>new Set(values).size===values.length, 'Commitment labels must be distinct.').optional();

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
    description:'Read a public board identified by its exact official employer board token. Preserves stable IDs, complete returned descriptions, native fields and raw pagination. No keyword, role, skills, salary or candidate filter. Lever alone accepts optional commitments: exact labels observed in this employer board taxonomy, repeated as case-sensitive OR parameters. Keep the unfiltered missing/mixed/other-label complement; labels do not prove compatible hours. Greenhouse/Ashby expose whole-board snapshots; Lever uses skip/limit pages. Failed reads are source_limited, never zero jobs.',
    inputSchema:{source,board,region,skip:z.number().int().min(0).max(1000000).default(0),limit:z.number().int().min(1).max(100).default(100),commitments},annotations
  },async ({source,board,region,skip,limit,commitments})=>{
    if(source!=='lever' && (region!=='global' || skip!==0 || limit!==100)) return limitation('Only Lever accepts region/skip/limit; other sources return their official whole-board response.');
    if(commitments!==undefined && source!=='lever') return limitation('Only Lever list reads accept observed commitment filters.');
    if(!registeredCommitments(commitments)) return limitation('Use one to twenty distinct exact observed commitment labels.');
    return invoke(['--source',source,'--board',board,...(source==='lever'?['--region',region,'--skip',String(skip),'--limit',String(limit),...(commitments||[]).flatMap(value=>['--commitment',value])]:[])],undefined,'egypt_job_sources.ats');
  });

  server.registerTool('read_employer_job_detail',{
    description:'Read one exact public Greenhouse or Lever posting by source board token and source ID, checking returned identity and retaining full native text. Ashby has no documented individual public detail endpoint; use its complete board response. No application form, candidate data or contact.',
    inputSchema:{source:z.enum(['greenhouse','lever']),board,region,job_id:z.string().min(1).max(200).regex(/^[A-Za-z0-9_-]+$/)},annotations
  },async ({source,board,region,job_id})=>{
    if(source!=='lever' && region!=='global') return limitation('Only Lever accepts a regional endpoint.');
    return invoke(['--source',source,'--board',board,'--job-id',job_id,...(source==='lever'?['--region',region]:[])],undefined,'egypt_job_sources.ats');
  });
}

function registeredCommitments(value) { return commitments.safeParse(value).success; }
