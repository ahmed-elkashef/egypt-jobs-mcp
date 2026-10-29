#!/usr/bin/env node
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { EntgeltatlasClient } from "./clients/entgeltatlas.js";
import { JobsucheClient } from "./clients/jobsuche.js";
import { AusbildungClient } from "./clients/ausbildung.js";
import { StudiumClient } from "./clients/studium.js";
import { WeiterbildungClient } from "./clients/weiterbildung.js";
import { CoachingClient } from "./clients/coaching.js";
import { createServer } from "./server.js";
const clients = {
    entgeltatlas: new EntgeltatlasClient(),
    jobsuche: new JobsucheClient(),
    ausbildung: new AusbildungClient(),
    studium: new StudiumClient(),
    weiterbildung: new WeiterbildungClient(),
    coaching: new CoachingClient(),
};
const server = createServer(clients);
const transport = new StdioServerTransport();
await server.connect(transport);
//# sourceMappingURL=index.js.map