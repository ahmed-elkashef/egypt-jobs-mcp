import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'node:url';

const client = new Client({name:'egypt-jobs-mcp-smoke',version:'0.2.0'});
try {
  await client.connect(new StdioClientTransport({command:process.execPath,args:[fileURLToPath(new URL('./index.mjs',import.meta.url))]}));
  const result = await client.listTools();
  const names = result.tools.map(tool=>tool.name);
  if (names.length !== 11 || result.tools.some(tool=>tool.annotations?.readOnlyHint !== true)) throw Error('Read-only tool contract failed');
  console.log(JSON.stringify({status:'connected',tools:names}));
} finally {
  await client.close();
}
