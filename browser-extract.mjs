/**
 * Read selected public DOM sections through the operator-authorized browser.
 * Paste this function into your browser tool’s read-only DOM evaluator; it has no dependencies,
 * network calls, storage/cookie reads, hidden application state or UI actions.
 * Never run it on account pages. HTTP fetches remain a separate transport.
 */
export function captureEgyptBoardDOM({source, kind = 'page'}) {
  if (source === 'tanqeeb' || source === 'akhtaboot') {
    // Only selected public DOM and explicitly allowlisted native controls.
    // Do not copy forms, hidden inputs, CSRF metadata or account state.
    const expectedHost = source === 'tanqeeb' ? 'egypt.tanqeeb.com' : 'www.akhtaboot.com';
    const current = new URL(document.location.href);
    // Native disclosure anchors do not change the provider inventory request.
    if (source==='tanqeeb' && kind==='page' && ['#order-by-wrap','#job-type-wrap'].includes(current.hash)) current.hash='';
    if (current.protocol !== 'https:' || current.hostname !== expectedHost || current.port || current.username || current.password || current.hash || !['page','detail'].includes(kind)) throw Error('Canonical public board URL required');
    if (source === 'tanqeeb') {
      if (kind === 'detail') {
        if (!/^\/jobs-in-(?:egypt|middle-east)\/all\/jobs\/0?\d+\.html$/.test(current.pathname) || current.search) throw Error('Canonical Tanqeeb detail required');
      } else {
        if (!/^\/jobs\/search(?:\/page\/[1-9]\d*)?$/.test(current.pathname)) throw Error('Canonical Tanqeeb Egypt inventory required');
        const allowed = new Set(['keywords','country','state','lang','order_by']);
        for (const [key] of current.searchParams) if (!allowed.has(key) || current.searchParams.getAll(key).length !== 1) throw Error('Unsupported or repeated Tanqeeb filter');
        if (current.searchParams.get('country') !== '213' || (current.searchParams.get('keywords') || '') !== '' || !['0',null].includes(current.searchParams.get('state')) || !['all',null].includes(current.searchParams.get('lang')) || !['most_recent',null].includes(current.searchParams.get('order_by'))) throw Error('Blank-query whole-Egypt newest scope required');
      }
    } else if (kind === 'page') {
      if (current.pathname !== '/en/egypt/jobs' || current.search) throw Error('Canonical Akhtaboot Egypt inventory required');
    } else {
      // Expanded only when a concrete canonical public route is verified.
      if (!/^\/en\/egypt\/jobs\/[^/]+\/\d+-[^/]+$/.test(current.pathname) || current.search) throw Error('Canonical Akhtaboot Egypt detail required');
    }
    const escape = value => String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    const allowedAttributes=['id','class','href','title','datetime','aria-label','aria-current','aria-disabled','data-job-id','data-job-type','data-job-closed','data-job-country'];
    const serialize = node => {
      if (node.nodeType === 3) return escape(node.nodeValue || '');
      if (node.nodeType !== 1 || ['SCRIPT','STYLE','META','FORM','INPUT','IFRAME','IMG','SVG','BUTTON'].includes(node.tagName)) return '';
      if (node.matches?.('.social,.strip-social')) return '';
      if (node.hidden || node.getAttribute('aria-hidden') === 'true' || node.style.display === 'none' || !node.getClientRects().length) return '';
      const tag=node.tagName.toLowerCase();
      return `<${tag}${allowedAttributes.filter(a=>node.hasAttribute(a)).map(a=>` ${a}="${escape(node.getAttribute(a))}"`).join('')}>${Array.from(node.childNodes).map(serialize).join('')}</${tag}>`;
    };
    let sections='';
    if (source === 'tanqeeb' && kind === 'page') {
      const country=document.querySelector('select#countryHeader[name="country"] option:checked');
      if (!country || country.value !== '213' || country.textContent.trim() !== 'Egypt') throw Error('Visible selected Egypt control required');
      const names = new Set(['refine[job_types][]','refine[workplaces][]','refine[search_period]','refine[order_by]']);
      const controls = Array.from(document.querySelectorAll('input:checked,select option:checked')).filter(node=>names.has(node.name || node.parentElement?.name));
      sections='<section data-public-native-filters data-country="Egypt">'+controls.map(node=>{
        const name=node.name || node.parentElement.name;
        const label=node.labels?.[0]?.innerText || node.textContent || '';
        return `<span data-filter-name="${escape(name)}" data-filter-value="${escape(node.value)}">${escape(label.trim())}</span>`;
      }).join('')+'</section>';
      sections += '<section id="jobs_list">'+Array.from(document.querySelectorAll('article[data-job-id]')).map(serialize).join('')+'</section>';
      sections += Array.from(document.querySelectorAll('[aria-label="Search Results Navigation"],.jobs-results-col > h1,.jobs-results-count')).map(serialize).join('');
    } else if (kind === 'page') {
      // Scope marker is selected public search geography, never the default
      // All Countries selector. Read only its exact country value.
      const country=document.querySelector('#filter_form input[name="search[cp_country_name][vals][]"]');
      if (!country || country.value !== 'Egypt') throw Error('Akhtaboot Egypt search scope required');
      sections='<section data-public-native-filters data-country="Egypt"></section>';
      sections+=Array.from(document.querySelectorAll('#current_page,.error_message,.pagination')).map(serialize).join('');
      sections+=Array.from(new Set(Array.from(document.querySelectorAll('a.job-link')).map(node=>node.closest('.row')).filter(Boolean))).map(serialize).join('');
    } else {
      const title=document.querySelector(source === 'tanqeeb' ? 'h3.job-title-text' : 'h1');
      if (source === 'tanqeeb') {
        const body=document.querySelector('#jobDescriptionBody');
        if (!title || !body) throw Error('Verified public title and actual job-description section required');
        sections='<h1 data-public-source-title>'+escape(title.innerText.trim())+'</h1><section data-public-job-description>'+serialize(body)+'</section>';
      } else {
        const blocks=Array.from(document.querySelectorAll('.description-list dl'));
        if (!blocks.some(block=>Array.from(block.querySelectorAll('dt')).some(dt=>dt.innerText.trim()==='Job Description and Requirements'))) throw Error('Actual Akhtaboot task description required');
        const labels=new Set(['Job Description and Requirements','Company:','Industry:','Job Location:','Career Level:','Date Posted:','Ref. Number:','Citizenships','Residence Country','Employment Type:','Job Type:','Salary:']);
        sections=(title ? serialize(title) : '')+blocks.map(block=>'<div class="description-list"><dl>'+Array.from(block.querySelectorAll('dt')).filter(dt=>labels.has(dt.innerText.trim())).map(dt=>serialize(dt)+(dt.nextElementSibling?.tagName==='DD' ? serialize(dt.nextElementSibling) : '')).join('')+'</dl></div>').join('');
      }
    }
    return {url:current.href,kind,captured_at:new Date().toISOString(),html:'<html><body>'+sections+'</body></html>'};
  }
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
      forasna:['start','filters[country][0]','filters[jobType][0]'],
      arabjobs:['filterJobCountry','filterJobType','sortType','pageIndex'],
    }[source];
    if (Object.keys(params).some(key=>!allowed.includes(key))) throw Error('Only geography/native employment/pagination filters are allowed');
    if (source === 'wuzzuf' && (params['filters[country][0]'] !== 'Egypt' ||
        (params['filters[job_types][0]'] !== undefined && !['full_time','part_time','freelance_project','internship','shift_based','volunteering'].includes(params['filters[job_types][0]'])))) throw Error('Egypt/native employment scope required');
    if (source === 'forasna' && (
        (params['filters[country][0]'] !== undefined && new URL(href).searchParams.get('filters[country][0]') !== 'مصر') ||
        (params['filters[jobType][0]'] !== undefined && (new URL(href).searchParams.get('filters[jobType][0]') !== 'نصف يوم' || params['filters[country][0]'] === undefined)))) throw Error('Verified Egypt/half-day Forasna scope required');
    if (source === 'arabjobs' && (params.filterJobCountry !== 'EG' ||
        (params.sortType !== undefined && params.sortType !== '2') ||
        (params.filterJobType !== undefined && !['1','2','3','4','5'].includes(params.filterJobType)))) throw Error('Egypt/newest-first/verified native employment scope required');
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
