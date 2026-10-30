import {fileURLToPath} from 'node:url';
import {runNativeReader} from '../../../shared/public-sources/native-reader.mjs';

const script = fileURLToPath(new URL('../discovery/reader.py', import.meta.url));
const allowed = {
  meinpraktikum_inventory: ['scope', 'page', 'personal_noncommercial_use'],
  meinpraktikum_detail: ['url', 'personal_noncommercial_use'],
  organisation_directory: ['directory', 'page', 'personal_noncommercial_use'],
  handwerk_inventory: ['scope', 'postal_code', 'radius_km', 'page', 'first_native_pages', 'personal_noncommercial_use'],
  handwerk_detail: ['url', 'personal_noncommercial_use'],
};
const limited = error => ({status: 'source_limited', source: 'german_discovery', error,
  returned_count: null, source_result_count: null, coverage_complete: false,
  full_posting_reviewed: false, reviewed_by_model: false});
export function runDiscovery(argv, options = {}) {
  const directory = argv[argv.indexOf('--directory') + 1];
  const source = argv[0].startsWith('hand_') ? 'handwerk' : argv[0] === 'organisation_directory'
    ? (directory === 'higher_education' ? 'hochschulkompass' : 'gvp_staffing')
    : 'meinpraktikum';
  return runNativeReader(script, argv, {...options, source, countField: 'returned_count', timeoutMs: 70000});
}
export async function germanDiscovery(name, args = {}, {run = runDiscovery} = {}) {
  if (!Object.hasOwn(allowed, name) || !args || typeof args !== 'object' || Array.isArray(args)
      || Object.keys(args).some(key => !allowed[name].includes(key))
      || args.personal_noncommercial_use !== true) return limited('invalid_read_arguments_or_personal_use_not_acknowledged');
  const page = args.page === undefined ? 1 : args.page;
  if (!Number.isInteger(page) || page < 1 || page > 10000) return limited('invalid_native_page');
  let argv;
  if (name === 'handwerk_inventory') {
    const radius = args.radius_km === undefined ? 25 : args.radius_km;
    if (!['internships', 'apprenticeships'].includes(args.scope)
        || typeof args.postal_code !== 'string' || !/^[0-9]{5}$/.test(args.postal_code)
        || !Number.isInteger(radius) || radius < 1 || radius > 1000) return limited('invalid_native_handwerk_scope');
    if ((page === 1 && args.first_native_pages !== undefined)
        || (page > 1 && (!Number.isInteger(args.first_native_pages)
          || args.first_native_pages < page || args.first_native_pages > 10000))) return limited('unqualified_native_page_ceiling');
    argv = ['hand_inventory', '--scope', args.scope, '--postal-code', args.postal_code,
      '--radius-km', String(radius), '--page', String(page)];
    if (page > 1) argv.push('--first-native-pages', String(args.first_native_pages));
  } else if (name === 'handwerk_detail') {
    if (typeof args.url !== 'string' || !args.url.length || args.url.length > 4096) return limited('invalid_native_advert_url');
    argv = ['hand_detail', '--url', args.url];
  } else if (name === 'meinpraktikum_inventory') {
    if (!['internships', 'working_student'].includes(args.scope)) return limited('unknown_native_scope');
    argv = ['mein_inventory', '--scope', args.scope, '--page', String(page)];
  } else if (name === 'meinpraktikum_detail') {
    if (typeof args.url !== 'string' || !args.url.length || args.url.length > 4096) return limited('invalid_native_advert_url');
    argv = ['mein_detail', '--url', args.url];
  } else {
    if (!['higher_education', 'staffing_members'].includes(args.directory)
        || (args.directory === 'higher_education' && page !== 1)) return limited('unknown_directory_or_file_pagination');
    argv = ['organisation_directory', '--directory', args.directory, '--page', String(page)];
  }
  return run([...argv, '--personal-noncommercial-use']);
}
