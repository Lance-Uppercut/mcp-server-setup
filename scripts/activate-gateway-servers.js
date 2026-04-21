#!/usr/bin/env node

const http = require("http")
const https = require("https")
const { URL } = require("url")

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function getClient(urlObj) {
  return urlObj.protocol === "https:" ? https : http
}

function postJson(urlObj, path, payload) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(payload)
    const client = getClient(urlObj)
    const req = client.request(
      {
        protocol: urlObj.protocol,
        hostname: urlObj.hostname,
        port: urlObj.port,
        path,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
        },
      },
      (res) => {
        let out = ""
        res.on("data", (chunk) => {
          out += chunk
        })
        res.on("end", () => {
          resolve({ status: res.statusCode || 0, body: out })
        })
      },
    )

    req.on("error", reject)
    req.write(body)
    req.end()
  })
}

function discoverSession(urlObj) {
  return new Promise((resolve, reject) => {
    const client = getClient(urlObj)
    const req = client.get(
      {
        protocol: urlObj.protocol,
        hostname: urlObj.hostname,
        port: urlObj.port,
        path: urlObj.pathname,
        headers: { Accept: "text/event-stream" },
      },
      (res) => {
        let buffer = ""
        res.setEncoding("utf8")
        res.on("data", (chunk) => {
          buffer += chunk
          const match = buffer.match(/data:\s*(\/sse\?sessionid=[^\s\r\n]+)/)
          if (match) {
            resolve({
              sessionPath: match[1],
              close: () => req.destroy(),
            })
          }
        })
        res.on("end", () => {
          reject(new Error("SSE stream ended before session endpoint was emitted"))
        })
      },
    )

    req.on("error", reject)
    req.setTimeout(10000, () => {
      req.destroy(new Error("Timed out waiting for SSE session endpoint"))
    })
  })
}

async function main() {
  const gatewayUrl = process.argv[2] || "http://localhost:3100/sse"
  const serversCsv = process.argv[3] || ""
  const servers = serversCsv
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)

  if (servers.length === 0) {
    throw new Error("No servers specified. Pass a comma-separated server list as arg2.")
  }

  const urlObj = new URL(gatewayUrl)
  const session = await discoverSession(urlObj)
  const sessionPath = session.sessionPath

  await postJson(urlObj, sessionPath, {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "gateway-activator", version: "1.0" },
    },
  })

  await postJson(urlObj, sessionPath, {
    jsonrpc: "2.0",
    method: "notifications/initialized",
    params: {},
  })

  for (const server of servers) {
    const response = await postJson(urlObj, sessionPath, {
      jsonrpc: "2.0",
      id: `add-${server}`,
      method: "tools/call",
      params: {
        name: "mcp-add",
        arguments: { name: server, activate: true },
      },
    })

    console.log(`mcp-add ${server} -> HTTP ${response.status}`)
    await delay(1500)
  }

  session.close()
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})
