#!/usr/bin/env node

import * as dotenv from 'dotenv';
import { parseArgs } from 'node:util';
import { createServer, IncomingMessage, ServerResponse } from 'http';
import { parse as parseUrl } from 'url';
import { parse as parseQueryString } from 'querystring';
import open from 'open';

// Load environment variables from .env file as fallback
dotenv.config();

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { ListToolsRequestSchema, CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { GmailTools } from './tools/gmail.js';
import { CalendarTools } from './tools/calendar.js';
import { GAuthService } from './services/gauth.js';

// Configure logging
const logger = {
  info: (msg: string) => console.error(`[INFO] ${msg}`),
  error: (msg: string, error?: Error) => {
    console.error(`[ERROR] ${msg}`);
    if (error?.stack) console.error(error.stack);
  }
};

interface ServerConfig {
  gauthFile: string;
  accountsFile: string;
  credentialsDir: string;
}

class OAuthServer {
  private server: ReturnType<typeof createServer>;
  private gauth: GAuthService;

  constructor(gauth: GAuthService) {
    this.gauth = gauth;
    this.server = createServer(this.handleRequest.bind(this));
  }

  private async handleRequest(req: IncomingMessage, res: ServerResponse) {
    const url = parseUrl(req.url || '');
    if (url.pathname !== '/code') {
      res.writeHead(404);
      res.end();
      return;
    }

    const query = parseQueryString(url.query || '');
    if (!query.code) {
      res.writeHead(400);
      res.end();
      return;
    }

    res.writeHead(200);
    res.write('Auth successful! You can close the tab!');
    res.end();

    const storage = {};
    await this.gauth.getCredentials(query.code as string, storage);
    this.server.close();
  }

  listen(port: number = 4100) {
    this.server.listen(port);
  }
}

class GoogleWorkspaceServer {
  private server: Server;
  private gauth: GAuthService;
  private transportMode: 'stdio' | 'sse';
  private port: number;
  private tools!: {
    gmail: GmailTools;
    calendar: CalendarTools;
  };

  constructor(config: ServerConfig, transportMode: 'stdio' | 'sse', port: number) {
    logger.info('Starting Google Workspace MCP Server...');

    // Initialize services
    this.gauth = new GAuthService(config);
    this.transportMode = transportMode;
    this.port = port;
    
    // Initialize server
    this.server = new Server(
      { name: "mcp-google-workspace", version: "1.0.0" },
      { capabilities: { tools: {} } }
    );
  }

  private async initializeTools() {
    // Initialize tools after OAuth2 client is ready
    this.tools = {
      gmail: new GmailTools(this.gauth),
      calendar: new CalendarTools(this.gauth)
    };

    this.setupHandlers();
  }

  private async startAuthFlow(userId: string) {
    const authUrl = await this.gauth.getAuthorizationUrl(userId, {});
    open(authUrl);

    const oauthServer = new OAuthServer(this.gauth);
    oauthServer.listen(4100);
  }

  private async setupOAuth2(userId: string) {
    const accounts = await this.gauth.getAccountInfo();
    if (accounts.length === 0) {
      throw new Error("No accounts specified in .gauth.json");
    }
    if (!accounts.some(a => a.email === userId)) {
      throw new Error(`Account for email: ${userId} not specified in .gauth.json`);
    }

    let credentials = await this.gauth.getStoredCredentials(userId);
    if (!credentials) {
      if (this.transportMode === 'sse') {
        throw new Error("No stored credentials found. Seed OAuth files in credentials directory before using SSE mode.");
      }
      await this.startAuthFlow(userId);
    } else {
      const tokens = credentials.credentials;
      if (tokens.expiry_date && tokens.expiry_date < Date.now()) {
        logger.error("credentials expired, trying refresh");
      }

      // Refresh access token if needed
      const userInfo = await this.gauth.getUserInfo(credentials);
      await this.gauth.storeCredentials(credentials, userId);
    }
  }

  private setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          ...this.tools.gmail.getTools(),
          ...this.tools.calendar.getTools()
        ]
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      
      try {
        if (typeof args !== 'object' || args === null) {
          return {
            isError: true,
            content: [{ type: "text", text: JSON.stringify({
              error: "arguments must be dictionary",
              success: false
            }, null, 2) }]
          };
        }

        // Special case for list_accounts tools which don't require user_id
        if (name === 'gmail_list_accounts' || name === 'calendar_list_accounts') {
          try {
            // Route tool calls to appropriate handler
            let result;
            if (name.startsWith('gmail_')) {
              result = await this.tools.gmail.handleTool(name, args);
            } else if (name.startsWith('calendar_')) {
              result = await this.tools.calendar.handleTool(name, args);
            } else {
              throw new Error(`Unknown tool: ${name}`);
            }

            return { content: result };
          } catch (error) {
            logger.error(`Error handling tool ${name}:`, error as Error);
            return {
              isError: true,
              content: [{ type: "text", text: JSON.stringify({
                error: `Tool execution failed: ${(error as Error).message}`,
                success: false
              }, null, 2) }]
            };
          }
        }

        // For all other tools, require user_id
        if (!args.user_id) {
          return {
            isError: true,
            content: [{ type: "text", text: JSON.stringify({
              error: "user_id argument is missing in dictionary",
              success: false
            }, null, 2) }]
          };
        }

        try {
          await this.setupOAuth2(args.user_id as string);
        } catch (error) {
          logger.error("OAuth2 setup failed:", error as Error);
          return {
            isError: true,
            content: [{ type: "text", text: JSON.stringify({
              error: `OAuth2 setup failed: ${(error as Error).message}`,
              success: false
            }, null, 2) }]
          };
        }

        // Route tool calls to appropriate handler
        try {
          let result;
          if (name.startsWith('gmail_')) {
            result = await this.tools.gmail.handleTool(name, args);
          } else if (name.startsWith('calendar_')) {
            result = await this.tools.calendar.handleTool(name, args);
          } else {
            throw new Error(`Unknown tool: ${name}`);
          }

          return { content: result };
        } catch (error) {
          logger.error(`Error handling tool ${name}:`, error as Error);
          return {
            isError: true,
            content: [{ type: "text", text: JSON.stringify({
              error: `Tool execution failed: ${(error as Error).message}`,
              success: false
            }, null, 2) }]
          };
        }
      } catch (error) {
        logger.error("Unexpected error in call_tool:", error as Error);
        return {
          isError: true,
          content: [{ type: "text", text: JSON.stringify({
            error: `Unexpected error: ${(error as Error).message}`,
            success: false
          }, null, 2) }]
        };
      }
    });
  }

  private async startSseServer() {
    const sessions: Record<string, SSEServerTransport> = {};
    const httpServer = createServer(async (req, res) => {
      const url = parseUrl(req.url || '', true);

      if (req.method === 'GET' && url.pathname === '/sse') {
        const transport = new SSEServerTransport('/messages', res);
        sessions[transport.sessionId] = transport;
        res.on('close', () => {
          delete sessions[transport.sessionId];
        });

        try {
          await this.server.connect(transport);
          await transport.start();
        } catch (error) {
          logger.error("SSE connection error:", error as Error);
        }
        return;
      }

      if (req.method === 'POST' && url.pathname === '/messages') {
        const sessionId = url.query.sessionId as string | undefined;
        if (!sessionId || !sessions[sessionId]) {
          res.writeHead(400).end('Invalid or missing sessionId');
          return;
        }
        await sessions[sessionId].handlePostMessage(req, res);
        return;
      }

      if (req.method === 'GET' && url.pathname === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', transport: 'sse', port: this.port }));
        return;
      }

      res.writeHead(404).end();
    });

    await new Promise<void>((resolve, reject) => {
      httpServer.once('error', reject);
      httpServer.listen(this.port, '0.0.0.0', () => {
        logger.info(`SSE server listening on port ${this.port}`);
        resolve();
      });
    });
  }

  async start() {
    try {
      // Initialize OAuth2 client first
      await this.gauth.initialize();

      // Initialize tools after OAuth2 is ready
      await this.initializeTools();

      // Check for existing credentials
      const accounts = await this.gauth.getAccountInfo();
      for (const account of accounts) {
        const creds = await this.gauth.getStoredCredentials(account.email);
        if (creds) {
          logger.info(`found credentials for ${account.email}`);
        }
      }

      if (this.transportMode === 'sse') {
        await this.startSseServer();
        logger.info('Server ready in SSE mode');
        return;
      }

      const transport = new StdioServerTransport();
      logger.info('Connecting to stdio transport...');
      await this.server.connect(transport);
      logger.info('Server ready in stdio mode');
    } catch (error) {
      logger.error("Server error:", error as Error);
      throw error; // Let the error propagate to stop the server
    }
  }
}

// Parse command line arguments
const { values } = parseArgs({
  args: process.argv.slice(2),
  options: {
    'gauth-file': { type: 'string', default: './.gauth.json' },
    'accounts-file': { type: 'string', default: './.accounts.json' },
    'credentials-dir': { type: 'string', default: '.' }
  }
});

const config: ServerConfig = {
  gauthFile: values['gauth-file'] as string,
  accountsFile: values['accounts-file'] as string,
  credentialsDir: values['credentials-dir'] as string
};

const transportMode = (process.env.TRANSPORT_MODE || 'stdio').toLowerCase() === 'sse' ? 'sse' : 'stdio';
const port = Number(process.env.PORT || '3103');

// Start the server
const server = new GoogleWorkspaceServer(config, transportMode, port);
server.start().catch(error => {
  logger.error("Fatal error:", error as Error);
  process.exit(1);
});
