export declare class ArbeitsmarktApiError extends Error {
    statusCode: number;
    endpoint: string;
    constructor(statusCode: number, message: string, endpoint: string);
}
