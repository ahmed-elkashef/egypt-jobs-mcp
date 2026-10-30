import {fileURLToPath} from 'node:url';
import {runNativeReader} from './native-reader.mjs';

const script = fileURLToPath(new URL('../personio/reader.py', import.meta.url));
export const personioTools = [{
  name: 'personio_detail',
  description: 'Read an exact verified Personio primary advert. Preserve complete primary public HTML/text, separate About us context, native sections/header and source JobPosting projection. XML can omit company context or translations. No account, form, script, media, application or contact request; no original-clock, working-language or applicant-fit inference.',
  inputSchema: {type: 'object', properties: {job_url: {type: 'string', maxLength: 4096}}, required: ['job_url'], additionalProperties: false},
  annotations: {readOnlyHint: true, destructiveHint: false, openWorldHint: true},
}];
const limited = error => ({status: 'source_limited', source: 'personio', returned_count: null, source_result_count: null,
  error, coverage_complete: false, reviewed_by_model: false});
export function runPersonio(argv, options = {}) {
  return runNativeReader(script, argv, {...options, source: 'personio', countField: 'returned_count', timeoutMs: 55000});
}
export async function personio(name, args = {}, {run = runPersonio} = {}) {
  if (name !== 'personio_detail' || !args || typeof args !== 'object' || Array.isArray(args)
      || Object.keys(args).some(key => key !== 'job_url') || typeof args.job_url !== 'string'
      || !args.job_url.length || args.job_url.length > 4096) return limited('invalid_read_arguments');
  return run(['--job-url', args.job_url]);
}
