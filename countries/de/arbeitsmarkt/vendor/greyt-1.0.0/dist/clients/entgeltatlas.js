import { ArbeitsmarktApiError } from "../errors.js";
const BASE_URL = "https://rest.arbeitsagentur.de/infosysbub/entgeltatlas/pc/v1";
const API_KEY = "c4f0d292-9d0f-4763-87dd-d3f9e78fb006";
export class EntgeltatlasClient {
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
//# sourceMappingURL=entgeltatlas.js.map