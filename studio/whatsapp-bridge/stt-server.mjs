/**
 * Keep a warm local Whisper (faster-whisper) sidecar for voice STT — free, no API key.
 */
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('child_process').ChildProcess | null} */
let proc = null;

function kaiRepoRoot() {
  if (process.env.KAI_REPO) return path.resolve(process.env.KAI_REPO);
  return path.resolve(__dirname, "../..");
}

function pythonBin() {
  return process.env.KAI_PYTHON || "python3";
}

function sttPort() {
  return Number(process.env.KAI_STT_SERVER_PORT || 18792);
}

function sttServerUrl() {
  return (process.env.KAI_STT_SERVER_URL || `http://127.0.0.1:${sttPort()}`).replace(/\/$/, "");
}

export function sttServerEnv() {
  return {
    KAI_STT_SERVER_URL: sttServerUrl(),
  };
}

async function waitForHealth(timeoutMs = 120000) {
  const url = `${sttServerUrl()}/health`;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const resp = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (resp.ok) {
        const data = await resp.json();
        if (data?.ok) return true;
      }
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

/**
 * Start STT sidecar if not already running (loads Whisper model once).
 */
export async function ensureSttServer(log = console) {
  if (proc && !proc.killed) {
    return waitForHealth(5000);
  }

  const port = sttPort();
  const root = kaiRepoRoot();
  const env = {
    ...process.env,
    PYTHONPATH: [root, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
  };

  proc = spawn(pythonBin(), ["-m", "kai.media.stt_server", "--port", String(port)], {
    env,
    cwd: root,
    stdio: ["ignore", "pipe", "pipe"],
  });

  proc.stdout?.on("data", (d) => log.info?.({ stt: d.toString().trim() }, "stt server"));
  proc.stderr?.on("data", (d) => log.warn?.({ stt: d.toString().trim() }, "stt server stderr"));
  proc.on("exit", (code) => {
    log.warn?.({ code }, "stt server exited");
    proc = null;
  });

  const ok = await waitForHealth();
  if (!ok) {
    log.error?.("STT server failed to become ready — voice may fall back or fail");
  }
  return ok;
}

export function stopSttServer() {
  if (!proc || proc.killed) return;
  proc.kill("SIGTERM");
  proc = null;
}
