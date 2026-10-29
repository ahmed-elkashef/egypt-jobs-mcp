import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { registerJobs, JobsClient, READ_ONLY } from './jobs.js';
import { registerEntgeltatlasTools } from '../vendor/greyt-1.0.0/dist/tools/entgeltatlas.js';
import { registerAusbildungTools } from '../vendor/greyt-1.0.0/dist/tools/ausbildung.js';
import { registerStudiumTools } from '../vendor/greyt-1.0.0/dist/tools/studium.js';
import { registerWeiterbildungTools } from '../vendor/greyt-1.0.0/dist/tools/weiterbildung.js';
import { registerCoachingTools } from '../vendor/greyt-1.0.0/dist/tools/coaching.js';
import { EntgeltatlasClient } from '../vendor/greyt-1.0.0/dist/clients/entgeltatlas.js';
import { AusbildungClient } from '../vendor/greyt-1.0.0/dist/clients/ausbildung.js';
import { StudiumClient } from '../vendor/greyt-1.0.0/dist/clients/studium.js';
import { WeiterbildungClient } from '../vendor/greyt-1.0.0/dist/clients/weiterbildung.js';
import { CoachingClient } from '../vendor/greyt-1.0.0/dist/clients/coaching.js';

export function createServer(overrides = {}) {
  const clients = { jobsuche: new JobsClient(), entgeltatlas: new EntgeltatlasClient(),
    ausbildung: new AusbildungClient(), studium: new StudiumClient(),
    weiterbildung: new WeiterbildungClient(), coaching: new CoachingClient(), ...overrides };
  const server = new McpServer({ name: 'german-arbeitsmarkt', version: '1.1.0' }, {
    instructions: 'Read-only German labour-market source tools. Jobs preserve structured source records and pagination evidence. Six tool families are retained. Source retrieval and reported totals do not prove candidate fit, eligibility, complete market coverage or a frozen publication interval.',
  });
  registerJobs(server, clients.jobsuche);
  // Retain the five other upstream families, with explicit read-only annotations
  // and actual MCP error flags for their legacy error-text responses.
  const legacy = { tool(name, description, inputSchema, callback) {
    return server.registerTool(name, { description, inputSchema, annotations: READ_ONLY }, async input => {
      try {
        const result = await callback(input);
        const errored = result.content?.some(item => item.type === 'text' && /^Fehler\b/.test(item.text));
        return errored ? { ...result, isError: true } : result;
      } catch (error) {
        return { isError: true, content: [{ type: 'text', text: error instanceof Error ? error.message : String(error) }] };
      }
    });
  } };
  registerEntgeltatlasTools(legacy, clients.entgeltatlas);
  registerAusbildungTools(legacy, clients.ausbildung);
  registerStudiumTools(legacy, clients.studium);
  registerWeiterbildungTools(legacy, clients.weiterbildung);
  registerCoachingTools(legacy, clients.coaching);
  return server;
}
