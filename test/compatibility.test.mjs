import test from 'node:test';
import assert from 'node:assert/strict';
test('legacy public module paths retain the exact country exports',async()=>{
  for(const name of ['ats-tools.mjs','expanded-tools.mjs','browser-extract.mjs','browser-runner.mjs','browser-tools.mjs']){
    const legacy=await import('../'+name),canonical=await import('../countries/eg/mcp/'+name);
    assert.deepEqual(Object.keys(legacy),Object.keys(canonical));
    for(const key of Object.keys(legacy))assert.equal(legacy[key],canonical[key]);
  }
});
