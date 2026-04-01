import { google } from 'googleapis';
import * as fs from 'fs/promises';
import * as path from 'path';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REDIRECT_URI = 'http://localhost:4100/code';
const SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.settings.basic',
    'https://www.googleapis.com/auth/calendar'
];
class AccountInfoImpl {
    constructor(email, accountType, extraInfo = '') {
        this.email = email;
        this.accountType = accountType;
        this.extraInfo = extraInfo;
    }
    toDescription() {
        return `Account for email: ${this.email} of type: ${this.accountType}. Extra info for: ${this.extraInfo}`;
    }
}
export class GetCredentialsError extends Error {
    constructor(authorizationUrl) {
        super('Error getting credentials');
        this.authorizationUrl = authorizationUrl;
    }
}
export class CodeExchangeError extends GetCredentialsError {
}
export class NoRefreshTokenError extends GetCredentialsError {
}
export class NoUserIdError extends Error {
}
export class GAuthService {
    constructor(config) {
        this.config = config;
    }
    getConfig() {
        return this.config;
    }
    async initialize() {
        try {
            const gauthPath = path.resolve(process.cwd(), this.config.gauthFile);
            const gauthData = await fs.readFile(gauthPath, 'utf8');
            const credentials = JSON.parse(gauthData);
            if (!credentials.installed) {
                throw new Error('Invalid OAuth2 credentials format in gauth file');
            }
            this.oauth2Client = new google.auth.OAuth2(credentials.installed.client_id, credentials.installed.client_secret, REDIRECT_URI);
        }
        catch (error) {
            throw new Error(`Failed to initialize OAuth2 client: ${error.message}`);
        }
    }
    getClient() {
        if (!this.oauth2Client) {
            throw new Error('OAuth2 client not initialized. Call initialize() first.');
        }
        return this.oauth2Client;
    }
    getCredentialFilename(userId) {
        const credPath = path.resolve(this.config.credentialsDir, `.oauth2.${userId}.json`);
        const credDir = path.resolve(this.config.credentialsDir);
        if (!credPath.startsWith(credDir + path.sep) && credPath !== credDir) {
            throw new Error('Invalid user ID');
        }
        return credPath;
    }
    async getAccountInfo() {
        try {
            const accountsPath = path.resolve(process.cwd(), this.config.accountsFile);
            const data = await fs.readFile(accountsPath, 'utf8');
            const { accounts } = JSON.parse(data);
            if (!Array.isArray(accounts)) {
                throw new Error('Invalid accounts format in accounts file');
            }
            return accounts.map((acc) => new AccountInfoImpl(acc.email, acc.account_type, acc.extra_info));
        }
        catch (error) {
            console.error('Error reading accounts file:', error);
            return [];
        }
    }
    async getStoredCredentials(userId) {
        if (!this.oauth2Client) {
            return null;
        }
        try {
            const credFilePath = this.getCredentialFilename(userId);
            const data = await fs.readFile(credFilePath, 'utf8');
            const credentials = JSON.parse(data);
            this.oauth2Client.setCredentials(credentials);
            return this.oauth2Client;
        }
        catch (error) {
            console.warn(`No stored OAuth2 credentials yet for user: ${userId}`);
            return null;
        }
    }
    async storeCredentials(client, userId) {
        const credFilePath = this.getCredentialFilename(userId);
        await fs.mkdir(path.dirname(credFilePath), { recursive: true });
        await fs.writeFile(credFilePath, JSON.stringify(client.credentials, null, 2), { mode: 0o600 });
    }
    async exchangeCode(authorizationCode) {
        if (!this.oauth2Client) {
            throw new Error('OAuth2 client not initialized. Call initialize() first.');
        }
        try {
            const { tokens } = await this.oauth2Client.getToken(authorizationCode);
            this.oauth2Client.setCredentials(tokens);
            return this.oauth2Client;
        }
        catch (error) {
            console.error('Error exchanging code:', error);
            throw new CodeExchangeError('');
        }
    }
    async getUserInfo(client) {
        const oauth2 = google.oauth2({ version: 'v2', auth: client });
        try {
            const { data } = await oauth2.userinfo.get();
            if (data && data.id) {
                return data;
            }
            throw new NoUserIdError();
        }
        catch (error) {
            console.error('Error getting user info:', error);
            throw error;
        }
    }
    async getAuthorizationUrl(emailAddress, state) {
        if (!this.oauth2Client) {
            throw new Error('OAuth2 client not initialized. Call initialize() first.');
        }
        return this.oauth2Client.generateAuthUrl({
            access_type: 'offline',
            scope: SCOPES,
            state: JSON.stringify(state),
            prompt: 'consent',
            login_hint: emailAddress
        });
    }
    async getCredentials(authorizationCode, state) {
        let emailAddress = '';
        try {
            const credentials = await this.exchangeCode(authorizationCode);
            const userInfo = await this.getUserInfo(credentials);
            emailAddress = userInfo.email;
            if (credentials.credentials.refresh_token) {
                await this.storeCredentials(credentials, emailAddress);
                return credentials;
            }
            else {
                const storedCredentials = await this.getStoredCredentials(emailAddress);
                if (storedCredentials?.credentials.refresh_token) {
                    return storedCredentials;
                }
            }
        }
        catch (error) {
            if (error instanceof CodeExchangeError) {
                console.error('An error occurred during code exchange.');
                error.authorizationUrl = await this.getAuthorizationUrl(emailAddress, state);
                throw error;
            }
            if (error instanceof NoUserIdError) {
                console.error('No user ID could be retrieved.');
            }
            const authorizationUrl = await this.getAuthorizationUrl(emailAddress, state);
            throw new NoRefreshTokenError(authorizationUrl);
        }
        const authorizationUrl = await this.getAuthorizationUrl(emailAddress, state);
        throw new NoRefreshTokenError(authorizationUrl);
    }
}
