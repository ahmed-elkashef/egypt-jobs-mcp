import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {StdioServerTransport} from '@modelcontextprotocol/sdk/server/stdio.js';
import {z} from 'zod';
import {capabilities,read} from '../interamt/client.mjs';
import {jobmensa,studentBoards} from '../student-boards/bridge.mjs';
const server=new McpServer({name:'germany-public-services',version:'0.3.0'});
const result=data=>({content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data,
  isError:!['ok',undefined].includes(data.status)});
const annotations={readOnlyHint:true,destructiveHint:false,openWorldHint:true};
server.registerTool('interamt_capabilities',{description:'Offline official Interamt API scope, credentials, fixed GET operations and customer/MultiMandant restrictions. No request or account action.',inputSchema:{},annotations:{...annotations,openWorldHint:false}},async()=>result(capabilities()));
server.registerTool('interamt_read',{description:'Read one approved Interamt customer/multi-agency/internship array or exact numeric detail. Requires locally approved key and explicit provider API base. Agency list is not all Germany. No arbitrary URL, query, write, credential argument or browser fallback.',
  inputSchema:{operation:z.enum(['agency_list','multi_agency','internships','detail']),id:z.number().int().positive().optional()},annotations},async input=>result(await read(input)));
server.registerTool('jobmensa_capabilities',{description:'Offline public Jobmensa list/detail scope, native fields, capture setup and limitations. No network or candidate action.',inputSchema:{},annotations:{...annotations,openWorldHint:false}},async()=>result(await jobmensa()));
for(const operation of ['page','detail'])server.registerTool(`jobmensa_${operation}`,{
 description:`Read one complete public Jobmensa ${operation} after checking current robots policy. Exact HTTPS host and native paths only. No career-keyword inventory, guessed continuation, login, application, email or subscription. Native category, date, hours and remote metadata remain unverified applicant constraints.`,
 inputSchema:{url:z.string().url().max(2048)},annotations},async({url})=>result(await jobmensa({operation,url})));
server.registerTool('student_boards_capabilities',{description:'Offline original StudentJob/YoungCapital public Germany list/detail/native redirect contracts and limits; no network or account action.',inputSchema:{},annotations:{...annotations,openWorldHint:false}},async()=>result(await studentBoards()));
for(const operation of ['page','detail','resolve_external'])server.registerTool(`student_board_${operation}`,{
 description:`Read one public StudentJob or YoungCapital ${operation} with current robots and exact native paths. Lists retain all native cards, actual continuation, filters, counts and ambiguous/promoted records. Details preserve complete visible description plus conflicting JSON-LD; URL ID is authoritative over placeholder schema IDs. External resolution only HEADs the native redirect when policy permits, never fetches its target. No keyword census, apply, login, save, subscription, email or profile action.`,
 inputSchema:{source:z.enum(['studentjob','youngcapital']),url:z.string().url().max(2048)},annotations},async input=>result(await studentBoards({...input,operation})));
await server.connect(new StdioServerTransport());
