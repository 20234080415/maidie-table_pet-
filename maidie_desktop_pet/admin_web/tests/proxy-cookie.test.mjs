import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import http from "node:http";
import test from "node:test";
import { fileURLToPath } from "node:url";

const TEST_COOKIE =
  "maidie_admin_session=proxy-test-token; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=28800";

function listen(server) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve(server.address().port));
  });
}

function close(server) {
  return new Promise((resolve, reject) => {
    server.closeAllConnections?.();
    server.close((error) => error ? reject(error) : resolve());
  });
}

function stop(child) {
  if (child.exitCode !== null) return Promise.resolve();
  return new Promise((resolve) => {
    child.once("exit", resolve);
    child.kill();
    const timer = setTimeout(resolve, 2_000);
    timer.unref();
  });
}

async function waitForServer(url, processOutput) {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.status < 500) return;
    } catch {
      // The production server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`production server did not start:\n${processOutput.join("")}`);
}

test("admin proxy preserves the session cookie and sends it back upstream", {
  timeout: 30_000,
}, async () => {
  const upstream = http.createServer((request, response) => {
    if (request.url === "/login") {
      response.writeHead(200, {
        "Content-Type": "application/json",
        "X-Maidie-Admin-Set-Cookie": TEST_COOKIE,
      });
      response.end('{"success":true}');
      return;
    }
    if (request.url === "/overview") {
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ cookie: request.headers.cookie ?? "" }));
      return;
    }
    response.writeHead(404).end();
  });
  const upstreamPort = await listen(upstream);

  const sitePort = 19431;
  const output = [];
  const site = spawn(
    process.execPath,
    ["node_modules/vinext/dist/cli.js", "start", "-p", String(sitePort)],
    {
    cwd: fileURLToPath(new URL("..", import.meta.url)),
    env: {
      ...process.env,
      MAIDIE_ADMIN_API_URL: `http://127.0.0.1:${upstreamPort}`,
      MAIDIE_ADMIN_PROXY_SECRET: "integration-test-secret",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  site.stdout.on("data", (chunk) => output.push(chunk.toString()));
  site.stderr.on("data", (chunk) => output.push(chunk.toString()));

  try {
    const baseUrl = `http://127.0.0.1:${sitePort}`;
    await waitForServer(baseUrl, output);
    const login = await fetch(`${baseUrl}/api/admin/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: '{"password":"not-sent-upstream-by-this-mock"}',
    });
    assert.equal(login.status, 200);
    const setCookie = login.headers.get("set-cookie");
    assert.ok(setCookie?.includes("maidie_admin_session=proxy-test-token"));

    const cookie = setCookie.split(";", 1)[0];
    const overview = await fetch(`${baseUrl}/api/admin/overview`, {
      headers: { Cookie: cookie },
    });
    assert.equal(overview.status, 200);
    assert.equal((await overview.json()).cookie, cookie);
  } finally {
    await stop(site);
    await close(upstream);
  }
});
