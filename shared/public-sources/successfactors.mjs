import {fileURLToPath} from 'node:url';
import {runNativeReader} from './native-reader.mjs';

const script = fileURLToPath(new URL('../successfactors/reader.py', import.meta.url));
const annotations = {readOnlyHint: true, destructiveHint: false, openWorldHint: true};
const inventoryProperties = {
  board_url: {type: 'string', maxLength: 2048, description: 'Exact independently verified legacy RMK search URL from capabilities.'},
  country: {type: 'string', enum: ['DE', 'EG'], description: 'Optional qualified native country partition. Omit for the whole legacy board.'},
  page: {type: 'integer', minimum: 1, maximum: 10000},
  first_page_total: {type: 'integer', minimum: 0, maximum: 1000000, description: 'Frozen native first-page total; required for every continuation.'},
};
export const successfactorsTools = [
  {
    name: 'successfactors_capabilities',
    description: 'Offline original SAP RMK list/detail contracts and qualified origins. The separately discovered modern SAP front remains a separate unimplemented transport.',
    inputSchema: {type: 'object', properties: {}, additionalProperties: false},
    annotations: {...annotations, openWorldHint: false},
  },
  {
    name: 'successfactors_inventory',
    description: 'Read a complete native RMK page with native range, row, country, sort and advertised continuation reconciliation. No role/department/career-status selection. A current employer partition is not historical or national coverage.',
    inputSchema: {type: 'object', properties: inventoryProperties, required: ['board_url'], additionalProperties: false},
    annotations,
  },
  {
    name: 'successfactors_detail',
    description: 'Read an exact returned RMK posting URI and preserve its complete primary description, full job display, distinct URL-site/requisition identities and raw contract/date fields. No account, alert or application operation.',
    inputSchema: {type: 'object', properties: {job_url: {type: 'string', maxLength: 4096}}, required: ['job_url'], additionalProperties: false},
    annotations,
  },
];
const limited = error => ({
  status: 'source_limited', source: 'successfactors', returned_count: null,
  source_result_count: null, error, coverage_complete: false, reviewed_by_model: false,
});
export function runSuccessfactors(argv, options = {}) {
  return runNativeReader(script, argv, {...options, source: 'successfactors', countField: 'returned_count', timeoutMs: 55000});
}
export async function successfactors(name, args = {}, {run = runSuccessfactors} = {}) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return limited('invalid_read_arguments');
  if (name === 'successfactors_capabilities') {
    return Object.keys(args).length ? limited('invalid_read_arguments') : run(['--capabilities']);
  }
  if (name === 'successfactors_detail') {
    if (Object.keys(args).some(key => key !== 'job_url') || typeof args.job_url !== 'string'
        || !args.job_url.length || args.job_url.length > 4096) return limited('invalid_read_arguments');
    return run(['--job-url', args.job_url]);
  }
  if (name !== 'successfactors_inventory' || Object.keys(args).some(key => !Object.hasOwn(inventoryProperties, key))
      || typeof args.board_url !== 'string' || !args.board_url.length || args.board_url.length > 2048
      || args.country !== undefined && !['DE', 'EG'].includes(args.country)
      || args.page !== undefined && (!Number.isSafeInteger(args.page) || args.page < 1 || args.page > 10000)
      || args.first_page_total !== undefined && (!Number.isSafeInteger(args.first_page_total) || args.first_page_total < 0 || args.first_page_total > 1000000)
      || (args.page ?? 1) > 1 && args.first_page_total === undefined) return limited('invalid_read_arguments');
  const argv = ['--board-url', args.board_url];
  if (args.country !== undefined) argv.push('--country', args.country);
  if (args.page !== undefined) argv.push('--page', String(args.page));
  if (args.first_page_total !== undefined) argv.push('--first-page-total', String(args.first_page_total));
  return run(argv);
}
