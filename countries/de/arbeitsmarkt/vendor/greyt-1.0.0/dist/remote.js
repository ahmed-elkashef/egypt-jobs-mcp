#!/usr/bin/env node
/**
 * Remote MCP server for German Arbeitsmarkt APIs.
 * Runs as HTTP server with StreamableHTTP transport.
 * No OAuth needed — all APIs use server-side API keys.
 */
import { randomUUID } from "node:crypto";
import { createServer as createHttpServer } from "node:http";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { EntgeltatlasClient } from "./clients/entgeltatlas.js";
import { JobsucheClient } from "./clients/jobsuche.js";
import { AusbildungClient } from "./clients/ausbildung.js";
import { StudiumClient } from "./clients/studium.js";
import { WeiterbildungClient } from "./clients/weiterbildung.js";
import { CoachingClient } from "./clients/coaching.js";
import { createServer } from "./server.js";
const sessions = new Map();
// Clients are initialized once at server start (no per-user credentials needed)
const clients = {
    entgeltatlas: new EntgeltatlasClient(),
    jobsuche: new JobsucheClient(),
    ausbildung: new AusbildungClient(),
    studium: new StudiumClient(),
    weiterbildung: new WeiterbildungClient(),
    coaching: new CoachingClient(),
};
async function parseBody(req) {
    return new Promise((resolve, reject) => {
        let data = "";
        req.on("data", (chunk) => (data += chunk.toString()));
        req.on("end", () => resolve(data));
        req.on("error", reject);
    });
}
const httpServer = createHttpServer(async (req, res) => {
    const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "localhost"}`);
    const path = url.pathname;
    // CORS headers
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, mcp-session-id, Last-Event-ID");
    res.setHeader("Access-Control-Expose-Headers", "mcp-session-id");
    if (req.method === "OPTIONS") {
        res.writeHead(204);
        res.end();
        return;
    }
    // --- Root redirect ---
    if (path === "/") {
        res.writeHead(302, { Location: "/german-arbeitsmarkt" });
        res.end();
        return;
    }
    // --- Health check ---
    if (path === "/health") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "ok", service: "german-arbeitsmarkt-mcp", version: "1.0.0" }));
        return;
    }
    // --- MCP + Landing Page on /german-arbeitsmarkt ---
    if (path !== "/german-arbeitsmarkt") {
        res.writeHead(404);
        res.end("Not found");
        return;
    }
    // Browser GET without MCP session → redirect to marketing page
    if (req.method === "GET" && !req.headers["mcp-session-id"]) {
        const accept = req.headers.accept ?? "";
        if (accept.includes("text/html") || (!accept.includes("application/json") && !accept.includes("text/event-stream"))) {
            res.writeHead(302, { Location: "https://business-os.de/apps/german-arbeitsmarkt-mcp" });
            res.end();
            return;
        }
    }
    // --- MCP protocol handler ---
    const sessionId = req.headers["mcp-session-id"];
    try {
        if (req.method === "POST") {
            const body = await parseBody(req);
            const parsed = JSON.parse(body);
            if (sessionId && sessions.has(sessionId)) {
                const session = sessions.get(sessionId);
                await session.transport.handleRequest(req, res, parsed);
                return;
            }
            if (!sessionId && isInitializeRequest(parsed)) {
                const server = createServer(clients);
                const transport = new StreamableHTTPServerTransport({
                    sessionIdGenerator: () => randomUUID(),
                    onsessioninitialized: (sid) => {
                        console.log(`Session initialized: ${sid}`);
                        sessions.set(sid, { transport, server });
                    },
                });
                transport.onclose = () => {
                    const sid = transport.sessionId;
                    if (sid) {
                        console.log(`Session closed: ${sid}`);
                        sessions.delete(sid);
                    }
                };
                await server.connect(transport);
                await transport.handleRequest(req, res, parsed);
                return;
            }
            res.writeHead(400, { "Content-Type": "application/json" });
            res.end(JSON.stringify({
                jsonrpc: "2.0",
                error: { code: -32000, message: "Bad Request: No valid session ID" },
                id: null,
            }));
        }
        else if (req.method === "GET") {
            if (!sessionId || !sessions.has(sessionId)) {
                res.writeHead(400);
                res.end("Invalid or missing session ID");
                return;
            }
            await sessions.get(sessionId).transport.handleRequest(req, res);
        }
        else if (req.method === "DELETE") {
            if (!sessionId || !sessions.has(sessionId)) {
                res.writeHead(400);
                res.end("Invalid or missing session ID");
                return;
            }
            await sessions.get(sessionId).transport.handleRequest(req, res);
        }
        else {
            res.writeHead(405);
            res.end("Method not allowed");
        }
    }
    catch (error) {
        console.error("Error handling request:", error);
        if (!res.headersSent) {
            res.writeHead(500, { "Content-Type": "application/json" });
            res.end(JSON.stringify({
                jsonrpc: "2.0",
                error: { code: -32603, message: "Internal server error" },
                id: null,
            }));
        }
    }
});
const PORT = parseInt(process.env.PORT ?? "8080", 10);
httpServer.listen(PORT, () => {
    console.log(`German Arbeitsmarkt MCP server listening on port ${PORT}`);
    console.log(`MCP endpoint: http://localhost:${PORT}/german-arbeitsmarkt`);
});
//# sourceMappingURL=remote.js.map