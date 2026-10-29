import {fileURLToPath} from 'node:url';
import {runNativeReader} from './native-reader.mjs';

const script=fileURLToPath(new URL('../workday/reader.py',import.meta.url));
const annotations={readOnlyHint:true,destructiveHint:false,openWorldHint:true};
const board={type:'string',maxLength:2048,description:'Exact HTTPS *.wdN.myworkdayjobs.com/[locale/]site board URL verified from the official employer careers authority. Never guess a tenant.'};
export const workdayTools=[
  {name:'workday_capabilities',description:'Offline original anonymous Workday public CXS list/detail contracts, exact board seed requirements and limitations. No network.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{...annotations,openWorldHint:false}},
  {name:'workday_inventory',description:'Read one complete native unfiltered Workday employer-board page. Follow the exact returned continuation, including first_page_total: later native totals can be zero with jobs, while out-of-range offsets can reset to page one. First-page count is continuation state, not a fresh later-page total. Preserves scoped external-path IDs and raw source dates. Empty facets/search text fixed; no role/candidate selection. Compare IDs across all pages; no country/employer census. Failed reads have null counts.',inputSchema:{type:'object',properties:{board_url:board,offset:{type:'integer',minimum:0,maximum:1000000,default:0},limit:{type:'integer',minimum:1,maximum:20,default:20},first_page_total:{type:'integer',minimum:0,maximum:100000000,description:'Exact initial native total carried by returned continuation; required for nonzero offset.'}},required:['board_url'],additionalProperties:false},annotations},
  {name:'workday_detail',description:'Read the full native CXS jobDescription for an exact /job/... path returned by the same identified board. Checks returned tenant, site and posting path. Preserves all native description markup/text and qualified dates, without claiming browser-visible or independently reviewed content. No application form, account, candidate, contact or subscription endpoint.',inputSchema:{type:'object',properties:{board_url:board,external_path:{type:'string',maxLength:1800}},required:['board_url','external_path'],additionalProperties:false},annotations},
];

export const limited=error=>({status:'source_limited',source:'workday',count:null,source_result_count:null,error,coverage_complete:false,reviewed_by_model:false});

export function runWorkday(argv,options={}) {return runNativeReader(script,argv,{...options,source:'workday'});}

export async function workday(name,args={}, {run=runWorkday}={}) {
  if(!args||typeof args!=='object'||Array.isArray(args))return limited('invalid_read_arguments');
  const keys=name==='workday_capabilities'?[]:name==='workday_inventory'?['board_url','offset','limit','first_page_total']:name==='workday_detail'?['board_url','external_path']:null;
  if(!keys||Object.keys(args).some(k=>!keys.includes(k)))return limited('invalid_read_arguments');
  if(name==='workday_capabilities')return run(['--capabilities']);
  if(typeof args.board_url!=='string'||args.board_url.length>2048)return limited('invalid_explicit_board_url');
  const argv=['--board-url',args.board_url];
  if(name==='workday_detail') {
    if(typeof args.external_path!=='string'||args.external_path.length>1800)return limited('invalid_native_job_path');
    argv.push('--external-path',args.external_path);
  } else {
    const offset=args.offset??0,limit=args.limit??20;
    if(!Number.isInteger(offset)||offset<0||offset>1000000||!Number.isInteger(limit)||limit<1||limit>20)return limited('invalid_native_pagination');
    if(args.first_page_total!==undefined&&(!Number.isInteger(args.first_page_total)||args.first_page_total<0||args.first_page_total>100000000))return limited('invalid_initial_native_total');
    if(offset>0&&(args.first_page_total===undefined||offset>=args.first_page_total))return limited('valid_initial_native_total_required_for_offset');
    argv.push('--offset',String(offset),'--limit',String(limit));
    if(args.first_page_total!==undefined)argv.push('--first-page-total',String(args.first_page_total));
  }
  return run(argv);
}
