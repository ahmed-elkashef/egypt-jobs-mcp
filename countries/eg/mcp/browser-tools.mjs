import {z} from 'zod';
import {browserCapturePlan} from './browser-runner.mjs';

export function registerBrowserCapturePlan(server) {
  server.registerTool('browser_capture_plan',{
    description:'Discover the verified person-neutral native browser recipe for Tanqeeb or Forasna Egypt. Execution uses browser-runner.mjs inside the authorized CUA runtime with injected tabs and a trusted private checkpoint sink. No browser launch, session export, CAPTCHA bypass, arbitrary URL fetch, application or candidate ranking. Native filtering requires returned card membership and exact continuation checks.',
    inputSchema:{source:z.enum(['tanqeeb','forasna']),work_model:z.enum(['part_time','internship','freelance_project','all']).default('part_time')},
    annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false},
  },async ({source,work_model})=>{
    let data;
    try{data={status:'ok',...browserCapturePlan({source,workModel:work_model}),coverage_complete:false,reviewed_by_model:false};}
    catch(error){data={status:'source_limited',error:error.message,coverage_complete:false,reviewed_by_model:false};}
    return {content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data,isError:data.status==='source_limited'};
  });
}
