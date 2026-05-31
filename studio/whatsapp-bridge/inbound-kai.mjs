/**
 * Run kai_inbound.py for a tenant workspace (subprocess — one KAI_HOME per call).
 */
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";
import { sttServerEnv } from "./stt-server.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function kaiRepoRoot() {
  if (process.env.KAI_REPO) return path.resolve(process.env.KAI_REPO);
  return path.resolve(__dirname, "../..");
}

function inboundScript() {
  return path.join(kaiRepoRoot(), "studio", "backend", "kai_inbound.py");
}

function pythonBin() {
  if (process.env.KAI_PYTHON) return process.env.KAI_PYTHON;
  return "python3";
}

/**
 * @param {{ home: string, userId: string, text: string, contact?: { pushName?: string, phone?: string }, media?: object, timeoutMs?: number }} opts
 */
export function runKaiInbound({ home, userId, text, contact, media, timeoutMs = 120000 }) {
  return new Promise((resolve, reject) => {
    const script = inboundScript();
    const env = {
      ...process.env,
      KAI_HOME: home,
      PYTHONPATH: [kaiRepoRoot(), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
      ...sttServerEnv(),
    };
    const payload = {};
    if (contact && (contact.pushName || contact.phone)) {
      payload.contact = contact;
    }
    if (media && typeof media === "object") {
      payload.media = media;
    }
    const args = [script, home, userId, text];
    if (Object.keys(payload).length) {
      args.push(JSON.stringify(payload));
    }

    const proc = spawn(pythonBin(), args, {
      env,
      cwd: kaiRepoRoot(),
    });

    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      proc.kill("SIGTERM");
      reject(new Error("kai_inbound timed out"));
    }, timeoutMs);

    proc.stdout.on("data", (d) => {
      stdout += d.toString();
    });
    proc.stderr.on("data", (d) => {
      stderr += d.toString();
    });

    proc.on("close", (code) => {
      clearTimeout(timer);
      const line = stdout.trim().split("\n").pop() || "";
      try {
        const payload = JSON.parse(line);
        if (!payload.ok) {
          reject(new Error(payload.error || stderr || `kai_inbound failed (${code})`));
          return;
        }
        resolve(payload);
      } catch {
        reject(new Error(stderr || stdout || `kai_inbound exit ${code}`));
      }
    });

    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}
