import {fileURLToPath} from 'node:url';
import {runNativeReader} from '../../../shared/public-sources/native-reader.mjs';

const script=fileURLToPath(new URL('../discovery/state_reader.py',import.meta.url));
const fields={state_portal_inventory:['provider','scope','start','first_page_total'],
  state_portal_detail:['provider','url']};
const limited=error=>({status:'source_limited',source:'berlin_state_jobs',error,
  returned_count:null,source_result_count:null,coverage_complete:false,
  full_posting_reviewed:false,reviewed_by_model:false});
export function runStatePortal(argv,options={}) {
  return runNativeReader(script,argv,{...options,source:'berlin_state_jobs',
    countField:'returned_count',timeoutMs:70000});
}
export async function statePortal(name,args={}, {run=runStatePortal}={}) {
  if(!Object.hasOwn(fields,name)||!args||typeof args!=='object'||Array.isArray(args)
    ||Object.keys(args).some(k=>!fields[name].includes(k))||args.provider!=='berlin')
    return limited('unqualified_provider_or_arguments');
  if(name==='state_portal_detail') {
    if(typeof args.url!=='string'||!args.url.length||args.url.length>4096)
      return limited('exact_acquired_advert_URI_required');
    return run(['state_detail','--provider','berlin','--url',args.url]);
  }
  const start=args.start===undefined?0:args.start;
  if(!['all','student_entry'].includes(args.scope)||!Number.isInteger(start)||start<0||start>1000000)
    return limited('invalid_native_scope_or_offset');
  if((start===0&&args.first_page_total!==undefined)||(start>0&&(!Number.isInteger(args.first_page_total)
    ||args.first_page_total<=start||args.first_page_total>1000000)))return limited('unqualified_initial_native_total');
  const argv=['state_inventory','--provider','berlin','--scope',args.scope,'--start',String(start)];
  if(start>0)argv.push('--first-page-total',String(args.first_page_total));
  return run(argv);
}
