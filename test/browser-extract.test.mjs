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
    ['forasna', 'detail', 'https://forasna.com/job/p/constructed-%2F-example-100001'],
    ['arabjobs', 'page', 'https://www.arabjobs.com/en/jobs/search/?pageIndex=2&filterJobCountry=EG&sortType=2'],
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
