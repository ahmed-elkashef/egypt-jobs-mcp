export const INSTRUCTIONS = `# German Arbeitsmarkt — Entgeltatlas, Jobsuche, Ausbildung, Studium, Weiterbildung & Coaching

Du hast Zugriff auf 6 offizielle APIs der Bundesagentur für Arbeit.

## Empfohlener Workflow

### Gehalt nachschlagen
1. KldB-Code des Berufs ermitteln (siehe häufige Codes unten)
2. \`gehalt_suche\` mit Code aufrufen
3. Optional: nach Region, Geschlecht, Alter filtern

### Stelle finden
1. \`job_suche\` mit Suchbegriff und Ort
2. \`job_details\` mit hashId für vollständige Beschreibung

### Ausbildung/Studium finden
1. \`ausbildung_suche\` oder \`studium_suche\` mit Suchwort
2. \`studienfelder\` für verfügbare Studienfeld-IDs

### Weiterbildung finden
1. \`weiterbildung_suche\` mit Thema und Region
2. bg=true für nur geförderte Kurse

## Häufige KldB-Codes (für gehalt_suche)

| Code | Beruf |
|------|-------|
| 43412 | Softwareentwicklung |
| 25212 | Maschinenbautechnik |
| 71402 | Unternehmensberatung |
| 81312 | Buchhaltung |
| 81402 | Steuerberatung |
| 82102 | Versicherungskaufleute |
| 71302 | Personalwesen |
| 61312 | Krankenpflege |
| 84304 | Rechtsanwälte |
| 51412 | Kfz-Mechatronik |
| 34212 | Elektrotechnik |
| 33212 | Tischlerei |
| 62212 | Pharmazie |
| 84112 | Wirtschaftsprüfung |
| 52312 | Sanitär, Heizung, Klima |

## Leistungsniveaus (für gehalt_suche)

| l | Niveau | Beschreibung |
|---|--------|-------------|
| 1 | Helfer | An-/Ungelernte |
| 2 | Fachkraft | Berufsausbildung |
| 3 | Spezialist | Meister/Techniker/Bachelor |
| 4 | Experte | Master/Diplom |

## Regionen (für gehalt_suche)

| r | Region |
|---|--------|
| 1 | Deutschland gesamt |
| 2 | Ostdeutschland |
| 3 | Westdeutschland |
| 4+ | Einzelne Bundesländer (nutze gehalt_regionen) |

## Jobsuche — Arbeitszeit-Codes

| Code | Bedeutung |
|------|-----------|
| vz | Vollzeit |
| tz | Teilzeit |
| ho | Homeoffice |
| mj | Minijob |
| snw | Schicht/Nacht/Wochenende |

## Bundesland-Kürzel (für re-Parameter)

BAW=Baden-Württemberg, BAY=Bayern, BER=Berlin, BRA=Brandenburg, HB=Bremen, HH=Hamburg, HE=Hessen, MV=Mecklenburg-Vorpommern, NI=Niedersachsen, NRW=Nordrhein-Westfalen, RP=Rheinland-Pfalz, SL=Saarland, SA=Sachsen, ST=Sachsen-Anhalt, SH=Schleswig-Holstein, TH=Thüringen

## Typische Fragen → Tool

| Frage | Tool | Parameter |
|-------|------|-----------|
| Was verdient ein Softwareentwickler? | gehalt_suche | kldb="43412" |
| Gehalt Ingenieur in Bayern? | gehalt_suche | kldb="25212", r="9" |
| Stellen als Projektmanager in München? | job_suche | was="Projektmanager", wo="München" |
| Nur Homeoffice-Jobs? | job_suche | arbeitszeit="ho" |
| Ausbildungsplätze IT? | ausbildung_suche | ort="Berlin", sty=0 |
| Master Informatik? | studium_suche | sw="Informatik", abg="master" |
| Python-Kurs mit Bildungsgutschein? | weiterbildung_suche | sw="Python", bg=true |
| Bewerbungscoaching? | coaching_suche | sw="Bewerbung", mna=1 |

## Wichtige Hinweise

- **Entgeltatlas:** Zeigt Brutto-Monatsgehälter (Median) sozialversicherungspflichtig Beschäftigter
- **Jobsuche:** hashId für job_details ist die base64-kodierte Referenznummer
- **Studiensuche:** Mindestens sw, sfe oder smo=5 muss gesetzt sein
- **Weiterbildung:** bg=true filtert auf Bildungsgutschein-förderfähige Kurse
`;
//# sourceMappingURL=instructions.js.map