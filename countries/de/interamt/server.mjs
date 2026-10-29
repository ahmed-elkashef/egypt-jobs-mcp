import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {StdioServerTransport} from '@modelcontextprotocol/sdk/server/stdio.js';
import {z} from 'zod';
import {capabilities,read} from './client.mjs';
const server=new McpServer({name:'germany-public-services',version:'0.1.0'});
const result=data=>({content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data,
  isError:!['ok',undefined].includes(data.status)});
const annotations={readOnlyHint:true,destructiveHint:false,openWorldHint:true};
server.registerTool('interamt_capabilities',{description:'Offline official Interamt API scope, credentials, fixed GET operations and customer/MultiMandant restrictions. No request or account action.',inputSchema:{},annotations:{...annotations,openWorldHint:false}},async()=>result(capabilities()));
server.registerTool('interamt_read',{description:'Read one approved Interamt customer/multi-agency/internship array or exact numeric detail. Requires locally approved key and explicit provider API base. Agency list is not all Germany. No arbitrary URL, query, write, credential argument or browser fallback.',
  inputSchema:{operation:z.enum(['agency_list','multi_agency','internships','detail']),id:z.number().int().positive().optional()},annotations},async input=>result(await read(input)));
await server.connect(new StdioServerTransport());
