import {z} from 'zod';

// Raw SDK shapes strip unknown keys before reaching guarded readers. Preserve
// the exact public-DE contract by rejecting them at the actual MCP boundary.
export function registerStrictReadTool(server,name,config,handler) {
  return server.registerTool(name,{...config,inputSchema:z.strictObject(config.inputSchema)},handler);
}
