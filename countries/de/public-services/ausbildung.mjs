import {fileURLToPath} from 'node:url';
import {runNativeReader} from '../../../shared/public-sources/native-reader.mjs';

const script=fileURLToPath(new URL('../public-boards/ausbildung_reader.py',import.meta.url));
const catalogue='https://www.ausbildung.de/schuelerpraktikum/stellen/';
const protocol='2a3916610a6dcb25d4ff77510fd21b01119f1685d8bf530a59035f430567d40c';
const bindingKeys=['source','catalogue','protocol_sha256','resultsCount','vacanciesCount','countryEntryCode'];
const fields={ausbildung_inventory:['from','native_binding'],ausbildung_detail:['url']};
const limited=error=>({status:'source_limited',source:'ausbildung_de',error,returned_count:null,
 source_result_count:null,coverage_complete:false,full_posting_reviewed:false,reviewed_by_model:false});
export function runAusbildung(argv,options={}) {
 return runNativeReader(script,argv,{...options,source:'ausbildung_de',countField:'returned_count',timeoutMs:70000});
}
export async function ausbildung(name,args={}, {run=runAusbildung}={}) {
 if(!Object.hasOwn(fields,name)||!args||typeof args!=='object'||Array.isArray(args)
  ||Object.keys(args).some(key=>!fields[name].includes(key)))return limited('unqualified_arguments');
 if(name==='ausbildung_detail') {
  if(typeof args.url!=='string'||/\s/.test(args.url)||!/^https:\/\/www\.ausbildung\.de\/schuelerpraktikum\/stellen\/[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\/$/.test(args.url))
   return limited('exact_acquired_native_advert_URI_required');
  return run(['detail','--url',args.url]);
 }
 const offset=args.from===undefined?0:args.from,b=args.native_binding;
 if(!Number.isInteger(offset)||offset<0||offset>=10000000||offset%20)return limited('native_from_must_be_nonnegative_multiple_of_twenty');
 if(offset===0&&b!==undefined)return limited('initial_catalogue_cannot_carry_resume_binding');
 if(offset>0&&(!b||typeof b!=='object'||Array.isArray(b)||Object.keys(b).length!==bindingKeys.length
  ||bindingKeys.some(key=>!Object.hasOwn(b,key))||b.source!=='ausbildung_de'||b.catalogue!==catalogue
  ||b.protocol_sha256!==protocol||b.countryEntryCode!=='DE'||!Number.isInteger(b.resultsCount)
  ||b.resultsCount<1||b.resultsCount>10000000||offset>=b.resultsCount||!Number.isInteger(b.vacanciesCount)
  ||b.vacanciesCount<0||b.vacanciesCount>10000000))return limited('continuation_requires_exact_acquired_native_binding_and_in_range_from');
 const argv=['inventory','--from',String(offset)];
 if(offset>0)argv.push('--native-binding',JSON.stringify(b));
 return run(argv);
}
