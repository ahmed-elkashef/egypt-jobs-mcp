import { z } from "zod";
import { ArbeitsmarktApiError } from "../errors.js";
function formatError(error) {
    if (error instanceof ArbeitsmarktApiError) {
        return `Fehler bei der Weiterbildungs-API (${error.statusCode}): ${error.message}`;
    }
    return `Fehler: ${error instanceof Error ? error.message : String(error)}`;
}
export function registerWeiterbildungTools(server, client) {
    server.tool("weiterbildung_suche", `Weiterbildungskurse und Umschulungen durchsuchen. Filtert nach Thema, Region, Unterrichtsform und Bildungsgutschein.

WANN NUTZEN:
- Weiterbildungen zu einem Thema finden
- Kurse mit Bildungsgutschein-Förderung suchen (bg=true)
- E-Learning oder Präsenzkurse filtern
- Umschulungen in einer Region finden`, {
        sw: z.string().optional().describe("Suchwort (Kursthema, Anbieter)"),
        re: z.string().optional().describe("Region"),
        ort: z.string().optional().describe("Ort oder PLZ"),
        uk: z.number().optional().describe("Umkreis in km"),
        uz: z.number().optional().describe("Unterrichtszeit: 1=Ganztägig, 2=Teilzeit"),
        uf: z.number().optional().describe("Unterrichtsform: 1=Präsenz, 2=E-Learning, 3=Blended"),
        bg: z.boolean().optional().describe("Nur mit Bildungsgutschein förderbar"),
        page: z.number().optional().describe("Seite"),
    }, async ({ sw, re, ort, uk, uz, uf, bg, page }) => {
        try {
            const params = {};
            if (sw)
                params.sw = sw;
            if (re)
                params.re = re;
            if (ort)
                params.ort = ort;
            if (uk !== undefined)
                params.uk = String(uk);
            if (uz !== undefined)
                params.uz = String(uz);
            if (uf !== undefined)
                params.uf = String(uf);
            if (bg !== undefined)
                params.bg = bg ? "true" : "false";
            if (page !== undefined)
                params.page = String(page);
            const data = (await client.request("bildungsangebot", params));
            const angebote = data.bildungsangebote ?? data.items ?? [];
            const total = data.maxErgebnisse ?? data.total ?? angebote.length;
            const parts = [];
            parts.push(`## Weiterbildungsangebote (${total} Treffer)\n`);
            for (const wb of angebote) {
                const titel = wb.titel ?? "Ohne Titel";
                parts.push(`### ${titel}`);
                if (wb.anbieter)
                    parts.push(`- **Anbieter:** ${wb.anbieter}`);
                if (wb.ort)
                    parts.push(`- **Ort:** ${wb.ort}`);
                if (wb.beginn)
                    parts.push(`- **Beginn:** ${wb.beginn}`);
                if (wb.dauer)
                    parts.push(`- **Dauer:** ${wb.dauer}`);
                if (wb.unterrichtsform)
                    parts.push(`- **Unterrichtsform:** ${wb.unterrichtsform}`);
                if (wb.bildungsgutschein)
                    parts.push(`- **Bildungsgutschein:** Ja`);
                parts.push("");
            }
            if (angebote.length === 0) {
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
//# sourceMappingURL=weiterbildung.js.map