#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const python = process.env.EGYPT_JOBS_PYTHON || 'python3';
const execute = promisify(execFile);
const server = new McpServer({name:'egypt-jobs-mcp',version:'0.1.0'});
const source = z.enum(['wuzzuf','forasna','arabjobs','bayt','himalayas','jobicy','mostaql']);
const annotations = {readOnlyHint:true,destructiveHint:false,openWorldHint:true};
async function invoke(args, input, module='egypt_job_sources.sources') {
  const execution=execute(python,['-m',module,...args],{timeout:55000,maxBuffer:12*1024*1024});
  // The capture is JSON data on stdin, never shell text, a URL fetch or JS execution.
  execution.child.stdin.end(input === undefined ? undefined : JSON.stringify(input));
  let data;
  try {
    const {stdout} = await execution;
    data=JSON.parse(stdout);
  } catch (error) {
    data={status:'source_limited',coverage_complete:false,reviewed_by_model:false,
      error:error.killed?'Source process timed out; acquisition remains incomplete.':`Source process failed (${error.code || error.name}); acquisition remains incomplete.`};
  }
  return {content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data,isError:data.status==='source_limited'};
}
server.registerTool('read_source_page',{
  description:'Read one public source page. WUZZUF uses its verified public JSON:API search and full-description hydration, blank query with Egypt and optional native work model. Forasna HTTP is source_limited; use operator-authorized public DOM handoff. ArabJobs/Bayt Egypt, Himalayas EG including worldwide, Jobicy global seven-day cursor feed, Mostaql client projects. No keyword/role/seniority filters. Acquisition is not review or coverage completion.',
  inputSchema:{source,page:z.number().int().min(1).max(10000).default(1),cursor:z.string().max(4096).optional(),work_model:z.enum(['full_time','part_time','freelance','freelance_project','internship','shift_based','volunteering']).optional(),continuation_url:z.string().url().optional()},annotations
},async ({source,page,cursor,work_model,continuation_url})=>invoke([source,'--page',String(page),...(cursor?['--cursor',cursor]:[]),...(work_model?['--work-model',work_model]:[]),...(continuation_url?['--continuation-url',continuation_url]:[])]));
server.registerTool('read_source_detail',{
  description:'Read a canonical WUZZUF, Forasna, ArabJobs, Bayt Egypt job or Mostaql project. Blocked HTTP is source_limited. Full text is acquisition evidence, not a model review or fit decision. No submission or contact.',
  inputSchema:{source:z.enum(['wuzzuf','forasna','arabjobs','bayt','mostaql']),url:z.string().url()},annotations
},async ({source,url})=>invoke([source,'--detail-url',url]));
server.registerTool('parse_rendered_board_page',{
  description:'Parse selected public DOM acquired in the operator-authorized browser using browser-extract.mjs. Does not operate the browser or fetch a URL. Preserves cards, observed next link, stable IDs and full description plus requirements for details. Operator-supplied provenance; acquisition is not review. No cookies/session state.',
  inputSchema:{source:z.enum(['wuzzuf','forasna','arabjobs']),capture:z.object({url:z.string().url(),kind:z.enum(['page','detail']),captured_at:z.string().datetime({offset:true}),html:z.string().max(8000000)}).strict()},annotations
},async ({source,capture})=>invoke([source,'--browser-capture-stdin'],capture));
server.registerTool('read_saved_board_capture',{
  description:'Read an immutable public DOM checkpoint saved by the loopback-only CUA handoff by egypt-job-capture. Accepts only a SHA-256 receipt, never arbitrary files. Rehashes and reparses the original. Operator evidence is not individual review or completed market coverage.',
  inputSchema:{receipt_id:z.string().regex(/^[a-f0-9]{64}$/)},annotations
},async ({receipt_id})=>invoke(['show',receipt_id],undefined,'egypt_job_sources.capture'));
server.registerTool('jobicy_location_taxonomy',{
  description:'Read current official Jobicy location slugs. Egypt was absent on 2026-10-09; never invent geo=egypt.',inputSchema:{},annotations
},async ()=>invoke(['jobicy','--taxonomy']));
server.registerTool('wuzzuf_work_model_taxonomy',{
  description:'Read every native WUZZUF work-model facet for the blank-query Egypt inventory. Verify counts and unknown/mixed partitions before a full-supply run; native type labels do not establish compatible hours or fit. Undocumented public frontend contract, no authentication.',inputSchema:{},annotations
},async ()=>invoke(['wuzzuf','--taxonomy']));
await server.connect(new StdioServerTransport());
