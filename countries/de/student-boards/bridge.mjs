import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const execute=promisify(execFile);
const script=fileURLToPath(new URL('./jobmensa.py',import.meta.url));
export async function jobmensa(input={}){
 const args=input.operation?['--operation',input.operation,'--url',input.url]:['--capabilities'];
 try{
  const {stdout}=await execute(process.env.EGYPT_JOBS_PYTHON??'python3',[script,...args],{
   timeout:58000,maxBuffer:8*1024*1024,env:Object.fromEntries(
    ['PATH','HOME','LANG','LC_ALL','TMPDIR','TEMP','TMP','JOB_MARKET_CAPTURE_DIR','HTTPS_PROXY','HTTP_PROXY','NO_PROXY']
     .filter(k=>typeof process.env[k]==='string').map(k=>[k,process.env[k]]))});
  return JSON.parse(stdout);
 }catch(error){
  if(error.stdout){try{return JSON.parse(error.stdout);}catch{/* Never return a clipped body. */}}
  return {source:'jobmensa',status:'source_limited',coverage_complete:false,reviewed_by_model:false,
   returned_count:null,message:'Native source process failed or exceeded a transport bound; no truncated listings.'};
 }
}
