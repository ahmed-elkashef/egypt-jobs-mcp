import test from 'node:test';
import assert from 'node:assert/strict';
import { captureEgyptBoardDOM } from '../browser-extract.mjs';

function syntheticDocument(url) {
  let reads = 0;
  return {
    document: {
      location: new URL(url),
      get body() {
        reads += 1;
        return { innerText: '© Constructed source notice' };
      },
      querySelector() {
        reads += 1;
        return null;
      },
      querySelectorAll() {
        reads += 1;
        return [];
      },
    },
    reads: () => reads,
  };
}

function withDocument(url, run) {
  const original = globalThis.document;
  const synthetic = syntheticDocument(url);
  globalThis.document = synthetic.document;
  try {
    run(synthetic);
  } finally {
    if (original === undefined) delete globalThis.document;
    else globalThis.document = original;
  }
}

test('public scope is validated before reading any DOM content', () => {
  const invalid = [
    ['wuzzuf', 'page', 'https://wuzzuf.net/login'],
    ['wuzzuf', 'detail', 'https://wuzzuf.net/account/profile'],
    ['forasna', 'detail', 'https://forasna.com/profile'],
    ['arabjobs', 'page', 'https://www.arabjobs.com/en/login'],
    ['wuzzuf', 'page', 'http://wuzzuf.net/search/jobs?filters%5Bcountry%5D%5B0%5D=Egypt'],
    ['wuzzuf', 'page', 'https://other.invalid/search/jobs'],
    ['wuzzuf', 'detail', 'https://u:example@wuzzuf.net/jobs/p/abcdefghijkl-example-egypt'],
    ['wuzzuf', 'detail', 'https://wuzzuf.net/jobs/p/abcdefghijkl-example-egypt?token=example'],
    ['wuzzuf', 'detail', 'https://wuzzuf.net/jobs/p/abcdefghijkl-example-egypt#account'],
    ['wuzzuf', 'page', 'https://wuzzuf.net/search/jobs?filters%5Bcountry%5D%5B0%5D=Egypt&q=example'],
    ['wuzzuf', 'page', 'https://wuzzuf.net/search/jobs?filters%5Bcountry%5D%5B0%5D=Egypt&access_token=example'],
    ['wuzzuf', 'page', 'https://wuzzuf.net/search/jobs?filters%5Bcountry%5D%5B0%5D=Other'],
    ['wuzzuf', 'page', 'https://wuzzuf.net/search/jobs?filters%5Bcountry%5D%5B0%5D=Egypt&filters%5Bcountry%5D%5B0%5D=Other'],
    ['forasna', 'page', 'https://forasna.com/%D9%88%D8%B8%D8%A7%D8%A6%D9%81-%D8%AE%D8%A7%D9%84%D9%8A%D8%A9?keyword=example'],
    ['forasna', 'detail', 'https://forasna.com/job/p/example-100001?cookie=example'],
    ['arabjobs', 'page', 'https://www.arabjobs.com/en/jobs/search/?pageIndex=1&filterJobCountry=SA&sortType=2'],
    ['arabjobs', 'page', 'https://www.arabjobs.com/en/jobs/search/?pageIndex=1&filterJobCountry=EG&sortType=2&filterJobTitle=example'],
    ['arabjobs', 'page', 'https://www.arabjobs.com/en/jobs/search/?filterJobCountry=EG&filterJobType=99&sortType=2'],
    ['forasna', 'page', 'https://forasna.com/وظائف-خالية?filters[jobType][0]=نصف%20يوم'],
    ['tanqeeb', 'page', 'https://egypt.tanqeeb.com/jobs/search?keywords=example&country=213&state=0&lang=all'],
    ['tanqeeb', 'page', 'https://egypt.tanqeeb.com/jobs/search?keywords=&country=113&state=0&lang=all'],
    ['tanqeeb', 'detail', 'https://egypt.tanqeeb.com/account/profile'],
    ['akhtaboot', 'page', 'https://www.akhtaboot.com/en/jordan/jobs'],
    ['akhtaboot', 'detail', 'https://www.akhtaboot.com/en/jordan/jobs/amman/100001-constructed'],
  ];
  for (const [source, kind, url] of invalid) {
    withDocument(url, synthetic => {
      assert.throws(() => captureEgyptBoardDOM({ source, kind }), undefined, url);
      assert.equal(synthetic.reads(), 0, `DOM content was read on ${url}`);
    });
  }
});

test('verified public paths and native page scopes are accepted', () => {
  const safe = [
    ['wuzzuf', 'page', 'https://wuzzuf.net/search/jobs?filters%5Bcountry%5D%5B0%5D=Egypt'],
    ['wuzzuf', 'page', 'https://wuzzuf.net/search/jobs?filters%5Bcountry%5D%5B0%5D=Egypt&filters%5Bjob_types%5D%5B0%5D=full_time&start=1'],
    ['wuzzuf', 'detail', 'https://wuzzuf.net/jobs/p/abcdefghijkl-example-egypt'],
    ['forasna', 'page', 'https://forasna.com/%D9%88%D8%B8%D8%A7%D8%A6%D9%81-%D8%AE%D8%A7%D9%84%D9%8A%D8%A9'],
    ['forasna', 'page', 'https://forasna.com/%D9%88%D8%B8%D8%A7%D8%A6%D9%81-%D8%AE%D8%A7%D9%84%D9%8A%D8%A9?start=30'],
    ['forasna', 'page', 'https://forasna.com/وظائف-خالية?filters[country][0]=مصر&filters[jobType][0]=نصف%20يوم'],
    ['forasna', 'detail', 'https://forasna.com/job/p/constructed-%2F-example-100001'],
    ['arabjobs', 'page', 'https://www.arabjobs.com/en/jobs/search/?pageIndex=2&filterJobCountry=EG&sortType=2'],
    ['arabjobs', 'page', 'https://www.arabjobs.com/en/jobs/search/?pageIndex=2&filterJobCountry=EG&filterJobType=2&sortType=2'],
    ['arabjobs', 'detail', 'https://www.arabjobs.com/en/jobs/j/egypt/example/100001'],
  ];
  for (const [source, kind, url] of safe) {
    withDocument(url, synthetic => {
      const result = captureEgyptBoardDOM({ source, kind });
      assert.equal(result.url, new URL(url).href);
      assert.equal(result.kind, kind);
      assert.deepEqual(Object.keys(result).sort(), ['captured_at', 'html', 'kind', 'url']);
      assert.ok(Number.isFinite(Date.parse(result.captured_at)));
      assert.ok(synthetic.reads() > 0);
    });
  }
});

test('Tanqeeb extraction requires and retains selected native state, never forms or account inputs',()=>{
  withDocument('https://egypt.tanqeeb.com/jobs/search/page/2?keywords=&country=213&state=0&lang=all',synthetic=>{
    synthetic.document.querySelector=selector=>selector.includes('countryHeader') ? {value:'213',textContent:'Egypt'} : null;
    synthetic.document.querySelectorAll=selector=>selector==='input:checked,select option:checked' ? [
      {name:'refine[job_types][]',value:'2',labels:[{innerText:'Part Time'}]},
      {name:'refine[order_by]',value:'most_recent',labels:[{innerText:'Most Recent'}]},
      {name:'csrf_token',value:'EXCLUDED_TOKEN',labels:[]},
    ] : [];
    const result=captureEgyptBoardDOM({source:'tanqeeb'});
    assert.match(result.html,/data-country="Egypt"/);
    assert.match(result.html,/data-filter-value="2"/);
    assert.match(result.html,/most_recent/);
    assert.ok(!result.html.includes('EXCLUDED_TOKEN'));
    synthetic.document.querySelector=()=>({value:'113',textContent:'Other'});
    assert.throws(()=>captureEgyptBoardDOM({source:'tanqeeb'}),/selected Egypt/);
  });
});

test('Forasna public JobPosting metadata preserves exact dates/units/country and excludes contacts', () => {
  withDocument('https://forasna.com/job/p/constructed-100001', synthetic => {
    const posting = {
      '@type':'JobPosting', identifier:{value:'100001'},
      datePosted:'2026-10-05T19:13:21+03:00', validThrough:'2026-11-03T19:13:21+02:00',
      description:'Constructed description </script> remains data',
      jobLocationType:'TELECOMMUTE', applicantLocationRequirements:{name:'Constructed other country',email:'EXCLUDED'},
      baseSalary:{currency:'EGP',value:{minValue:1500,maxValue:2500,unitText:'MONTH',account:'EXCLUDED'}},
      hiringOrganization:{name:'Constructed company',contactPoint:{email:'EXCLUDED'}},
      cookies:'EXCLUDED',
    };
    synthetic.document.querySelectorAll = selector => selector === 'script[type="application/ld+json"]'
      ? [{textContent:JSON.stringify({'@graph':[{'@type':'WebSite',token:'EXCLUDED'},posting]})}] : [];
    const result = captureEgyptBoardDOM({source:'forasna',kind:'detail'});
    const raw = result.html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
    const retained = JSON.parse(raw);
    assert.equal(retained.identifier.value,'100001');
    assert.equal(retained.datePosted,posting.datePosted);
    assert.equal(retained.baseSalary.value.unitText,'MONTH');
    assert.equal(retained.applicantLocationRequirements.name,'Constructed other country');
    assert.equal(retained.description,posting.description);
    assert.ok(!result.html.includes('EXCLUDED'));
    assert.ok(!raw.includes('</script>'));
  });
});

test('Forasna unrelated or mismatched structured postings cannot certify canonical detail', () => {
  for (const postings of [
    {'@type':'JobPosting',identifier:{value:'100002'}},
    [{'@type':'JobPosting',identifier:{value:'100001'}},{'@type':'JobPosting',identifier:{value:'100002'}}],
  ]) withDocument('https://forasna.com/job/p/constructed-100001', synthetic => {
    synthetic.document.querySelectorAll = selector => selector === 'script[type="application/ld+json"]'
      ? [{textContent:JSON.stringify(postings)}] : [];
    assert.throws(()=>captureEgyptBoardDOM({source:'forasna',kind:'detail'}),/identity mismatch/);
  });
});
