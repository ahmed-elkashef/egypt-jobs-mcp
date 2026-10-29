import { z } from "zod";
import { ArbeitsmarktApiError } from "../errors.js";
function formatError(error) {
    if (error instanceof ArbeitsmarktApiError) {
        return `Fehler bei der Jobsuche-API (${error.statusCode}): ${error.message}`;
    }
    return `Fehler: ${error instanceof Error ? error.message : String(error)}`;
}
export function registerJobsucheTools(server, client) {
    // --- job_suche ---
    server.tool("job_suche", `Stellenangebote der Bundesagentur für Arbeit durchsuchen (500.000+ aktive Stellen). Unterstützt Volltext, Ort, Umkreis, Arbeitszeit und weitere Filter.

WANN NUTZEN:
- Stellenangebote zu einem Beruf oder Thema suchen
- Jobs in einer bestimmten Stadt oder Region finden
- Nach Arbeitszeit (Vollzeit, Teilzeit, Homeoffice) filtern

ERGEBNIS: Liste mit Titel, Arbeitgeber, Ort, Datum und hashId für Details.`, {
        was: z.string().optional().describe("Suchbegriff (Beruf, Tätigkeit, Firma)"),
        wo: z.string().optional().describe("Ort oder PLZ"),
        umkreis: z.number().optional().describe("Umkreis in km (default: 25)"),
        angebotsart: z.number().optional().describe("1=Arbeit, 2=Selbständigkeit, 4=Ausbildung, 34=Praktikum"),
        arbeitszeit: z.string().optional().describe("vz=Vollzeit, tz=Teilzeit, ho=Homeoffice, mj=Minijob"),
        befristung: z.number().optional().describe("1=Befristet, 2=Unbefristet"),
        veroeffentlicht_seit: z.number().optional().describe("Tage seit Veröffentlichung"),
        page: z.number().optional().describe("Seite (default: 1)"),
        size: z.number().max(100).optional().describe("Ergebnisse pro Seite (default: 25, max: 100)"),
    }, async ({ was, wo, umkreis, angebotsart, arbeitszeit, befristung, veroeffentlicht_seit, page, size }) => {
        try {
            const params = {};
            if (was)
                params.was = was;
            if (wo)
                params.wo = wo;
            if (umkreis !== undefined)
                params.umkreis = String(umkreis);
            if (angebotsart !== undefined)
                params.angebotsart = String(angebotsart);
            if (arbeitszeit)
                params.arbeitszeit = arbeitszeit;
            if (befristung !== undefined)
                params.befristung = String(befristung);
            if (veroeffentlicht_seit !== undefined)
                params.veroeffentlichtseit = String(veroeffentlicht_seit);
            if (page !== undefined)
                params.page = String(page);
            if (size !== undefined)
                params.size = String(size);
            const data = (await client.request("pc/v4/jobs", params));
            const stellen = data.stellenangebote ?? [];
            const total = data.maxErgebnisse ?? stellen.length;
            const parts = [];
            parts.push(`## Stellenangebote (${total} Treffer)\n`);
            for (const entry of stellen) {
                const job = entry.stelle ?? entry;
                const titel = job.titel ?? "Ohne Titel";
                const arbeitgeber = job.arbeitgeber ?? "Unbekannt";
                const ort = job.arbeitsort?.ort ?? "";
                const datum = job.veroeffentlichtAm ?? job.eintrittsdatum ?? "";
                const hashId = job.hashId ?? "";
                parts.push(`### ${titel}`);
                parts.push(`- **Arbeitgeber:** ${arbeitgeber}`);
                if (ort)
                    parts.push(`- **Ort:** ${ort}`);
                if (datum)
                    parts.push(`- **Datum:** ${datum}`);
                if (job.arbeitszeit)
                    parts.push(`- **Arbeitszeit:** ${job.arbeitszeit}`);
                if (job.befristung)
                    parts.push(`- **Befristung:** ${job.befristung}`);
                if (hashId)
                    parts.push(`- **hashId:** \`${hashId}\``);
                parts.push("");
            }
            const text = stellen.length > 0
                ? parts.join("\n")
                : "Keine Stellenangebote gefunden. Versuche andere Suchbegriffe oder Filter.";
            return { content: [{ type: "text", text }] };
        }
        catch (error) {
            return { content: [{ type: "text", text: formatError(error) }] };
        }
    });
    // --- job_details ---
    server.tool("job_details", `Details einer Stellenanzeige abrufen. Die hashId stammt aus den Ergebnissen von job_suche.

WANN NUTZEN:
- Vollständige Stellenbeschreibung lesen
- Anforderungen und Konditionen einer Stelle prüfen
- Kontaktdaten des Arbeitgebers finden`, {
        hashId: z.string().describe("base64-kodierte Referenznummer aus job_suche"),
    }, async ({ hashId }) => {
        try {
            const data = (await client.request(`pc/v4/jobdetails/${hashId}`));
            const parts = [];
            const titel = data.titel ?? "Stellenangebot";
            parts.push(`# ${titel}`);
            parts.push("");
            if (data.arbeitgeber)
                parts.push(`**Arbeitgeber:** ${data.arbeitgeber}`);
            if (data.branche)
                parts.push(`**Branche:** ${data.branche}`);
            const ort = data.arbeitsort;
            if (ort?.ort)
                parts.push(`**Ort:** ${ort.ort}${ort.plz ? ` (${ort.plz})` : ""}`);
            if (data.arbeitszeit)
                parts.push(`**Arbeitszeit:** ${data.arbeitszeit}`);
            if (data.befristung)
                parts.push(`**Befristung:** ${data.befristung}`);
            if (data.eintrittsdatum)
                parts.push(`**Eintritt:** ${data.eintrittsdatum}`);
            if (data.verguetung)
                parts.push(`**Vergütung:** ${data.verguetung}`);
            const beschreibung = data.stellenbeschreibung ?? data.beschreibung;
            if (beschreibung) {
                parts.push("");
                parts.push("## Stellenbeschreibung");
                parts.push(beschreibung);
            }
            // Include raw data for any additional fields
            const knownKeys = new Set(["titel", "arbeitgeber", "branche", "arbeitsort", "arbeitszeit", "befristung", "eintrittsdatum", "verguetung", "stellenbeschreibung", "beschreibung"]);
            const extra = {};
            for (const [k, v] of Object.entries(data)) {
                if (!knownKeys.has(k) && v !== null && v !== undefined) {
                    extra[k] = v;
                }
            }
            if (Object.keys(extra).length > 0) {
                parts.push("");
                parts.push("## Weitere Details");
                parts.push("```json");
                parts.push(JSON.stringify(extra, null, 2));
                parts.push("```");
            }
            return { content: [{ type: "text", text: parts.join("\n") }] };
        }
        catch (error) {
            return { content: [{ type: "text", text: formatError(error) }] };
        }
    });
}
//# sourceMappingURL=jobsuche.js.map