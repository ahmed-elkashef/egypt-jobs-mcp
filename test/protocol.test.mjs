import test from 'node:test';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

test('legacy root entrypoint still serves the original Egypt tool catalogue',async()=>{
  const client=new Client({name:'legacy-entry-test',version:'1'});
  try{
    await client.connect(new StdioClientTransport({command:process.execPath,args:[fileURLToPath(new URL('../index.mjs',import.meta.url))],env:{...process.env},stderr:'pipe'}));
    const tools=(await client.listTools()).tools;
    assert.equal(tools.length,16);assert.ok(tools.some(t=>t.name==='read_source_page'));
    const result=await client.callTool({name:'browser_capture_plan',arguments:{source:'forasna'}});
    assert.notEqual(result.isError,true);
  }finally{await client.close();}
});

test('real unified stdio lists countries and routes through Egypt and Germany offline',async()=>{
  const client=new Client({name:'country-protocol-test',version:'1'});
  const transport=new StdioClientTransport({command:process.execPath,args:[fileURLToPath(new URL('../server.mjs',import.meta.url))],env:{...process.env},stderr:'pipe'});
  transport.stderr?.on('data',()=>{});
  try{
    await client.connect(transport);
    const list=await client.listTools();
    for(const name of ['list_countries','list_country_sources','plan_country_scan','eg_read_source_page','de_ba_job_suche','de_stepstone_get_capabilities','shared_get_public_inventory','de_public_interamt_capabilities','de_public_interamt_read','de_public_jobmensa_capabilities','de_public_jobmensa_page','de_public_jobmensa_detail','de_public_student_boards_capabilities','de_public_student_board_page','de_public_student_board_detail','de_public_student_board_resolve_external','de_public_german_boards_capabilities','de_public_german_board_inventory','de_public_german_board_detail'])assert.ok(list.tools.some(t=>t.name===name),name);
    assert.equal(list.tools.length,62);
    assert.ok(list.tools.every(t=>t.annotations?.readOnlyHint===true));
    const countries=await client.callTool({name:'list_countries',arguments:{}});
    assert.equal(countries.structuredContent.countries.length,2);
    assert.ok(Object.values(countries.structuredContent.backend_status).every(b=>b.state==='ready'));
    const student=await client.callTool({name:'de_public_jobmensa_capabilities',arguments:{}});
    assert.equal(student.structuredContent.source,'jobmensa');
    const refused=await client.callTool({name:'de_public_jobmensa_page',arguments:{url:'https://example.test/jobs-suchen'}});
    assert.equal(refused.isError,true);assert.equal(refused.structuredContent.returned_count,null);
    const boards=await client.callTool({name:'de_public_student_boards_capabilities',arguments:{}});
    assert.deepEqual(boards.structuredContent.sources,['studentjob','youngcapital']);
    const unsafe=await client.callTool({name:'de_public_student_board_page',arguments:{source:'studentjob',url:'https://example.test/stellenangebote'}});
    assert.equal(unsafe.isError,true);assert.equal(unsafe.structuredContent.returned_count,null);
    const publicBoards=await client.callTool({name:'de_public_german_boards_capabilities',arguments:{}});
    assert.equal(publicBoards.structuredContent.sources.length,6);
    const unsafeBoard=await client.callTool({name:'de_public_german_board_inventory',arguments:{source:'germantechjobs',url:'https://germantechjobs.de/api/jobApply'}});
    assert.equal(unsafeBoard.isError,true);assert.equal(unsafeBoard.structuredContent.returned_count,null);
    const interamt=await client.callTool({name:'de_public_interamt_read',arguments:{operation:'agency_list'}});
    assert.equal(interamt.isError,true);assert.equal(interamt.structuredContent.status,'credential_required');
    for(const source of (await client.callTool({name:'list_country_sources',arguments:{country:'DE'}})).structuredContent.sources){
      for(const route of source.routes){const tool=list.tools.find(t=>t.name===route.public_tool);assert.ok(tool,route.public_tool);
        for(const [key,value]of Object.entries(route.fixed_arguments)){const schema=tool.inputSchema.properties[key];assert.ok(schema,key);if(schema.enum)assert.ok(schema.enum.includes(value));}}
    }
    const capture={url:'https://www.akhtaboot.com/en/egypt/jobs',kind:'page',captured_at:'2026-10-01T00:00:00Z',html:'<section data-public-native-filters data-country="Egypt"></section><li id="current_page">Jobs in Egypt</li><p class="error_message">Sorry, no results found</p>'};
    const parsed=await client.callTool({name:'eg_parse_rendered_board_page',arguments:{source:'akhtaboot',capture}});
    assert.equal(parsed.isError,false);assert.equal(parsed.structuredContent.native_empty_state_verified,true);
    const bad=await client.callTool({name:'de_ba_job_suche',arguments:{page:0}});
    assert.equal(bad.isError,true);assert.equal(bad.structuredContent.coverage_complete,false);
    const html='<script type="application/ld+json">'+JSON.stringify({'@context':'https://schema.org','@type':'JobPosting',title:'Synthetic role',identifier:{value:'123456'},description:'<p>'+('Full duties. '.repeat(500))+'</p>',hiringOrganization:{name:'Synthetic'},url:'https://www.stepstone.de/stellenangebote--Synthetic--123456-inline.html'})+'</script>';
    const detail=await client.callTool({name:'de_stepstone_parse_job_html',arguments:{html,source_url:'https://www.stepstone.de/stellenangebote--Synthetic--123456-inline.html'}});
    assert.equal(detail.isError,false);assert.ok(JSON.stringify(detail.structuredContent).length>5000);
  }finally{await client.close();}
});
