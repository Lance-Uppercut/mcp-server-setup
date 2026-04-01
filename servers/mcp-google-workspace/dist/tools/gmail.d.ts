import { Tool, TextContent, ImageContent, EmbeddedResource } from '@modelcontextprotocol/sdk/types.js';
import { GAuthService } from '../services/gauth.js';
export declare class GmailTools {
    private gauth;
    private gmail;
    constructor(gauth: GAuthService);
    private decodeBase64UrlString;
    private extractEmailText;
    private extractEmailHeaders;
    getTools(): Tool[];
    handleTool(name: string, args: Record<string, any>): Promise<Array<TextContent | ImageContent | EmbeddedResource>>;
    private listAccounts;
    private queryEmails;
    private getEmailById;
    private bulkGetEmails;
    private createDraft;
    private deleteDraft;
    private reply;
    private getAttachment;
    private bulkSaveAttachments;
    private archive;
    private bulkArchive;
}
