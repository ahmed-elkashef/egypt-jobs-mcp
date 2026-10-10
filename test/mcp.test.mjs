import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync, chmodSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const serverPath = fileURLToPath(new URL('../index.mjs',import.meta.url));
const python = process.env.EGYPT_JOBS_PYTHON || 'python3';
const capture = {
  url:'https://wuzzuf.net/search/jobs?filters%5Bcountry%5D%5B0%5D=Egypt',
  kind:'page',captured_at:'2026-01-01T12:00:00Z',
  html:'<div><div><h2><a href="/jobs/p/abcdefghijkl-synthetic-role-egypt">Synthetic role</a></h2></div><a>Part Time</a></div>',
};

async function connected(env,run) {
  const client = new Client({name:'egypt-jobs-offline-test',version:'0.1.0'});
  try {
    await client.connect(new StdioClientTransport({command:process.execPath,args:[serverPath],env:{...process.env,...env}}));
    return await run(client);
  } finally {
    await client.close();
  }
}

test('portable installed backend preserves parse and immutable receipt contracts',async () => {
  const cache = mkdtempSync(path.join(tmpdir(),'egypt-jobs-mcp-test-'));
  try {
    const saved = JSON.parse(execFileSync(python,['-c',
      'import json,sys; from egypt_job_sources.capture import save_capture; print(json.dumps(save_capture("wuzzuf", json.load(sys.stdin))))'],
      {input:JSON.stringify(capture),encoding:'utf8',env:{...process.env,EGYPT_JOBS_CAPTURE_DIR:cache}}));
    await connected({EGYPT_JOBS_CAPTURE_DIR:cache},async client => {
      const listed = await client.listTools();
      assert.equal(listed.tools.length,15);
      assert.ok(listed.tools.every(tool=>tool.annotations?.readOnlyHint===true));
      assert.ok(listed.tools.find(tool=>tool.name==='read_source_page').inputSchema.properties.work_model.enum.includes('full_time'));
      for (const request of [
        {name:'parse_rendered_board_page',arguments:{source:'wuzzuf',capture}},
        {name:'read_saved_board_capture',arguments:{receipt_id:saved.receipt_id}},
      ]) {
        const response = await client.callTool(request);
        assert.equal(response.isError,false);
        assert.equal(response.structuredContent.status,'ok');
        assert.equal(response.structuredContent.listings[0].id,'abcdefghijkl');
        assert.equal(response.structuredContent.coverage_complete,false);
        assert.equal(response.structuredContent.reviewed_by_model,false);
      }
      const refused = await client.callTool({name:'read_source_detail',arguments:{source:'wuzzuf',url:'https://example.invalid/private'}});
      assert.equal(refused.isError,true);
      assert.equal(refused.structuredContent.status,'source_limited');
      assert.equal(refused.structuredContent.coverage_complete,false);
      assert.ok(!('listings' in refused.structuredContent));
    });
  } finally {
    rmSync(cache,{recursive:true,force:true});
  }
});

test('missing interpreter is an explicit limitation and does not crash the MCP',async () => {
  await connected({EGYPT_JOBS_PYTHON:path.join(tmpdir(),'egypt-jobs-nonexistent-python')},async client => {
    const response = await client.callTool({name:'jobicy_location_taxonomy',arguments:{}});
    assert.equal(response.isError,true);
    assert.equal(response.structuredContent.status,'source_limited');
    assert.equal(response.structuredContent.coverage_complete,false);
    assert.ok(!('listings' in response.structuredContent));
    assert.equal((await client.listTools()).tools.length,15);
  });
});

test('expanded tools expose contracts and refuse credential and pagination drift',async () => {
  await connected({UPWORK_ACCESS_TOKEN:''},async client => {
    for (const name of ['remote_source_capabilities','freelance_source_capabilities','ats_source_capabilities']) {
      const response = await client.callTool({name,arguments:{}});
      assert.equal(response.isError,false);
      assert.equal(response.structuredContent.status,'ok');
      assert.equal(response.structuredContent.coverage_complete,false);
      assert.equal(response.structuredContent.reviewed_by_model,false);
    }
    for (const request of [
      {name:'read_remote_feed',arguments:{source:'remotive',cursor:'source-cursor'}},
      {name:'read_freelance_projects',arguments:{source:'freelancer',cursor:'source-cursor'}},
      {name:'read_freelance_projects',arguments:{source:'upwork',offset:20}},
      {name:'read_freelance_projects',arguments:{source:'upwork'}},
      {name:'read_freelance_project_detail',arguments:{source:'upwork',project_id:'synthetic-id'}},
    ]) {
      const response = await client.callTool(request);
      assert.equal(response.isError,true);
      assert.equal(response.structuredContent.status,'source_limited');
      assert.equal(response.structuredContent.coverage_complete,false);
      assert.equal(response.structuredContent.reviewed_by_model,false);
      assert.ok(!('listings' in response.structuredContent));
    }
    const listed = await client.listTools();
    assert.ok(listed.tools.every(tool=>tool.annotations.readOnlyHint===true));
    assert.ok(!listed.tools.some(tool=>/apply|bid|message|submit|pay/.test(tool.name)));
    for (const name of ['read_remote_feed','read_freelance_projects']) {
      const fields = Object.keys(listed.tools.find(tool=>tool.name===name).inputSchema.properties);
      assert.ok(!fields.some(field=>/keyword|title|skill|salary|token|cookie|query|mutation/.test(field)));
    }
    const approval = await client.callTool({name:'read_freelance_projects',arguments:{source:'upwork'}});
    assert.equal(approval.structuredContent.api_approval_required,true);
    assert.match(approval.structuredContent.approval_reference,/support\.upwork\.com/);
    assert.ok(!('reported_total' in approval.structuredContent));
  });
});

test('oversize complete output is an honest limitation and the MCP connection survives',async () => {
  const directory=mkdtempSync(path.join(tmpdir(),'egypt-jobs-large-test-'));
  const shim=path.join(directory,'python-shim');
  const size=13*1024*1024;
  try {
    writeFileSync(shim,`#!/usr/bin/env node\nprocess.stdout.write(JSON.stringify({status:'ok',coverage_complete:false,reviewed_by_model:false,listings:[{id:'synthetic',description:'x'.repeat(${size})}]}));\n`);
    chmodSync(shim,0o700);
    await connected({EGYPT_JOBS_PYTHON:shim},async client => {
      const response=await client.callTool({name:'read_remote_feed',arguments:{source:'remotive'}});
      assert.equal(response.isError,true);
      assert.match(response.structuredContent.error,/9 MiB MCP message limit/);
      assert.ok(!('listings' in response.structuredContent));
      assert.equal((await client.listTools()).tools.length,15);
    });
  } finally { rmSync(directory,{recursive:true,force:true}); }
});

test('large supported descriptions survive actual stdio without text slicing',async () => {
  const directory=mkdtempSync(path.join(tmpdir(),'egypt-jobs-medium-test-'));
  const shim=path.join(directory,'python-shim');
  const size=3*1024*1024;
  try {
    writeFileSync(shim,`#!/usr/bin/env node\nprocess.stdout.write(JSON.stringify({status:'ok',coverage_complete:false,reviewed_by_model:false,listings:[{id:'synthetic',description:'x'.repeat(${size})}]}));\n`);
    chmodSync(shim,0o700);
    await connected({EGYPT_JOBS_PYTHON:shim},async client => {
      const response=await client.callTool({name:'read_remote_feed',arguments:{source:'remotive'}});
      assert.equal(response.isError,false);
      assert.equal(response.structuredContent.listings[0].description.length,size);
    });
  } finally { rmSync(directory,{recursive:true,force:true}); }
});

test('early backend exit while receiving a capture stays a limitation without crashing',async () => {
  const directory=mkdtempSync(path.join(tmpdir(),'egypt-jobs-early-exit-'));
  const shim=path.join(directory,'python-shim');
  try {
    writeFileSync(shim,'#!/usr/bin/env node\nprocess.exit(1);\n');
    chmodSync(shim,0o700);
    await connected({EGYPT_JOBS_PYTHON:shim},async client => {
      const response=await client.callTool({name:'parse_rendered_board_page',arguments:{source:'wuzzuf',capture:{...capture,html:'x'.repeat(2*1024*1024)}}});
      assert.equal(response.isError,true);
      assert.equal(response.structuredContent.status,'source_limited');
      assert.equal((await client.listTools()).tools.length,15);
    });
  } finally { rmSync(directory,{recursive:true,force:true}); }
});
