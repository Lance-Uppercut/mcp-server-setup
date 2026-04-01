import { OAuth2Client } from 'google-auth-library';
export interface AccountInfo {
    email: string;
    accountType: string;
    extraInfo?: string;
    toDescription(): string;
}
interface ServerConfig {
    gauthFile: string;
    accountsFile: string;
    credentialsDir: string;
}
export declare class GetCredentialsError extends Error {
    authorizationUrl: string;
    constructor(authorizationUrl: string);
}
export declare class CodeExchangeError extends GetCredentialsError {
}
export declare class NoRefreshTokenError extends GetCredentialsError {
}
export declare class NoUserIdError extends Error {
}
export declare class GAuthService {
    private oauth2Client?;
    private config;
    constructor(config: ServerConfig);
    getConfig(): ServerConfig;
    initialize(): Promise<void>;
    getClient(): OAuth2Client;
    private getCredentialFilename;
    getAccountInfo(): Promise<AccountInfo[]>;
    getStoredCredentials(userId: string): Promise<OAuth2Client | null>;
    storeCredentials(client: OAuth2Client, userId: string): Promise<void>;
    exchangeCode(authorizationCode: string): Promise<OAuth2Client>;
    getUserInfo(client: OAuth2Client): Promise<any>;
    getAuthorizationUrl(emailAddress: string, state: any): Promise<string>;
    getCredentials(authorizationCode: string, state: any): Promise<OAuth2Client>;
}
export {};
