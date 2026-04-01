import { Tool, TextContent, ImageContent, EmbeddedResource } from '@modelcontextprotocol/sdk/types.js';
import { GAuthService } from '../services/gauth.js';
export declare class CalendarTools {
    private gauth;
    private calendar;
    constructor(gauth: GAuthService);
    getTools(): Tool[];
    handleTool(name: string, args: Record<string, any>): Promise<Array<TextContent | ImageContent | EmbeddedResource>>;
    private listAccounts;
    private listCalendars;
    private getCalendarEvents;
    private createCalendarEvent;
    private deleteCalendarEvent;
}
