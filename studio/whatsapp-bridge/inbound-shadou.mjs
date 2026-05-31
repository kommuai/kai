/**
 * Run shadou_inbound.py for a tenant workspace (subprocess — one SHADOU_HOME per call).
 */
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";
import { sttServerEnv } from "./stt-server.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function shadouRepoRoot() {
  if (process.env.SHADOU_REPO) return path.resolve(process.env.SHADOU_REPO);
  return path.resolve(__dirname, "../..");
}

function inboundScript() {
  return path.join(shadouRepoRoot(), "studio", "backend", "shadou_inbound.py");
}

function pythonBin() {
  if (process.env.SHADOU_PYTHON) return process.env.SHADOU_PYTHON;
  return "python3";
}

/**
 * @param {{ home: string, userId: string, text: string, contact?: { pushName?: string, phone?: string }, media?: object, timeoutMs?: number }} opts
 */
export function runShadouInbound({ home, userId, text, contact, media, timeoutMs = 120000 }) {
  return new Promise((resolve, reject) => {
    const script = inboundScript();
    const env = {
      ...process.env,
      SHADOU_HOME: home,
      PYTHONPATH: [shadouRepoRoot(), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
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
      cwd: shadouRepoRoot(),
    });

    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      proc.kill("SIGTERM");
      reject(new Error("shadou_inbound timed out"));
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
          reject(new Error(payload.error || stderr || `shadou_inbound failed (${code})`));
          return;
        }
        resolve(payload);
      } catch {
        reject(new Error(stderr || stdout || `shadou_inbound exit ${code}`));
      }
    });

    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}
