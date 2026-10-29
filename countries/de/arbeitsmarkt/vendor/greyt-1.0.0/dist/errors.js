export class ArbeitsmarktApiError extends Error {
    statusCode;
    endpoint;
    constructor(statusCode, message, endpoint) {
        super(`Arbeitsmarkt API error (${statusCode}) on ${endpoint}: ${message}`);
        this.statusCode = statusCode;
        this.endpoint = endpoint;
        this.name = "ArbeitsmarktApiError";
    }
}
//# sourceMappingURL=errors.js.map