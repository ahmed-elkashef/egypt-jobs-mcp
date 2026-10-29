export function getLandingPageHtml() {
    return `<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>German Arbeitsmarkt MCP — Deutsche Arbeitsmarktdaten für KI</title>
<meta name="description" content="6 offizielle APIs der Bundesagentur für Arbeit — Entgeltatlas, Jobsuche, Ausbildung, Studium, Weiterbildung & Coaching — direkt aus Claude, Cursor oder jedem MCP-fähigen System abfragen.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Syne', sans-serif;
  background: #05050D;
  color: #ededed;
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.card {
  max-width: 540px;
  width: 100%;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 24px;
  padding: 48px 40px;
  text-align: center;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 600;
  background: rgba(52,211,153,0.1);
  color: #34d399;
  border: 1px solid rgba(52,211,153,0.2);
  margin-bottom: 24px;
}
h1 {
  font-size: 28px;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 12px;
}
.subtitle {
  font-size: 16px;
  color: rgba(237,237,237,0.6);
  margin-bottom: 32px;
  line-height: 1.6;
}
.apis {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 32px;
}
.api-item {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 16px;
  text-align: left;
}
.api-item .name {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 4px;
}
.api-item .desc {
  font-size: 12px;
  color: rgba(237,237,237,0.5);
}
.stats {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-bottom: 32px;
  font-size: 14px;
  color: rgba(237,237,237,0.5);
}
.stats strong {
  color: #ededed;
  font-weight: 700;
  font-size: 20px;
  display: block;
}
.btn {
  display: inline-block;
  padding: 14px 32px;
  background: #4f49ff;
  color: white;
  border: none;
  border-radius: 999px;
  font-family: inherit;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.2s;
  box-shadow: 0 10px 30px rgba(74,64,255,0.35);
}
.btn:hover { opacity: 0.9; }
</style>
</head>
<body>
<div class="card">
  <div class="badge">MCP Server</div>
  <h1>German Arbeitsmarkt MCP</h1>
  <p class="subtitle">6 offizielle APIs der Bundesagentur für Arbeit — Entgeltatlas, Jobsuche, Ausbildung, Studium, Weiterbildung & Coaching — direkt aus deinem KI-Client abfragen.</p>

  <div class="apis">
    <div class="api-item">
      <div class="name">Entgeltatlas</div>
      <div class="desc">Median-Gehälter nach Beruf, Region, Alter</div>
    </div>
    <div class="api-item">
      <div class="name">Jobsuche</div>
      <div class="desc">500.000+ Stellenangebote durchsuchen</div>
    </div>
    <div class="api-item">
      <div class="name">Ausbildung</div>
      <div class="desc">Ausbildungsplätze & duale Studiengänge</div>
    </div>
    <div class="api-item">
      <div class="name">Studium</div>
      <div class="desc">Studiengänge an deutschen Hochschulen</div>
    </div>
    <div class="api-item">
      <div class="name">Weiterbildung</div>
      <div class="desc">Kurse, Umschulungen, Bildungsgutschein</div>
    </div>
    <div class="api-item">
      <div class="name">Coaching</div>
      <div class="desc">AVGS-Maßnahmen & Aktivierungsangebote</div>
    </div>
  </div>

  <div class="stats">
    <div><strong>6</strong> APIs</div>
    <div><strong>9</strong> Tools</div>
    <div><strong>0</strong> Auth</div>
  </div>

  <a href="https://business-os.de/apps/german-arbeitsmarkt-mcp" class="btn">Mehr erfahren</a>
</div>
</body>
</html>`;
}
//# sourceMappingURL=landing.js.map