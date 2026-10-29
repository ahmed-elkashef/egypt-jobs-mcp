import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { EntgeltatlasClient } from "./clients/entgeltatlas.js";
import { JobsucheClient } from "./clients/jobsuche.js";
import { AusbildungClient } from "./clients/ausbildung.js";
import { StudiumClient } from "./clients/studium.js";
import { WeiterbildungClient } from "./clients/weiterbildung.js";
import { CoachingClient } from "./clients/coaching.js";
export interface Clients {
    entgeltatlas: EntgeltatlasClient;
    jobsuche: JobsucheClient;
    ausbildung: AusbildungClient;
    studium: StudiumClient;
    weiterbildung: WeiterbildungClient;
    coaching: CoachingClient;
}
export declare function createServer(clients: Clients): McpServer;
