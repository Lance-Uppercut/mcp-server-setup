import express from 'express';
import { createServer } from 'http';
import { spawn } from 'child_process';
import { randomUUID } from 'crypto';

const app = express();
const PORT = parseInt(process.env.MCP_PORT || '3101', 10);

app.use(express.text({ type: '*/*' }));

const sessions = new Map();

app.get('/mcp/sse', (req, res) => {
  const sessionId = randomUUID();

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  });

  res.write(`event: endpoint\ndata: /mcp/messages?sessionId=${sessionId}\n\n`);

  const child = spawn('node', ['node_modules/mcp-mail-server/dist/index.js'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
      IMAP_HOST: process.env.IMAP_HOST,
      IMAP_PORT: process.env.IMAP_PORT,
      IMAP_SECURE: process.env.IMAP_SECURE,
      SMTP_HOST: process.env.SMTP_HOST,
      SMTP_PORT: process.env.SMTP_PORT,
      SMTP_SECURE: process.env.SMTP_SECURE,
      EMAIL_USER: process.env.EMAIL_USER,
      EMAIL_PASS: process.env.EMAIL_PASS,
    },
  });

  let buffer = '';
  let closed = false;

  child.stdout.on('data', (chunk) => {
    if (closed) return;
    buffer += chunk.toString('utf8');
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        JSON.parse(trimmed);
        res.write(`event: message\ndata: ${trimmed}\n\n`);
      } catch {
        // non-JSON line from child stdout, skip
      }
    }
  });

  child.stderr.on('data', (chunk) => {
    process.stderr.write(`[mcp-mail] ${chunk}`);
  });

  child.on('exit', (code) => {
    if (!closed) {
      res.end();
    }
  });

  child.on('error', (err) => {
    process.stderr.write(`[mcp-mail] spawn error: ${err.message}\n`);
    if (!closed) {
      res.write(`event: error\ndata: ${err.message}\n\n`);
    }
  });

  const entry = { res, child };
  sessions.set(sessionId, entry);

  req.on('close', () => {
    closed = true;
    child.kill();
    sessions.delete(sessionId);
  });
});

app.post('/mcp/messages', (req, res) => {
  const sessionId = req.query.sessionId;
  const entry = sessions.get(sessionId);

  if (!entry) {
    res.status(404).json({ error: 'Session not found' });
    return;
  }

  entry.child.stdin.write(req.body + '\n');
  res.status(202).end();
});

const server = createServer(app);
server.listen(PORT, () => {
  process.stderr.write(`Yahoo Mail MCP Server (SSE) running on port ${PORT}\n`);
});
