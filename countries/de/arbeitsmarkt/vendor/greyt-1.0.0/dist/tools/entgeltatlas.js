import { z } from "zod";
import { ArbeitsmarktApiError } from "../errors.js";
function formatError(error) {
    if (error instanceof ArbeitsmarktApiError) {
        return `Fehler bei der Entgeltatlas-API (${error.statusCode}): ${error.message}`;
    }
    return `Fehler: ${error instanceof Error ? error.message : String(error)}`;
}
export function registerEntgeltatlasTools(server, client) {
    // --- gehalt_suche ---
    server.tool("gehalt_suche", `Median-Gehälter nach Beruf (KldB-2010-Code) abfragen. Zeigt was Beschäftigte in Deutschland typischerweise verdienen, aufgeschlüsselt nach Region, Geschlecht, Alter und Branche.

WANN NUTZEN:
- Gehalt eines bestimmten Berufs nachschlagen
- Gehaltsvergleiche nach Region, Geschlecht oder Alter
- Branchenspezifische Gehälter ermitteln

HINWEIS: Nutze die KldB-Codes aus den Instructions oder frage den User nach dem Beruf.`, {
        kldb: z.string().describe("KldB-2010-Code des Berufs (3-5 Stellen, z.B. '43412' für Softwareentwicklung)"),
        l: z.number().min(1).max(4).optional().describe("Leistungsniveau: 1=Helfer, 2=Fachkraft, 3=Spezialist, 4=Experte"),
        r: z.string().optional().describe("Regionscode (1=Deutschland, 2=Ost, 3=West, 4-19=Bundesländer)"),
        g: z.number().min(1).max(3).optional().describe("Geschlecht: 1=Gesamt, 2=Männlich, 3=Weiblich"),
        a: z.number().min(1).max(4).optional().describe("Alter: 1=Alle, 2=unter 25, 3=25-54, 4=55+"),
        b: z.number().min(1).max(11).optional().describe("Branche (1=Alle, 2-11=spezifische)"),
    }, async ({ kldb, l, r, g, a, b }) => {
        try {
            const params = {};
            if (l !== undefined)
                params.l = String(l);
            if (r !== undefined)
                params.r = r;
            if (g !== undefined)
                params.g = String(g);
            if (a !== undefined)
                params.a = String(a);
            if (b !== undefined)
                params.b = String(b);
            const data = (await client.request(`entgelte/${kldb}`, params));
            const parts = [];
            parts.push(`# Gehaltsinformation`);
            parts.push("");
            if (data.beruf)
                parts.push(`**Beruf:** ${data.beruf}`);
            if (data.kldb)
                parts.push(`**KldB-Code:** ${data.kldb}`);
            if (data.region)
                parts.push(`**Region:** ${data.region}`);
            if (data.geschlecht)
                parts.push(`**Geschlecht:** ${data.geschlecht}`);
            if (data.alter)
                parts.push(`**Altersgruppe:** ${data.alter}`);
            if (data.branche)
                parts.push(`**Branche:** ${data.branche}`);
            parts.push("");
            if (data.median !== undefined) {
                parts.push(`**Median-Gehalt:** ${data.median.toLocaleString("de-DE")} EUR/Monat`);
            }
            if (data.q1 !== undefined) {
                parts.push(`**25%-Quartil:** ${data.q1.toLocaleString("de-DE")} EUR/Monat`);
            }
            if (data.q3 !== undefined) {
                parts.push(`**75%-Quartil:** ${data.q3.toLocaleString("de-DE")} EUR/Monat`);
            }
            if (data.beschaeftigte !== undefined) {
                parts.push(`**Beschäftigte:** ${data.beschaeftigte.toLocaleString("de-DE")}`);
            }
            // If response has other fields, include raw data
            if (!data.median && !data.q1 && !data.q3) {
                parts.push("");
                parts.push("## Rohdaten");
                parts.push("```json");
                parts.push(JSON.stringify(data, null, 2));
                parts.push("```");
            }
            return { content: [{ type: "text", text: parts.join("\n") }] };
        }
        catch (error) {
            return { content: [{ type: "text", text: formatError(error) }] };
        }
    });
    // --- gehalt_regionen ---
    server.tool("gehalt_regionen", `Verfügbare Regionen des Entgeltatlas mit IDs abrufen. Die IDs können als r-Parameter in gehalt_suche verwendet werden.

WANN NUTZEN:
- Regionale Gehaltsvergleiche vorbereiten
- Regions-IDs für gehalt_suche nachschlagen`, {}, async () => {
        try {
            const data = (await client.request("regionen"));
            const parts = [];
            parts.push("# Verfügbare Regionen");
            parts.push("");
            if (Array.isArray(data)) {
                for (const region of data) {
                    const r = region;
                    const id = r.id ?? r.code ?? "";
                    const name = r.name ?? r.label ?? "";
                    parts.push(`- **${id}:** ${name}`);
                }
            }
            else {
                parts.push("```json");
                parts.push(JSON.stringify(data, null, 2));
                parts.push("```");
            }
            return { content: [{ type: "text", text: parts.join("\n") }] };
        }
        catch (error) {
            return { content: [{ type: "text", text: formatError(error) }] };
        }
    });
}
//# sourceMappingURL=entgeltatlas.js.map