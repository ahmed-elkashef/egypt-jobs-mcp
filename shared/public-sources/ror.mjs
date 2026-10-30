import {fileURLToPath} from 'node:url';
import {runNativeReader} from './native-reader.mjs';

const script = fileURLToPath(new URL('../ror/reader.py', import.meta.url));
const recordId = {type: 'string', pattern: '^[1-9][0-9]{3,11}$', maxLength: 12};
const annotations = {readOnlyHint: true, destructiveHint: false, openWorldHint: true};
export const rorTools = [
  {name: 'ror_release', annotations,
    description: 'Resolve the official public ROR concept to its advertised immutable record, returning any native wait deadline without following redirects. Or read an exact discovered record’s complete release metadata, count, archive and checksum. Public HTML only, no denied Zenodo API, accounts, scripts or subscriptions. Dataset metadata is not vacancy supply. Honour record_read_not_before before the next call.',
    inputSchema: {type: 'object', properties: {record_id: recordId}, additionalProperties: false}},
  {name: 'ror_directory', annotations,
    description: 'Read original complete native ROR organisation records for DE or EG from a checksum-verified immutable official full dump. Cold cache reads only the exact public release and its advertised policy-permitted ZIP; later country segments use the verified local snapshot without network. All types/statuses and native fields retained; no role/career/degree filter. Use exact next_request including archive snapshot digest. A research-organisation directory is not all employers, job worksites, vacancies, hiring, applicant eligibility or country/week completeness. Requires operator JOB_MARKET_CAPTURE_DIR.',
    inputSchema: {type: 'object', properties: {record_id: recordId, country: {type: 'string', enum: ['DE', 'EG']},
      offset: {type: 'integer', minimum: 0, maximum: 1000000, default: 0},
      limit: {type: 'integer', minimum: 1, maximum: 500, default: 200},
      snapshot_sha256: {type: 'string', pattern: '^[0-9a-f]{64}$'}}, required: ['record_id', 'country'], additionalProperties: false}},
];
const limited = error => ({status: 'source_limited', source: 'ror', organization_count: null,
  source_result_count: null, coverage_complete: false, reviewed_by_model: false, error});
export function runRor(argv, options = {}) {
  return runNativeReader(script, argv, {...options, source: 'ror', countField: 'organization_count'});
}
export async function ror(name, args = {}, {run = runRor} = {}) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return limited('invalid_ROR_arguments');
  const allowed = name === 'ror_release' ? ['record_id'] : name === 'ror_directory' ? ['record_id','country','offset','limit','snapshot_sha256'] : [];
  if (!allowed.length || Object.keys(args).some(k => !allowed.includes(k))) return limited('invalid_ROR_arguments');
  if ((args.record_id !== undefined || name === 'ror_directory')
      && (typeof args.record_id !== 'string' || !/^[1-9][0-9]{3,11}$/.test(args.record_id) || args.record_id === '6347574')) return limited('exact_version_specific_ROR_record_required');
  const argv = [name === 'ror_release' ? 'release' : 'directory'];
  if (args.record_id !== undefined) argv.push('--record-id', args.record_id);
  if (name === 'ror_directory') {
    const offset = args.offset ?? 0, limit = args.limit ?? 200;
    if (!['DE','EG'].includes(args.country) || !Number.isSafeInteger(offset) || offset < 0 || offset > 1000000
        || !Number.isSafeInteger(limit) || limit < 1 || limit > 500
        || offset > 0 && args.snapshot_sha256 === undefined
        || args.snapshot_sha256 !== undefined && (typeof args.snapshot_sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(args.snapshot_sha256))) return limited('exact_ROR_country_and_snapshot_bound_segment_required');
    argv.push('--country', args.country, '--offset', String(offset), '--limit', String(limit));
    if (args.snapshot_sha256 !== undefined) argv.push('--snapshot-sha256', args.snapshot_sha256);
  }
  return run(argv);
}
