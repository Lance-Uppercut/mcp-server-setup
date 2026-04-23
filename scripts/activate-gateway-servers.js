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

function parseSseChunk(rawChunk) {
  const lines = rawChunk.split(/\r?\n/)
  const dataLines = []
  for (const line of lines) {
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart())
    }
  }
  if (dataLines.length === 0) {
    return null
  }
  return dataLines.join("\n")
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

function createSseSession(urlObj) {
  return new Promise((resolve, reject) => {
    let settled = false
    let buffer = ""
    const pending = new Map()

    function settleError(error) {
      if (!settled) {
        settled = true
        reject(error)
      }
    }

    function resolvePending(message) {
      if (!message || typeof message !== "object") {
        return
      }
      const { id } = message
      if (id === undefined || id === null) {
        return
      }
      const key = String(id)
      const handler = pending.get(key)
      if (!handler) {
        return
      }
      pending.delete(key)
      handler(message)
    }

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
        if (res.statusCode !== 200) {
          settleError(new Error(`SSE connect failed with HTTP ${res.statusCode || 0}`))
          req.destroy()
          return
        }

        res.setEncoding("utf8")
        res.on("data", (chunk) => {
          buffer += chunk

          while (true) {
            const separatorMatch = buffer.match(/\r?\n\r?\n/)
            if (!separatorMatch || separatorMatch.index === undefined) {
              break
            }

            const separatorIndex = separatorMatch.index
            const separatorLength = separatorMatch[0].length

            const rawEvent = buffer.slice(0, separatorIndex)
            buffer = buffer.slice(separatorIndex + separatorLength)
            const data = parseSseChunk(rawEvent)
            if (!data) {
              continue
            }

            const sessionMatch = data.match(/^(\/sse\?sessionid=[^\s\r\n]+)$/)
            if (sessionMatch && !settled) {
              settled = true
              const sessionPath = sessionMatch[1]
              const api = {
                sessionPath,
                close: () => req.destroy(),
                waitForResponse: (id, timeoutMs = 20000) =>
                  new Promise((resolveResponse, rejectResponse) => {
                    const key = String(id)
                    const timeout = setTimeout(() => {
                      pending.delete(key)
                      rejectResponse(new Error(`Timed out waiting for response id=${key}`))
                    }, timeoutMs)
                    pending.set(key, (message) => {
                      clearTimeout(timeout)
                      resolveResponse(message)
                    })
                  }),
              }
              resolve(api)
              continue
            }

            try {
              const parsed = JSON.parse(data)
              resolvePending(parsed)
            } catch (error) {
              // Ignore non-JSON events.
            }
          }
        })
        res.on("end", () => {
          settleError(new Error("SSE stream ended unexpectedly"))
        })
      },
    )

    req.on("error", settleError)
    req.setTimeout(10000, () => {
      req.destroy(new Error("Timed out waiting for SSE session endpoint"))
    })
  })
}

function describeRpcMessage(message) {
  if (!message || typeof message !== "object") {
    return "invalid response"
  }
  if (message.error) {
    const code = message.error.code !== undefined ? ` code=${message.error.code}` : ""
    const text = message.error.message || "unknown error"
    return `error${code}: ${text}`
  }
  if (message.result !== undefined) {
    return "ok"
  }
  return "no result"
}

async function callRpc(urlObj, session, payload, timeoutMs = 25000) {
  const response = await postJson(urlObj, session.sessionPath, payload)
  if (response.status !== 200 && response.status !== 202) {
    throw new Error(`HTTP ${response.status} for method ${payload.method}`)
  }

  if (payload.id === undefined || payload.id === null) {
    return null
  }

  return session.waitForResponse(payload.id, timeoutMs)
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
  const session = await createSseSession(urlObj)

  const initializeResponse = await callRpc(urlObj, session, {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "gateway-activator", version: "1.0" },
    },
  })
  console.log(`initialize -> ${describeRpcMessage(initializeResponse)}`)

  await callRpc(urlObj, session, {
    jsonrpc: "2.0",
    method: "notifications/initialized",
    params: {},
  })

  for (const server of servers) {
    const requestId = `add-${server}`
    try {
      const httpResponse = await postJson(urlObj, session.sessionPath, {
        jsonrpc: "2.0",
        id: requestId,
        method: "tools/call",
        params: {
          name: "mcp-add",
          arguments: { name: server, activate: true },
        },
      })
      console.log(`mcp-add ${server} -> HTTP ${httpResponse.status}`)
    } catch (error) {
      console.log(`mcp-add ${server} -> request failed (${error.message})`)
    }
    await delay(1500)
  }

  try {
    const toolsResponse = await callRpc(urlObj, session, {
      jsonrpc: "2.0",
      id: 999,
      method: "tools/list",
      params: {},
    })

    if (toolsResponse && toolsResponse.result && Array.isArray(toolsResponse.result.tools)) {
      console.log(`tools/list -> ${toolsResponse.result.tools.length} tools visible after activation`)
    } else {
      console.log(`tools/list -> ${describeRpcMessage(toolsResponse)}`)
    }
  } catch (error) {
    console.log(`tools/list -> request failed (${error.message})`)
  }

  session.close()
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})
