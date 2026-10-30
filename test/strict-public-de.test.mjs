import test from 'node:test';
import assert from 'node:assert/strict';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {InMemoryTransport} from '@modelcontextprotocol/sdk/inMemory.js';
import {z} from 'zod';
import {registerStrictReadTool} from '../countries/de/public-services/strict-tools.mjs';

async function fixture(run){
 const server=new McpServer({name:'synthetic-strict-protocol',version:'1'});
 const client=new Client({name:'strict-contract-test',version:'1'});
 let calls=0;
 registerStrictReadTool(server,'synthetic_reader',{inputSchema:{page:z.number().int().nonnegative().optional()},
  annotations:{readOnlyHint:true}},async()=>{calls++;return{content:[{type:'text',text:'synthetic result'}]};});
 const [a,b]=InMemoryTransport.createLinkedPair();
 try{await server.connect(a);await client.connect(b);await run(client,()=>calls);}
 finally{await client.close();await server.close();}
}
test('actual MCP rejects unknown filters before invoking the guarded reader',async()=>{
 await fixture(async(client,calls)=>{
  const result=await client.callTool({name:'synthetic_reader',arguments:{query:'marketing'}});
  assert.equal(result.isError,true);assert.match(result.content[0].text,/Input validation error/);
  assert.equal(calls(),0);
  const valid=await client.callTool({name:'synthetic_reader',arguments:{page:0}});
  assert.notEqual(valid.isError,true);assert.equal(calls(),1);
 });
});
test('actual MCP rejects null native values and keeps declared strict schema',async()=>{
 await fixture(async(client,calls)=>{
  const tools=await client.listTools();assert.equal(tools.tools[0].inputSchema.additionalProperties,false);
  const result=await client.callTool({name:'synthetic_reader',arguments:{page:null}});
  assert.equal(result.isError,true);assert.match(result.content[0].text,/Input validation error/);assert.equal(calls(),0);
 });
});
