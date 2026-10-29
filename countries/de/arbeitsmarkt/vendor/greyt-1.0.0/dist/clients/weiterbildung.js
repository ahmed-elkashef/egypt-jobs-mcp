import { ArbeitsmarktApiError } from "../errors.js";
const BASE_URL = "https://rest.arbeitsagentur.de/infosysbub/wbsuche/pc/v2";
const API_KEY = "infosysbub-wbsuche";
export class WeiterbildungClient {
    async request(endpoint, params = {}) {
        const url = new URL(`${BASE_URL}/${endpoint}`);
        for (const [key, value] of Object.entries(params)) {
            if (value !== undefined && value !== "") {
                url.searchParams.set(key, value);
            }
        }
        const resp = await fetch(url.toString(), {
            method: "GET",
            headers: {
                "X-API-Key": API_KEY,
                Accept: "application/json",
            },
            signal: AbortSignal.timeout(30_000),
        });
        if (!resp.ok) {
            const body = await resp.text().catch(() => "");
            throw new ArbeitsmarktApiError(resp.status, `HTTP ${resp.status} ${resp.statusText}: ${body}`, endpoint);
        }
        return resp.json();
    }
}
//# sourceMappingURL=weiterbildung.js.map