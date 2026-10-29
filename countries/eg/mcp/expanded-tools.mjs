import { z } from 'zod';

const annotations = {readOnlyHint:true,destructiveHint:false,openWorldHint:true};
const remote = z.enum(['remotive','remoteok','weworkremotely','workingnomads','himalayas_global']);
const freelance = z.enum(['freelancer','upwork']);

function limitation(error) {
  const data = {status:'source_limited',error,coverage_complete:false,reviewed_by_model:false};
  return {content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data,isError:true};
}

export function registerExpandedSources(server, invoke) {
  server.registerTool('read_public_api_jobs',{
    description:'Read one complete native Arbeitnow or The Muse public API page, preserving every returned description. Arbeitnow starts at page1; The Muse starts at page0. Echo exact returned next_url for continuation. No title, role or keyword filters. The Muse needs registered app credentials in machine-local THEMUSE_API_KEY for production; testing=true is only a bounded anonymous capability test. An API page is not original-date proof or a historical census.',
    inputSchema:{source:z.enum(['arbeitnow','themuse']),page:z.number().int().min(0).max(1000000).optional(),next_url:z.string().url().max(4096).optional(),testing:z.boolean().default(false)},annotations
  },async ({source,page,next_url,testing})=> {
    if (page!==undefined && next_url) return limitation('Choose a page or the exact returned next_url.');
    if (source==='arbeitnow' && page===0) return limitation('Arbeitnow pages begin at one.');
    if (source==='arbeitnow' && testing) return limitation('Anonymous testing mode is only for The Muse.');
    return invoke([source,...(page!==undefined?['--page',String(page)]:[]),...(next_url?['--next-url',next_url]:[]),...(testing?['--testing']:[])],undefined,'egypt_job_sources.public_apis');
  });

  server.registerTool('remote_source_capabilities',{
    description:'Offline source contracts, attribution, date/history limits and pagination for broad worldwide remote feeds. Country access, part-time hours, experience and actual income require individual review.',
    inputSchema:{},annotations
  },async ()=>invoke(['--capabilities'],undefined,'egypt_job_sources.remote'));

  server.registerTool('read_remote_feed',{
    description:'Read an unfiltered public remote feed: Remotive, Remote OK, We Work Remotely RSS, Working Nomads exposed inventory, or Himalayas global cursor page. Keeps all returned descriptions and source terms. No title, keyword, skill or salary filter. Source snapshots, unknown hours and worldwide labels never establish Egypt eligibility or whole-market coverage.',
    inputSchema:{source:remote,cursor:z.string().min(1).max(4096).optional()},annotations
  },async ({source,cursor})=> {
    if (cursor && source!=='himalayas_global') return limitation('Only the verified Himalayas global feed accepts a returned cursor.');
    return invoke([source,...(cursor?['--cursor',cursor]:[])],undefined,'egypt_job_sources.remote');
  });

  server.registerTool('freelance_source_capabilities',{
    description:'Offline contracts for public Freelancer projects and approval-gated Upwork marketplace reads. Reports source access requirements and budget/pagination limits; does not create accounts, obtain tokens or verify payment access.',
    inputSchema:{},annotations
  },async ()=>invoke(['--capabilities'],undefined,'egypt_job_sources.freelance'));

  server.registerTool('read_freelance_projects',{
    description:'Read one client-project page without role/skill filters, including complete returned descriptions and budget terms. Freelancer public active-project GET optionally takes paired aware RFC3339 from_time/to_time: native dates constrain UPDATE activity, not new creation. Retain exact original submission screening and raw pagination; missing/conflicting dates remain undetermined. Hourly commitment is a billing limit, not proven minimum workload. Upwork custom API is separately approval-gated and accepts no time filters. No bid, contact, payment, account extras or arbitrary query.',
    inputSchema:{source:freelance,limit:z.number().int().min(1).max(100).default(20),offset:z.number().int().min(0).max(1000000).default(0),cursor:z.string().min(1).max(4096).optional(),from_time:z.string().datetime({offset:true}).max(128).optional(),to_time:z.string().datetime({offset:true}).max(128).optional()},annotations
  },async ({source,limit,offset,cursor,from_time,to_time})=> {
    if (source==='freelancer' && cursor) return limitation('Freelancer uses verified numeric offsets, not an opaque cursor.');
    if (source==='upwork' && offset!==0) return limitation('Upwork uses exact source-returned cursors, not numeric offsets.');
    if ((from_time || to_time) && source!=='freelancer') return limitation('Time filters are supported only for Freelancer public activity search, not Upwork.');
    if (!!from_time!==!!to_time) return limitation('Supply both aware from_time and to_time for one fixed activity interval.');
    return invoke(['--source',source,'--limit',String(limit),...(source==='freelancer'?['--offset',String(offset)]:[]),...(cursor?['--cursor',cursor]:[]),...(from_time?['--from-time',from_time,'--to-time',to_time]:[])],undefined,'egypt_job_sources.freelance');
  });

  server.registerTool('read_freelance_project_detail',{
    description:'Read one public client-project description by source ID: numeric Freelancer ID or approved Upwork job ID. Source identity and public scope must match. Does not retrieve profiles, bids, files, contracts or private financial records.',
    inputSchema:{source:freelance,project_id:z.string().min(1).max(200).regex(/^[A-Za-z0-9_~=-]+$/)},annotations
  },async ({source,project_id})=>invoke(['--source',source,'--project-id',project_id],undefined,'egypt_job_sources.freelance'));
}
