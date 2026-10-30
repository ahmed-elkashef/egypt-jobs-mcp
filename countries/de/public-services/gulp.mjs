import {fileURLToPath} from 'node:url';
import {runNativeReader} from '../../../shared/public-sources/native-reader.mjs';

const script=fileURLToPath(new URL('../discovery/gulp_reader.py',import.meta.url));
const fields={gulp_inventory:['page','first_page_total'],gulp_detail:['url']};
const limited=error=>({status:'source_limited',source:'gulp',error,returned_count:null,
  source_result_count:null,coverage_complete:false,full_posting_reviewed:false,reviewed_by_model:false});
export function runGulp(argv,options={}) {
  return runNativeReader(script,argv,{...options,source:'gulp',countField:'returned_count',timeoutMs:70000});
}
export async function gulp(name,args={}, {run=runGulp}={}) {
  if(!Object.hasOwn(fields,name)||!args||typeof args!=='object'||Array.isArray(args)
    ||Object.keys(args).some(key=>!fields[name].includes(key)))return limited('unqualified_arguments');
  if(name==='gulp_detail') {
    if(typeof args.url!=='string'||/\s/.test(args.url)||!/^https:\/\/www\.gulp\.de\/gulp2\/g\/jobs\/C[0-9]{8}$/.test(args.url))
      return limited('exact_acquired_native_job_URI_required');
    return run(['detail','--url',args.url]);
  }
  const page=args.page===undefined?0:args.page;
  if(!Number.isInteger(page)||page<0||page>=500000)return limited('invalid_zero_based_native_page');
  if(page===0&&args.first_page_total!==undefined)return limited('initial_page_cannot_carry_counter_state');
  if(page>0&&(!Number.isInteger(args.first_page_total)||args.first_page_total<1||args.first_page_total>10000000
    ||page*20>=args.first_page_total))return limited('continuation_requires_acquired_counter_and_in_range_native_page');
  const argv=['inventory','--page',String(page)];
  if(page>0)argv.push('--first-page-total',String(args.first_page_total));
  return run(argv);
}
