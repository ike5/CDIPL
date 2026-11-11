#!/usr/bin/env node
'use strict';

// A tiny HTTP server with two endpoints:
//   GET  /time  -> the current time as JSON
//   POST /echo  -> the JSON body that was sent, returned unchanged
// Usage: node j05_web_server.js [port]      (default 3000, or $PORT)

const http = require('node:http');

const DEFAULT_PORT = 3000;
const MAX_BODY_BYTES = 1024 * 1024; // refuse request bodies over 1 MB

function sendJson(res, status, payload, headers = {}) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    ...headers,
  });
  res.end(body);
}

/** Collect the request body as a string, rejecting oversized uploads. */
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        // Stop buffering but keep draining, so the client can read the 413 reply.
        chunks.length = 0;
        reject(Object.assign(new Error('Request body too large'), { status: 413 }));
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

function handleTime(req, res) {
  const now = new Date();
  sendJson(res, 200, { time: now.toISOString(), epochMs: now.getTime() });
}

async function handleEcho(req, res) {
  const body = await readBody(req);
  let data;
  try {
    data = JSON.parse(body);
  } catch {
    sendJson(res, 400, { error: 'Request body must be valid JSON' });
    return;
  }
  sendJson(res, 200, data);
}

// path -> { method, handler }
const routes = {
  '/time': { method: 'GET', handler: handleTime },
  '/echo': { method: 'POST', handler: handleEcho },
};

async function handleRequest(req, res) {
  const { pathname } = new URL(req.url, 'http://localhost');
  const route = routes[pathname];

  if (!route) {
    sendJson(res, 404, { error: `No such address: ${pathname}` });
    return;
  }
  if (req.method !== route.method) {
    sendJson(res, 405, { error: `Use ${route.method} for ${pathname}` }, { Allow: route.method });
    return;
  }

  try {
    await route.handler(req, res);
  } catch (err) {
    if (!res.headersSent) {
      const message = err.status ? err.message : 'Internal server error';
      sendJson(res, err.status ?? 500, { error: message }, { Connection: 'close' });
    }
  }
}

function parsePort(value) {
  if (value === undefined) return DEFAULT_PORT;
  const port = Number(value);
  if (!Number.isInteger(port) || port < 0 || port > 65535) {
    throw new Error(`Invalid port "${value}" (expected 0-65535)`);
  }
  return port;
}

function main() {
  let port;
  try {
    port = parsePort(process.argv[2] ?? process.env.PORT);
  } catch (err) {
    console.error(`Error: ${err.message}`);
    console.error('Usage: node j05_web_server.js [port]');
    process.exit(2);
  }

  const server = http.createServer(handleRequest);

  server.on('error', (err) => {
    const reason = err.code === 'EADDRINUSE' ? `port ${port} is already in use` : err.message;
    console.error(`Error: cannot start server: ${reason}`);
    process.exit(1);
  });

  // Listen on the loopback interface only; this is a local tool.
  server.listen(port, '127.0.0.1', () => {
    const { port: actualPort } = server.address();
    console.log(`Listening on http://127.0.0.1:${actualPort}`);
    console.log('  GET  /time   current time as JSON');
    console.log('  POST /echo   returns the JSON you send');
  });

  // Shut down cleanly on Ctrl+C or kill.
  for (const signal of ['SIGINT', 'SIGTERM']) {
    process.on(signal, () => {
      server.close(() => process.exit(0));
      server.closeAllConnections();
    });
  }
}

main();
