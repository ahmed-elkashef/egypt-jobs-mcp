import { z } from "zod";
import { ArbeitsmarktApiError } from "../errors.js";
function formatError(error) {
    if (error instanceof ArbeitsmarktApiError) {
        return `Fehler bei der Studium-API (${error.statusCode}): ${error.message}`;
    }
    return `Fehler: ${error instanceof Error ? error.message : String(error)}`;
}
export function registerStudiumTools(server, client) {
    // --- studium_suche ---
    server.tool("studium_suche", `Studiengänge an deutschen Hochschulen durchsuchen. Filtert nach Studiengang, Studienfeld, Region, Abschluss und Hochschulart.

WANN NUTZEN:
- Studiengänge zu einem Fach suchen
- Bachelor/Master-Programme vergleichen
- Hochschulen in einer Region finden
- Duale Studiengänge suchen (smo=5)

WICHTIG: Mindestens ein Parameter (sw, sfe oder smo=5) muss gesetzt sein!`, {
        sw: z.string().optional().describe("Suchwort"),
        sfe: z.string().optional().describe("Studienfeld-ID (aus studienfelder)"),
        re: z.string().optional().describe("Region/Bundesland"),
        uk: z.number().optional().describe("Umkreis in km"),
        abg: z.string().optional().describe("Abschluss: 'bachelor', 'master', 'staatsexamen'"),
        hsa: z.string().optional().describe("Hochschulart: 'uni', 'fh'"),
        smo: z.number().optional().describe("5=Dual"),
        pg: z.number().optional().describe("Seite"),
    }, async ({ sw, sfe, re, uk, abg, hsa, smo, pg }) => {
        try {
            const params = {};
            if (sw)
                params.sw = sw;
            if (sfe)
                params.sfe = sfe;
            if (re)
                params.re = re;
            if (uk !== undefined)
                params.uk = String(uk);
            if (abg)
                params.abg = abg;
            if (hsa)
                params.hsa = hsa;
            if (smo !== undefined)
                params.smo = String(smo);
            if (pg !== undefined)
                params.pg = String(pg);
            const data = (await client.request("studienangebote", params));
            const angebote = data.studienangebote ?? data.items ?? [];
            const total = data.maxErgebnisse ?? data.total ?? angebote.length;
            const parts = [];
            parts.push(`## Studiengänge (${total} Treffer)\n`);
            for (const sg of angebote) {
                const name = sg.name ?? sg.studienfach ?? "Ohne Titel";
                parts.push(`### ${name}`);
                if (sg.hochschule)
                    parts.push(`- **Hochschule:** ${sg.hochschule}`);
                if (sg.ort)
                    parts.push(`- **Ort:** ${sg.ort}`);
                if (sg.abschluss)
                    parts.push(`- **Abschluss:** ${sg.abschluss}`);
                if (sg.studienform)
                    parts.push(`- **Studienform:** ${sg.studienform}`);
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
    // --- studienfelder ---
    server.tool("studienfelder", `Alle Studienfelder mit IDs abrufen. Die IDs können als sfe-Parameter in studium_suche verwendet werden.

WANN NUTZEN:
- Studienfeld-IDs für studium_suche nachschlagen
- Überblick über verfügbare Studienbereiche`, {}, async () => {
        try {
            const data = (await client.request("studienfelder"));
            const parts = [];
            parts.push("# Verfügbare Studienfelder");
            parts.push("");
            if (Array.isArray(data)) {
                for (const feld of data) {
                    const f = feld;
                    const id = f.id ?? f.code ?? "";
                    const name = f.name ?? f.label ?? "";
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
//# sourceMappingURL=studium.js.map