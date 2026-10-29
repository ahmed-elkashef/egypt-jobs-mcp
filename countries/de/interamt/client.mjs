// Original read-only implementation from the provider's published OpenAPI.
export const BASES=new Set(['https://www.interamt.de/koop/rest/v1/import',
  'https://gate.interamt.de/interamtApi/v1/api']);
export const DOCUMENTATION='https://gate.interamt.de/interamtApi/api-doc/Interamt.yaml';
export const ROUTES={agency_list:'/Stellenangebote',multi_agency:'/MasterBehoerde',internships:'/Export/Praktikum'};

export function capabilities(){return {source:'interamt',documentation:DOCUMENTATION,
  operations:['agency_list','multi_agency','internships','detail'],methods:['GET'],
  credentials:'Caller-approved INTERAMT_API_KEY, never a tool argument.',
  configuration:'Explicit INTERAMT_API_BASE required; no credentials are sent to a default staging host.',
  allowed_bases:[...BASES],
  scope:'Agency list is one authorized customer, not the national market. Multi-agency/internships require a MultiMandant key.',
  pagination:'Published schema returns one native array; no page/cursor is invented.',
  source_status:'credential_required',coverage_complete:false,reviewed_by_model:false};}

export function endpoint({operation,id},base){
  if(!BASES.has(base))throw new Error('Configure an exact provider-published API base.');
  if(operation==='detail'){
    if(typeof id!=='number'||!Number.isSafeInteger(id)||id<1)throw new Error('A positive numeric source ID is required.');
    return base+`/Stellenangebote/${id}`;
  }
  if(!Object.hasOwn(ROUTES,operation)||id!==undefined)throw new Error('Unsupported read operation or stray ID.');
  return base+ROUTES[operation];
}
const limit=(status,code,message,extra={})=>({source:'interamt',status,code,message,
  coverage_complete:false,reviewed_by_model:false,...extra});

export async function read(input,{env=process.env,fetchImpl=fetch,maxBytes=8*1024*1024,timeoutMs=20000}={}){
  // Validate the operation before checking a secret or touching the network.
  let url;
  try{url=endpoint(input,env.INTERAMT_API_BASE||[...BASES][0]);}
  catch{return limit('invalid_request','invalid_request','Unsupported endpoint, operation or source ID.');}
  if(!env.INTERAMT_API_KEY?.trim())return limit('credential_required','missing_approved_key','Configure an approved provider key locally; no request was made.');
  if(!env.INTERAMT_API_BASE)return limit('configuration_required','missing_api_base','Confirm the API base for the granted key; no request was made.');
  try{
    const response=await fetchImpl(url,{method:'GET',redirect:'manual',
      headers:{Accept:'application/json','X-API-Key':env.INTERAMT_API_KEY},signal:AbortSignal.timeout(timeoutMs)});
    if(!response.ok){await response.body?.cancel();return limit('source_limited','provider_http_error',`Interamt HTTP ${response.status}; no automatic retry or redirect.`,{http_status:response.status,retry_after:response.headers.get('retry-after')});}
    if(!/\bapplication\/(?:[a-z.+-]*\+)?json\b/i.test(response.headers.get('content-type')||'')){
      await response.body?.cancel();return limit('source_limited','unexpected_content_type','Expected a native JSON response.');}
    if(Number(response.headers.get('content-length'))>maxBytes){await response.body?.cancel();return limit('source_limited','response_too_large','Complete response exceeds the configured bound; nothing was sliced.');}
    const reader=response.body.getReader();let size=0;const parts=[];
    try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;
      if(size>maxBytes){await reader.cancel();return limit('source_limited','response_too_large','Complete response exceeds the configured bound; nothing was sliced.');}parts.push(value);}}
    finally{reader.releaseLock();}
    let data;try{data=JSON.parse(Buffer.concat(parts).toString('utf8'));}catch{return limit('source_limited','invalid_json','Native response was not valid JSON.');}
    if(!data||typeof data!=='object'||Array.isArray(data))return limit('source_limited','invalid_envelope','Expected the provider object envelope.');
    if(input.operation!=='detail'&&!Array.isArray(data.stellenangebote))return limit('source_limited','missing_inventory','Expected stellenangebote array; missing structure is not empty supply.');
    if(input.operation==='detail'&&data.Id!==input.id)return limit('source_limited','detail_identity_mismatch','Native detail ID is missing or differs from the requested source ID.');
    return {source:'interamt',status:'ok',operation:input.operation,
      observed_at:new Date().toISOString(),source_url:url,
      scope:input.operation==='agency_list'?'authorized_single_customer':'authorized_provider_scope',
      native_returned_count:Array.isArray(data.stellenangebote)?data.stellenangebote.length:null,
      raw_response:data,coverage_complete:false,reviewed_by_model:false,
      limits:[capabilities().scope,'Published API server description includes staging; deployment and key scope must be confirmed with provider.','All native fields retained. Published list may omit attributes; use exact numeric detail IDs. No national completeness or original-time qualification is inferred.']};
  }catch{return limit('source_limited','transport_failure','Request failed, timed out or response could not be read; no retry was made.');}
}
