/**
 * Read selected public DOM sections through the operator-authorized browser.
 * Paste this function into your browser tool’s read-only DOM evaluator; it has no dependencies,
 * network calls, storage/cookie reads, hidden application state or UI actions.
 * Never run it on account pages. HTTP fetches remain a separate transport.
 */
export function captureEgyptBoardDOM({source, kind = 'page'}) {
  const hosts = {wuzzuf:'wuzzuf.net',forasna:'forasna.com',arabjobs:'www.arabjobs.com'};
  if (!hosts[source] || document.location.hostname !== hosts[source]) throw Error('Wrong public board');
  if (!['page','detail'].includes(kind)) throw Error('Wrong capture kind');
  // Validate scope before reading any page content, including its title/header.
  // Use only the visible URL string so constrained DOM evaluators work too.
  const root = 'https://' + hosts[source];
  const href = document.location.href;
  if (!href.startsWith(root + '/') || href.includes('#')) throw Error('Canonical HTTPS public URL required');
  const components = href.slice(root.length).split('?');
  if (components.length > 2) throw Error('Invalid public URL');
  const [pathname, query = ''] = components;
  if (kind === 'detail') {
    const patterns = {
      wuzzuf:/^\/jobs\/p\/[a-z0-9]{12}-[^/]+$/,
      forasna:/^\/job\/p\/[^/]+-\d+$/,
      arabjobs:/^\/en\/jobs\/j\/[^/]+\/[^/]+\/\d+$/,
    };
    if (components.length !== 1 || !patterns[source].test(pathname)) throw Error('Canonical public detail URL required');
  } else {
    const paths = {
      wuzzuf:/^\/search\/jobs$/,
      forasna:/^\/(?:وظائف-خالية|%D9%88%D8%B8%D8%A7%D8%A6%D9%81-%D8%AE%D8%A7%D9%84%D9%8A%D8%A9)$/i,
      arabjobs:/^\/en\/jobs\/search\/$/,
    };
    if (!paths[source].test(pathname)) throw Error('Canonical public inventory URL required');
    const params = {};
    for (const pair of query ? query.split('&') : []) {
      const parts = pair.split('=');
      const key = parts[0].replace(/%5B/gi,'[').replace(/%5D/gi,']');
      if (parts.length !== 2 || Object.prototype.hasOwnProperty.call(params,key)) throw Error('Invalid or duplicate source filter');
      params[key] = parts[1];
    }
    const allowed = {
      wuzzuf:['filters[country][0]','filters[job_types][0]','start'],
      forasna:['start'],
      arabjobs:['filterJobCountry','sortType','pageIndex'],
    }[source];
    if (Object.keys(params).some(key=>!allowed.includes(key))) throw Error('Only geography/native employment/pagination filters are allowed');
    if (source === 'wuzzuf' && (params['filters[country][0]'] !== 'Egypt' ||
        (params['filters[job_types][0]'] !== undefined && !['full_time','part_time','freelance_project','internship','shift_based','volunteering'].includes(params['filters[job_types][0]'])))) throw Error('Egypt/native employment scope required');
    if (source === 'arabjobs' && (params.filterJobCountry !== 'EG' ||
        (params.sortType !== undefined && params.sortType !== '2'))) throw Error('Egypt/newest-first scope required');
    for (const key of ['start','pageIndex']) {
      if (params[key] !== undefined && (!/^\d+$/.test(params[key]) || Number(params[key]) > 200000)) throw Error('Invalid source pagination');
    }
  }
  const escape = value => String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  const attributes = ['class','href','title','datetime','aria-label','aria-current'];
  const serialize = node => {
    if (node.nodeType === 3) return escape(node.nodeValue || '');
    if (node.nodeType !== 1 || ['SCRIPT','STYLE','META','FORM','INPUT','IFRAME','IMG','SVG'].includes(node.tagName)) return '';
    if (node.hidden || node.getAttribute('aria-hidden') === 'true' || node.style.display === 'none' || !node.getClientRects().length) return '';
    const tag=node.tagName.toLowerCase();
    const attrs=attributes.filter(a=>node.hasAttribute(a)).map(a=>` ${a}="${escape(node.getAttribute(a))}"`).join('');
    return `<${tag}${attrs}>${Array.from(node.childNodes).map(serialize).join('')}</${tag}>`;
  };
  let nodes = [];
  if (kind === 'page') {
    if (source === 'wuzzuf') nodes = [
      ...Array.from(document.querySelectorAll('h2 a[href*="/jobs/p/"]')).map(a=>a.parentElement.parentElement.parentElement),
      ...document.querySelectorAll('nav[aria-label="Pagination"]'),
    ];
    if (source === 'forasna') nodes = [
      ...Array.from(document.querySelectorAll('h2.job-title a')).map(a=>a.closest('.item-details')),
      ...document.querySelectorAll('.search-jobs-count'),
      ...document.querySelectorAll('ul.pagination'),
    ];
    if (source === 'arabjobs') nodes = [
      ...Array.from(document.querySelectorAll('h3 a[href*="/en/jobs/j/"]')).map(a=>a.parentElement.parentElement),
      ...document.querySelectorAll('#pager'),
    ];
  } else {
    const names = {
      wuzzuf:['Job Details','Job Description','Job Requirements'],
      forasna:['متطلبات الوظيفة','الراتب ونوع العمل','مميزات الوظيفة','تفاصيل الوظيفة'],
      arabjobs:['Job Description','Job Requirements'],
    }[source];
    const title=document.querySelector('h1');
    const header=title ? (source === 'forasna' ? title.parentElement.parentElement : title.parentElement) : null;
    nodes = [];
    for (const heading of document.querySelectorAll('h2,h3,div.panel-heading')) {
      if (!names.includes(heading.innerText.trim())) continue;
      nodes.push(source === 'forasna' ? heading.parentElement.parentElement : heading.parentElement);
    }
    const headerHTML=header ? '<header data-public-source-header>'+serialize(header)+'</header>' : '';
    const notice=(document.body.innerText.match(/©[^\n]*(?:\n[^\n]*){0,2}/) || [''])[0];
    // A public JSON-LD JobPosting is DOM source evidence, not hidden app state.
    // Retain only this detail's job fields. Never copy scripts, account/contact
    // properties, application forms, tracking payloads or arbitrary nested data.
    let structuredHTML = '';
    if (source === 'forasna') {
      const fields = {
        '@type':{}, title:{}, description:{}, url:{},
        identifier:{'@type':{},name:{},value:{}}, datePosted:{}, validThrough:{}, employmentType:{},
        hiringOrganization:{'@type':{},name:{},sameAs:{}}, jobLocationType:{},
        applicantLocationRequirements:{'@type':{},name:{}},
        jobLocation:{'@type':{},address:{'@type':{},addressRegion:{},addressCountry:{}}},
        baseSalary:{'@type':{},currency:{},value:{'@type':{},value:{},minValue:{},maxValue:{},unitText:{}}},
      };
      const select = (value, allowed) => {
        if (Array.isArray(value)) return value.map(v=>select(v,allowed));
        if (value === null || typeof value !== 'object') return value;
        const selected = {};
        for (const key of Object.keys(allowed)) if (Object.prototype.hasOwnProperty.call(value,key)) selected[key]=select(value[key],allowed[key]);
        return selected;
      };
      const postings=[];
      const walk=value=>{
        if (Array.isArray(value)) value.forEach(walk);
        else if (value && typeof value === 'object') {
          if (value['@type']==='JobPosting') postings.push(value);
          if (value['@graph']) walk(value['@graph']);
        }
      };
      for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
        try { walk(JSON.parse(script.textContent)); } catch { /* malformed metadata does not invent a posting */ }
      }
      if (postings.length) {
        const expectedID=pathname.match(/-(\d+)$/)[1];
        if (postings.length !== 1 || String(postings[0].identifier?.value) !== expectedID) throw Error('JobPosting/canonical detail identity mismatch');
        structuredHTML='<script type="application/ld+json">'+JSON.stringify(select(postings[0],fields)).replace(/</g,'\\u003c')+'</script>';
      }
    }
    return {
      url:document.location.href,kind,captured_at:new Date().toISOString(),
      html:'<html><body>'+headerHTML+Array.from(new Set(nodes.filter(Boolean))).map(serialize).join('\n')+structuredHTML+'<footer data-source-notice>'+escape(notice)+'</footer></body></html>',
    };
  }
  return {
    url:document.location.href,kind,captured_at:new Date().toISOString(),
    html:'<html><body>'+Array.from(new Set(nodes.filter(Boolean))).map(serialize).join('\n')+'<footer data-source-notice>'+escape((document.body.innerText.match(/©[^\n]*(?:\n[^\n]*){0,2}/) || [''])[0])+'</footer></body></html>',
  };
}
