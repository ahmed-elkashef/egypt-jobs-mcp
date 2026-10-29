import {fileURLToPath} from 'node:url';
import {runNativeReader} from './native-reader.mjs';

const script=fileURLToPath(new URL('../teamtailor/reader.py',import.meta.url));
const annotations={readOnlyHint:true,destructiveHint:false,openWorldHint:true};
const careerOrigin={type:'string',maxLength:2048,description:'Exact official-employer-verified HTTPS *.teamtailor.com career origin or one of the explicitly verified custom origins in capabilities. No path, query, key or account host.'};
const guid={type:'string',minLength:36,maxLength:36,pattern:'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'};
export const teamtailorTools=[
  {name:'teamtailor_capabilities',description:'Offline original anonymous Teamtailor careers-feed contracts, exact allowed origins and employer-seed requirements. This is separate from the secret-key account API. No network.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{...annotations,openWorldHint:false}},
  {name:'teamtailor_inventory',description:'Read the exact employer careers site public API catalogue, full native JSON/RSS job feeds and advertised count. Reconcile every GUID/URL/title, preserve full description/schema/RSS variants and raw dates/remote/location facts. No role, keyword, country or candidate selection. Native counts do not establish employer/weekly/country coverage. No account API, auth, apply, contact or subscription.',inputSchema:{type:'object',properties:{careers_origin:careerOrigin},required:['careers_origin'],additionalProperties:false},annotations},
  {name:'teamtailor_detail',description:'Acquire the same full unfiltered native career feeds and select one exact returned native GUID. Returns complete native description and body/schema/RSS variants; absence is a source limitation, never a fabricated empty posting or a guessed URL. Source evidence is not person fit or application readiness.',inputSchema:{type:'object',properties:{careers_origin:careerOrigin,job_id:guid},required:['careers_origin','job_id'],additionalProperties:false},annotations},
];
const limited=error=>({status:'source_limited',source:'teamtailor',returned_count:null,source_result_count:null,error,coverage_complete:false,reviewed_by_model:false});
export function runTeamtailor(argv,options={}) {return runNativeReader(script,argv,{...options,source:'teamtailor',countField:'returned_count',timeoutMs:55000});}
export async function teamtailor(name,args={}, {run=runTeamtailor}={}) {
  if(!args||typeof args!=='object'||Array.isArray(args))return limited('invalid_read_arguments');
  const keys=name==='teamtailor_capabilities'?[]:name==='teamtailor_inventory'?['careers_origin']:name==='teamtailor_detail'?['careers_origin','job_id']:null;
  if(!keys||Object.keys(args).some(k=>!keys.includes(k)))return limited('invalid_read_arguments');
  if(name==='teamtailor_capabilities')return run(['--capabilities']);
  if(typeof args.careers_origin!=='string'||!args.careers_origin.length||args.careers_origin.length>2048)return limited('invalid_verified_career_origin');
  const argv=['--careers-origin',args.careers_origin];
  if(name==='teamtailor_detail'){
    if(typeof args.job_id!=='string'||!new RegExp(guid.pattern).test(args.job_id))return limited('invalid_exact_native_job_guid');
    argv.push('--job-id',args.job_id);
  }
  return run(argv);
}
