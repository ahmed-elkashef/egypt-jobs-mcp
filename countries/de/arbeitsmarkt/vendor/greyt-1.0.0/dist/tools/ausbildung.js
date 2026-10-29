import { z } from "zod";
import { ArbeitsmarktApiError } from "../errors.js";
function formatError(error) {
    if (error instanceof ArbeitsmarktApiError) {
        return `Fehler bei der Ausbildungs-API (${error.statusCode}): ${error.message}`;
    }
    return `Fehler: ${error instanceof Error ? error.message : String(error)}`;
}
export function registerAusbildungTools(server, client) {
    server.tool("ausbildung_suche", `Ausbildungsplätze und duale Studiengänge in Deutschland durchsuchen.

WANN NUTZEN:
- Ausbildungsplätze in einem Beruf oder Ort suchen
- Duale Studiengänge finden
- Beamtenausbildungen recherchieren

FILTER: sty=0 für Ausbildung, sty=1 für Duales Studium, sty=2 für Beamtenausbildung.`, {
        sty: z.number().min(0).max(4).optional().describe("0=Ausbildung, 1=Duales Studium, 2=Beamtenausbildung"),
        ids: z.string().optional().describe("Kommagetrennte Berufs-IDs"),
        re: z.string().optional().describe("Region/Bundesland-Kürzel"),
        ort: z.string().optional().describe("Ort oder PLZ"),
        uk: z.number().optional().describe("Umkreis in km"),
        page: z.number().optional().describe("Seite"),
        size: z.number().optional().describe("Ergebnisse pro Seite (default: 25)"),
    }, async ({ sty, ids, re, ort, uk, page, size }) => {
        try {
            const params = {};
            if (sty !== undefined)
                params.sty = String(sty);
            if (ids)
                params.ids = ids;
            if (re)
                params.re = re;
            if (ort)
                params.ort = ort;
            if (uk !== undefined)
                params.uk = String(uk);
            if (page !== undefined)
                params.page = String(page);
            if (size !== undefined)
                params.size = String(size);
            const data = (await client.request("ausbildungsangebot", params));
            const angebote = data.ausbildungsangebote ?? data.items ?? [];
            const total = data.maxErgebnisse ?? data.total ?? angebote.length;
            const parts = [];
            parts.push(`## Ausbildungsangebote (${total} Treffer)\n`);
            for (const angebot of angebote) {
                const titel = angebot.titel ?? angebot.beruf ?? "Ohne Titel";
                parts.push(`### ${titel}`);
                if (angebot.arbeitgeber)
                    parts.push(`- **Arbeitgeber:** ${angebot.arbeitgeber}`);
                if (angebot.ort)
                    parts.push(`- **Ort:** ${angebot.ort}`);
                if (angebot.beginn)
                    parts.push(`- **Beginn:** ${angebot.beginn}`);
                if (angebot.typ)
                    parts.push(`- **Typ:** ${angebot.typ}`);
                parts.push("");
            }
            // If no structured data matched, output raw
            if (angebote.length === 0) {
                parts.push("```json");
                parts.push(JSON.stringify(data, null, 2));
                parts.push("```");
            }
            const text = parts.join("\n");
            return { content: [{ type: "text", text }] };
        }
        catch (error) {
            return { content: [{ type: "text", text: formatError(error) }] };
        }
    });
}
//# sourceMappingURL=ausbildung.js.map