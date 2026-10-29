import { ArbeitsmarktApiError } from "../errors.js";
const BASE_URL = "https://rest.arbeitsagentur.de/infosysbub/avgs/avgs/pc/v1";
const API_KEY = "ee971dcb-96fa-47b3-b2be-00863e4fc88b";
export class CoachingClient {
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
//# sourceMappingURL=coaching.js.map