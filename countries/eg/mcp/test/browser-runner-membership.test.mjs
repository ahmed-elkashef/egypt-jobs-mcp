import assert from 'node:assert/strict';
import test from 'node:test';
import {membership} from '../browser-runner.mjs';

const page = (types=[]) => ({
  country:{value:'مصر',text:'Egypt'},
  controls:[{name:'Egypt-country',value:true},{name:'half-day',value:types.includes('نصف-يوم-jobtype')},
    ...types.map(value=>({name:'selected-jobtype',value}))],
  rows:[{id:'999001',url:'https://forasna.com/job/p/synthetic-example-999001',type:'يوم كامل'}],
});

test('Forasna broad inventory accepts the observed native All selection', () => {
  assert.equal(membership(page(['الكل-jobtype']),'forasna','all'),null);
  assert.equal(membership(page(),'forasna','all'),null);
});

test('Forasna broad inventory still refuses restrictive types and foreign scope', () => {
  for (const type of ['نصف-يوم-jobtype','يوم-كامل-jobtype','عمل-من-المنزل-jobtype','عمل-حر-jobtype']) {
    assert.equal(membership(page([type]),'forasna','all'),'selected_filter_drift');
  }
  assert.equal(membership(page(['الكل-jobtype','نصف-يوم-jobtype']),'forasna','all'),'selected_filter_drift');
  const foreign=page(['الكل-jobtype']); foreign.country.value='السعودية';
  assert.equal(membership(foreign,'forasna','all'),'selected_filter_drift');
});

test('Forasna priority still refuses full-time-only returned membership', () => {
  assert.equal(membership(page(['نصف-يوم-jobtype']),'forasna','part_time'),'native_membership_drift');
  const half=page(['نصف-يوم-jobtype']); half.rows[0].type='نصف يوم';
  assert.equal(membership(half,'forasna','part_time'),null);
});

test('Forasna All selection does not suppress barriers or unsettled cards', () => {
  assert.equal(membership({...page(['الكل-jobtype']),gate:'challenge'},'forasna','all'),'source_barrier');
  assert.equal(membership({...page(['الكل-jobtype']),rows:[]},'forasna','all'),'unsettled_or_changed_markup');
  const missingId=page(['الكل-jobtype']); missingId.rows[0].id='';
  assert.equal(membership(missingId,'forasna','all'),'unsettled_or_changed_markup');
});
