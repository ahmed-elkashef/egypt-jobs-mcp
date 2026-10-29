import { z } from "zod";
import { ArbeitsmarktApiError } from "../errors.js";
function formatError(error) {
    if (error instanceof ArbeitsmarktApiError) {
        return `Fehler bei der Coaching-API (${error.statusCode}): ${error.message}`;
    }
    return `Fehler: ${error instanceof Error ? error.message : String(error)}`;
}
export function registerCoachingTools(server, client) {
    server.tool("coaching_suche", `Coaching- und Aktivierungsangebote (AVGS-Maßnahmen) der Bundesagentur für Arbeit durchsuchen.

WANN NUTZEN:
- AVGS-geförderte Coachings finden
- Bewerbungscoaching oder Existenzgründungsberatung suchen
- Einzel- vs. Gruppencoaching filtern (mna=1 für Einzel)
- Maßnahmen zur Heranführung an den Arbeitsmarkt finden`, {
        mz: z.string().optional().describe("Maßnahmeziel (z.B. 'SA 01'=Heranführen an Arbeitsmarkt)"),
        sw: z.string().optional().describe("Suchwort"),
        re: z.string().optional().describe("Region"),
        ort: z.string().optional().describe("Ort oder PLZ"),
        uk: z.number().optional().describe("Umkreis in km"),
        mna: z.number().min(0).max(1).optional().describe("0=Gruppe, 1=Einzelcoaching"),
        page: z.number().optional().describe("Seite"),
    }, async ({ mz, sw, re, ort, uk, mna, page }) => {
        try {
            const params = {};
            if (mz)
                params.mz = mz;
            if (sw)
                params.sw = sw;
            if (re)
                params.re = re;
            if (ort)
                params.ort = ort;
            if (uk !== undefined)
                params.uk = String(uk);
            if (mna !== undefined)
                params.mna = String(mna);
            if (page !== undefined)
                params.page = String(page);
            const data = (await client.request("aktivierungsangebote", params));
            const angebote = data.aktivierungsangebote ?? data.items ?? [];
            const total = data.maxErgebnisse ?? data.total ?? angebote.length;
            const parts = [];
            parts.push(`## Coaching-/Aktivierungsangebote (${total} Treffer)\n`);
            for (const coaching of angebote) {
                const titel = coaching.titel ?? "Ohne Titel";
                parts.push(`### ${titel}`);
                if (coaching.anbieter)
                    parts.push(`- **Anbieter:** ${coaching.anbieter}`);
                if (coaching.ort)
                    parts.push(`- **Ort:** ${coaching.ort}`);
                if (coaching.massnahmeziel)
                    parts.push(`- **Maßnahmeziel:** ${coaching.massnahmeziel}`);
                if (coaching.massnahmeart)
                    parts.push(`- **Art:** ${coaching.massnahmeart}`);
                if (coaching.beginn)
                    parts.push(`- **Beginn:** ${coaching.beginn}`);
                if (coaching.dauer)
                    parts.push(`- **Dauer:** ${coaching.dauer}`);
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
//# sourceMappingURL=coaching.js.map