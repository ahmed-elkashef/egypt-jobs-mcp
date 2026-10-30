import {fileURLToPath} from 'node:url';
import {runNativeReader} from './native-reader.mjs';

const script = fileURLToPath(new URL('../oracle/reader.py', import.meta.url));
const annotations = {readOnlyHint: true, destructiveHint: false, openWorldHint: true};
const inventoryProperties = {
  board_url: {type: 'string', maxLength: 2048, description: 'Exact independently qualified external career site from capabilities.'},
  country: {type: 'string', enum: ['DE'], description: 'Optional qualified native Germany location partition. Omit for the complete site.'},
  page: {type: 'integer', minimum: 1, maximum: 10000},
  first_page_total: {type: 'integer', minimum: 0, maximum: 1000000, description: 'Frozen native TotalJobsCount from the first page; required for continuation.'},
};
export const oracleTools = [
  {
    name: 'oracle_capabilities',
    description: 'Offline original Oracle Candidate Experience list/detail contracts, qualified external sites and explicit source limits.',
    inputSchema: {type: 'object', properties: {}, additionalProperties: false},
    annotations: {...annotations, openWorldHint: false},
  },
  {
    name: 'oracle_inventory',
    description: 'Read one complete native whole-site or Germany inventory page. Reconcile the inner job total and offset; the outer search-container count is not the job count. No role, date, candidate or department filter.',
    inputSchema: {type: 'object', properties: inventoryProperties, required: ['board_url'], additionalProperties: false},
    annotations,
  },
  {
    name: 'oracle_detail',
    description: 'Read an exact public posting from a qualified Oracle external site. Preserve full public description sections, locations, distinct job/requisition IDs and raw dates/contracts. Internal descriptions and application controls are not exported.',
    inputSchema: {type: 'object', properties: {job_url: {type: 'string', maxLength: 4096}}, required: ['job_url'], additionalProperties: false},
    annotations,
  },
];
const limited = error => ({
  status: 'source_limited', source: 'oracle', returned_count: null,
  source_result_count: null, error, coverage_complete: false, reviewed_by_model: false,
});
export function runOracle(argv, options = {}) {
  return runNativeReader(script, argv, {...options, source: 'oracle', countField: 'returned_count', timeoutMs: 55000});
}
export async function oracle(name, args = {}, {run = runOracle} = {}) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return limited('invalid_read_arguments');
  if (name === 'oracle_capabilities') {
    return Object.keys(args).length ? limited('invalid_read_arguments') : run(['--capabilities']);
  }
  if (name === 'oracle_detail') {
    if (Object.keys(args).some(key => key !== 'job_url') || typeof args.job_url !== 'string'
        || !args.job_url.length || args.job_url.length > 4096) return limited('invalid_read_arguments');
    return run(['--job-url', args.job_url]);
  }
  if (name !== 'oracle_inventory' || Object.keys(args).some(key => !Object.hasOwn(inventoryProperties, key))
      || typeof args.board_url !== 'string' || !args.board_url.length || args.board_url.length > 2048
      || args.country !== undefined && args.country !== 'DE'
      || args.page !== undefined && (!Number.isSafeInteger(args.page) || args.page < 1 || args.page > 10000)
      || args.first_page_total !== undefined && (!Number.isSafeInteger(args.first_page_total) || args.first_page_total < 0 || args.first_page_total > 1000000)
      || (args.page ?? 1) > 1 && args.first_page_total === undefined) return limited('invalid_read_arguments');
  const argv = ['--board-url', args.board_url];
  if (args.country !== undefined) argv.push('--country', args.country);
  if (args.page !== undefined) argv.push('--page', String(args.page));
  if (args.first_page_total !== undefined) argv.push('--first-page-total', String(args.first_page_total));
  return run(argv);
}
