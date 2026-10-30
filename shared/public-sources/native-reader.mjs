import {spawn} from 'node:child_process';

/** Fixed-script, bounded IPC for original anonymous readers. Never a tool input. */
export function runNativeReader(script,argv,{source,countField='count',spawnProcess=spawn,env=process.env,timeoutMs=80000}={}) {
  const limited=error=>({status:'source_limited',source,[countField]:null,source_result_count:null,error,coverage_complete:false,reviewed_by_model:false});
  return new Promise(resolve=>{
    const names=['PATH','HOME','SYSTEMROOT','TMPDIR','TEMP','TMP','LANG','LC_ALL','HTTPS_PROXY','HTTP_PROXY','NO_PROXY','SSL_CERT_FILE'];
    const childEnv=Object.fromEntries(names.filter(k=>typeof env[k]==='string').map(k=>[k,env[k]]));
    const command=env.EGYPT_JOBS_PYTHON||env.JOB_MARKET_PYTHON||'python3';
    let child,done=false,size=0;
    const chunks=[];
    const finish=value=>{if(done)return;done=true;clearTimeout(timer);resolve(value);};
    const timer=setTimeout(()=>{child?.kill('SIGKILL');finish(limited('native_reader_timeout'));},timeoutMs);
    try {child=spawnProcess(command,[script,...argv],{env:childEnv,stdio:['ignore','pipe','ignore'],shell:false});}
    catch {finish(limited('native_reader_unavailable'));return;}
    child.stdout.on('data',chunk=>{
      if(done)return;
      size+=chunk.length;
      if(size>8*1024*1024){child.kill('SIGKILL');finish(limited('complete_response_exceeds_bridge_bound'));return;}
      chunks.push(chunk);
    });
    child.on('error',()=>finish(limited('native_reader_unavailable')));
    child.on('close',code=>{
      if(done)return;
      if(code!==0&&code!==2){finish(limited('native_reader_failed'));return;}
      try {
        const result=JSON.parse(Buffer.concat(chunks).toString('utf8'));
        if(!result||typeof result!=='object'||Array.isArray(result)||!['ok','source_limited'].includes(result.status)||result.source!==source)throw Error();
        // Fixed readers use exit2 for a typed, non-promoting source limit.
        // Preserve its exact policy/contract evidence, never a failed 'ok'.
        if(code===2&&(result.status!=='source_limited'||result.coverage_complete!==false
          ||result.reviewed_by_model!==false||result[countField]!==null))throw Error();
        finish(result);
      }catch {finish(limited(code===2?'native_reader_failed':'invalid_native_reader_result'));}
    });
  });
}
