import {fileURLToPath} from 'node:url';
import {runNativeReader} from './native-reader.mjs';

const script=fileURLToPath(new URL('../onlyfy/reader.py',import.meta.url));
const annotations={readOnlyHint:true,destructiveHint:false,openWorldHint:true};
const boardUrl={type:'string',maxLength:2048,description:'Exact independently identified HTTPS <tenant>.onlyfy.jobs/en or /de native career board, without query, account or application path.'};
const page={type:'integer',minimum:1,maximum:1000000,default:1};
const firstTotal={type:'integer',minimum:0,maximum:10000000,description:'Actual first-page total; required for native continuation after page1.'};
export const onlyfyTools=[
  {name:'onlyfy_capabilities',description:'Offline original onlyfy.jobs native inventory/full-ad contracts and employer-seed requirements. Distinct from authenticated account REST and legacy published-handle feeds. No network.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{...annotations,openWorldHint:false}},
  {name:'onlyfy_inventory',description:'Read one complete native unfiltered career page. Reconcile every posting handle with advertised range, current page, initial total and actual next-button state. Preserve all native cards and facts; no role, geography, language-of-job, candidate or title selection. One board/page is not a country census or historical week.',inputSchema:{type:'object',properties:{board_url:boardUrl,page,first_page_total:firstTotal},required:['board_url'],additionalProperties:false},annotations},
  {name:'onlyfy_detail',description:'Read one exact returned native job URL and its verified complete public HTML frame. The shell schema summary is never a full description. Keep primary main content, additional export variants, native identifiers/date/remote fields separately. No script, account API, application, print/PDF, contact or subscription request.',inputSchema:{type:'object',properties:{job_url:{type:'string',maxLength:4096,description:'Exact native <tenant>.onlyfy.jobs/en|de/job/<handle> URL from inventory; optional native page-only back-navigation reference.'}},required:['job_url'],additionalProperties:false},annotations},
];
const limited=error=>({status:'source_limited',source:'onlyfy',returned_count:null,source_result_count:null,error,coverage_complete:false,reviewed_by_model:false});
export function runOnlyfy(argv,options={}) {return runNativeReader(script,argv,{...options,source:'onlyfy',countField:'returned_count',timeoutMs:55000});}
export async function onlyfy(name,args={}, {run=runOnlyfy}={}) {
  if(!args||typeof args!=='object'||Array.isArray(args))return limited('invalid_read_arguments');
  const keys=name==='onlyfy_capabilities'?[]:name==='onlyfy_inventory'?['board_url','page','first_page_total']:name==='onlyfy_detail'?['job_url']:null;
  if(!keys||Object.keys(args).some(k=>!keys.includes(k)))return limited('invalid_read_arguments');
  if(name==='onlyfy_capabilities')return run(['--capabilities']);
  if(name==='onlyfy_detail'){
    if(typeof args.job_url!=='string'||!args.job_url.length||args.job_url.length>4096)return limited('invalid_native_onlyfy_job_url');
    return run(['--job-url',args.job_url]);
  }
  if(typeof args.board_url!=='string'||!args.board_url.length||args.board_url.length>2048)return limited('invalid_verified_onlyfy_board');
  const argv=['--board-url',args.board_url];
  if(args.page!==undefined){if(!Number.isInteger(args.page)||args.page<1||args.page>1000000)return limited('invalid_native_page_number');argv.push('--page',String(args.page));}
  if(args.first_page_total!==undefined){if(!Number.isInteger(args.first_page_total)||args.first_page_total<0||args.first_page_total>10000000)return limited('invalid_first_page_total');argv.push('--first-page-total',String(args.first_page_total));}
  return run(argv);
}
