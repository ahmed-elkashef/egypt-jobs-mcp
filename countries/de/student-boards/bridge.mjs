import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const execute=promisify(execFile);
async function native(script,args,source){
 try{
  const {stdout}=await execute(process.env.EGYPT_JOBS_PYTHON??'python3',[fileURLToPath(new URL(script,import.meta.url)),...args],{
   timeout:58000,maxBuffer:8*1024*1024,env:Object.fromEntries(
    ['PATH','HOME','LANG','LC_ALL','TMPDIR','TEMP','TMP','JOB_MARKET_CAPTURE_DIR','HTTPS_PROXY','HTTP_PROXY','NO_PROXY']
     .filter(k=>typeof process.env[k]==='string').map(k=>[k,process.env[k]]))});
  return JSON.parse(stdout);
 }catch(error){
  if(error.stdout){try{return JSON.parse(error.stdout);}catch{/* No clipped response. */}}
  return {source,status:'source_limited',coverage_complete:false,reviewed_by_model:false,
   returned_count:null,message:'Native source process failed or exceeded a transport bound; no truncated listings.'};
 }
}
export async function jobmensa(input={}){
 return native('./jobmensa.py',input.operation?['--operation',input.operation,'--url',input.url]:['--capabilities'],'jobmensa');
}
export async function studentBoards(input={}){
 return native('./studentjobs.py',input.operation?['--source',input.source,'--operation',input.operation,'--url',input.url]:['--capabilities'],input.source??'student_boards');
}

export async function germanBoards(input={}){
 return native('../public-boards/readers.py',input.operation?['--source',input.source,'--operation',input.operation,'--url',input.url]:['--capabilities'],input.source??'german_public_boards');
}
