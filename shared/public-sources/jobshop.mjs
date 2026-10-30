import {fileURLToPath} from 'node:url';
import {runNativeReader} from './native-reader.mjs';
const script=fileURLToPath(new URL('../jobshop/reader.py',import.meta.url));
const annotations={readOnlyHint:true,destructiveHint:false,openWorldHint:true};
export const jobshopTools=[
 {name:'jobshop_capabilities',description:'Offline original Jobshop SSR/CMS source contracts and independently verified employer origins; no account/search-key operation.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{...annotations,openWorldHint:false}},
 {name:'jobshop_inventory',description:'Read every unfiltered native SSR posting reference and reconcile native anchors/titles with an independent whole-board count. Never use client placeholders or hydration search keys. One employer is not a historical week or country census.',inputSchema:{type:'object',properties:{career_origin:{type:'string',maxLength:2048,description:'Exact independently verified employer origin from capabilities; no path or filters.'}},required:['career_origin'],additionalProperties:false},annotations},
 {name:'jobshop_detail',description:'Read an exact acquired native posting URI on an independently qualified Fraport or Haema origin. Preserve every complete primary CMS job-data section, separate sanitized full main/context, schema/native clocks and form labels. Legacy/vendor redirects are Fraport-only; cross-employer and application routes refuse. No source scripts, search credentials, accounts, application or contact request.',inputSchema:{type:'object',properties:{job_url:{type:'string',maxLength:4096,description:'Exact acquired canonical UUID, or Fraport-only read-only public offer-redirect URI.'}},required:['job_url'],additionalProperties:false},annotations},
];
const limited=error=>({status:'source_limited',source:'jobshop',returned_count:null,source_result_count:null,error,coverage_complete:false,reviewed_by_model:false});
export function runJobshop(argv,options={}){return runNativeReader(script,argv,{...options,source:'jobshop',countField:'returned_count',timeoutMs:55000});}
export async function jobshop(name,args={}, {run=runJobshop}={}){
 if(!args||typeof args!=='object'||Array.isArray(args))return limited('invalid_read_arguments');
 const key=name==='jobshop_inventory'?'career_origin':name==='jobshop_detail'?'job_url':null;
 if(name==='jobshop_capabilities')return Object.keys(args).length?limited('invalid_read_arguments'):run(['--capabilities']);
 if(!key||Object.keys(args).some(k=>k!==key)||typeof args[key]!=='string'||!args[key].length||args[key].length>(key==='job_url'?4096:2048))return limited('invalid_read_arguments');
 return run([key==='job_url'?'--job-url':'--career-origin',args[key]]);
}
