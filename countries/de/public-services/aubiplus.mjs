import {fileURLToPath} from 'node:url';
import {runNativeReader} from '../../../shared/public-sources/native-reader.mjs';

const script=fileURLToPath(new URL('../discovery/aubi_reader.py',import.meta.url));
const fields={aubiplus_inventory:['scope','page','first_page_total','continuation_url'],aubiplus_detail:['url']};
const limited=error=>({status:'source_limited',source:'aubi_plus',error,returned_count:null,
  source_result_count:null,coverage_complete:false,full_posting_reviewed:false,reviewed_by_model:false});
export function runAubiPlus(argv,options={}) {
  return runNativeReader(script,argv,{...options,source:'aubi_plus',countField:'returned_count',timeoutMs:70000});
}
export async function aubiPlus(name,args={}, {run=runAubiPlus}={}) {
  if(!Object.hasOwn(fields,name)||!args||typeof args!=='object'||Array.isArray(args)
    ||Object.keys(args).some(key=>!fields[name].includes(key)))return limited('unqualified_arguments');
  if(name==='aubiplus_detail') {
    if(typeof args.url!=='string'||!args.url.length||args.url.length>4096)return limited('exact_acquired_advert_URI_required');
    return run(['detail','--url',args.url]);
  }
  const page=args.page===undefined?1:args.page,scope=args.scope===undefined?'all':args.scope;
  if(!['all','student_internship','working_student'].includes(scope)||!Number.isInteger(page)||page<1||page>10000)
    return limited('invalid_native_scope_or_page');
  if(page===1&&(args.first_page_total!==undefined||args.continuation_url!==undefined))
    return limited('initial_page_cannot_carry_continuation_state');
  if(page>1&&(!Number.isInteger(args.first_page_total)||args.first_page_total<1||args.first_page_total>10000000
    ||typeof args.continuation_url!=='string'||!args.continuation_url.length||args.continuation_url.length>4096))
    return limited('continuation_requires_native_counter_and_acquired_URI');
  const argv=['inventory','--scope',scope,'--page',String(page)];
  if(page>1)argv.push('--first-page-total',String(args.first_page_total),'--continuation-url',args.continuation_url);
  return run(argv);
}
