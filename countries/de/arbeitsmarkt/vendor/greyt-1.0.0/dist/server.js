import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { INSTRUCTIONS } from "./instructions.js";
import { registerEntgeltatlasTools } from "./tools/entgeltatlas.js";
import { registerJobsucheTools } from "./tools/jobsuche.js";
import { registerAusbildungTools } from "./tools/ausbildung.js";
import { registerStudiumTools } from "./tools/studium.js";
import { registerWeiterbildungTools } from "./tools/weiterbildung.js";
import { registerCoachingTools } from "./tools/coaching.js";
export function createServer(clients) {
    const server = new McpServer({ name: "german-arbeitsmarkt", version: "1.0.0" }, { instructions: INSTRUCTIONS });
    registerEntgeltatlasTools(server, clients.entgeltatlas);
    registerJobsucheTools(server, clients.jobsuche);
    registerAusbildungTools(server, clients.ausbildung);
    registerStudiumTools(server, clients.studium);
    registerWeiterbildungTools(server, clients.weiterbildung);
    registerCoachingTools(server, clients.coaching);
    return server;
}
//# sourceMappingURL=server.js.map