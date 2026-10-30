import {fileURLToPath} from 'node:url';
import {runNativeReader} from './native-reader.mjs';

const script=fileURLToPath(new URL('../dvinci/reader.py',import.meta.url));
const annotations={readOnlyHint:true,destructiveHint:false,openWorldHint:true};
const portalUrl={type:'string',maxLength:2048,description:'Independently identified official employer HTTPS <tenant>.dvinci-hr.com origin, optionally /portal/<name>, or an explicitly verified custom origin in capabilities. No account, job or application URL.'};
const exactId={type:'string',minLength:1,maxLength:16,pattern:'^[1-9][0-9]{0,15}$',description:'Exact native publication ID returned by inventory; distinct from jobOpening.id.'};
export const dvinciTools=[
  {name:'dvinci_capabilities',description:'Offline original anonymous d.vinci publication contracts, permitted portal seeds and limitations. Separate from protected account REST and application APIs. No network.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{...annotations,openWorldHint:false}},
  {name:'dvinci_inventory',description:'Read every current regular-publication row from one independently verified employer portal through its documented public list. Compact metadata by default; include_body additionally preserves all full rendered/raw/company body variants. No role, keyword, geography, target-group or language filtering. No inferred original dates or person fit; one portal is not country/weekly coverage.',inputSchema:{type:'object',properties:{portal_url:portalUrl,include_body:{type:'boolean',default:false}},required:['portal_url'],additionalProperties:false},annotations},
  {name:'dvinci_detail',description:'Read the exact native publication ID through documented singular public GET /jobPublication/show/{id}.json. Preserve full rendered ad sections, raw variants, all company description fields and native dates/labels. Never follow application URLs, call protected account REST or infer person fit.',inputSchema:{type:'object',properties:{portal_url:portalUrl,publication_id:exactId},required:['portal_url','publication_id'],additionalProperties:false},annotations},
];
const limited=error=>({status:'source_limited',source:'dvinci',returned_count:null,source_result_count:null,error,coverage_complete:false,reviewed_by_model:false});
export function runDvinci(argv,options={}) {return runNativeReader(script,argv,{...options,source:'dvinci',countField:'returned_count',timeoutMs:40000});}
export async function dvinci(name,args={}, {run=runDvinci}={}) {
  if(!args||typeof args!=='object'||Array.isArray(args))return limited('invalid_read_arguments');
  const keys=name==='dvinci_capabilities'?[]:name==='dvinci_inventory'?['portal_url','include_body']:name==='dvinci_detail'?['portal_url','publication_id']:null;
  if(!keys||Object.keys(args).some(k=>!keys.includes(k)))return limited('invalid_read_arguments');
  if(name==='dvinci_capabilities')return run(['--capabilities']);
  if(typeof args.portal_url!=='string'||!args.portal_url.length||args.portal_url.length>2048)return limited('invalid_verified_publication_portal');
  const argv=['--portal-url',args.portal_url];
  if(name==='dvinci_inventory'){
    if(args.include_body!==undefined&&typeof args.include_body!=='boolean')return limited('invalid_read_arguments');
    if(args.include_body===true)argv.push('--include-body');
  }else{
    if(typeof args.publication_id!=='string'||!new RegExp(exactId.pattern).test(args.publication_id)||!Number.isSafeInteger(Number(args.publication_id)))return limited('invalid_exact_publication_id');
    argv.push('--job-id',args.publication_id);
  }
  return run(argv);
}
