/**
 * Baileys WhatsApp bridge — QR linking and multi-file auth state on disk.
 * Studio backend calls this service; one active link session per auth_dir.
 */
import express from "express";
import fs from "fs";
import path from "path";
import QRCode from "qrcode";
import pino from "pino";
import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";
import {
  pauseAuthDir,
  resumeAuthDir,
  sendWorkerOutbound,
  startWorkerManager,
  workerStatus,
} from "./worker-manager.mjs";

// Default 18791 — avoid 8090/8091 (often used by Cursor bridge / nginx on this host).
const PORT = Number(process.env.WHATSAPP_BRIDGE_PORT || 18791);
const HOST = process.env.WHATSAPP_BRIDGE_HOST || "127.0.0.1";
const MAX_RECONNECTS = Number(process.env.WHATSAPP_BRIDGE_MAX_RECONNECTS || "8");

/** @type {Map<string, LinkEntry>} */
const links = new Map();

const log = pino({ level: process.env.LOG_LEVEL || "info" });

/**
 * @typedef {Object} LinkEntry
 * @property {string} authDir
 * @property {string} status
 * @property {string} [qrDataUrl]
 * @property {string} [phone]
 * @property {string} [error]
 * @property {any} [sock]
 * @property {number} [reconnectAttempts]
 * @property {boolean} [reconnectScheduled]
 */

function newLinkId() {
  return `link_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function disconnectCode(lastDisconnect) {
  const err = lastDisconnect?.error;
  return err?.output?.statusCode ?? err?.data?.statusCode;
}

function friendlyDisconnectError(code, rawMessage) {
  if (code === DisconnectReason.loggedOut) {
    return "Logged out from WhatsApp. Unlink old devices in WhatsApp settings and try again.";
  }
  if (code === DisconnectReason.badSession) {
    return "Session invalid. Use Retry linking to start fresh.";
  }
  if (code === DisconnectReason.connectionReplaced) {
    return "Another WhatsApp Web session replaced this link. Try again.";
  }
  if (code === DisconnectReason.forbidden) {
    return "WhatsApp rejected the connection. Check your account status.";
  }
  if (code === DisconnectReason.restartRequired) {
    return rawMessage || "Reconnecting after scan…";
  }
  return rawMessage || "Connection closed";
}

function shouldReconnect(code) {
  if (code == null) return true;
  if (code === DisconnectReason.loggedOut) return false;
  if (code === DisconnectReason.badSession) return false;
  if (code === DisconnectReason.forbidden) return false;
  return true;
}

function publicStatus(entry) {
  return {
    status: entry.status,
    qr_data_url: entry.qrDataUrl || null,
    phone: entry.phone || null,
    error: entry.error || null,
  };
}

function findLinkIdByAuthDir(authDir) {
  const resolved = path.resolve(authDir);
  for (const [id, entry] of links) {
    if (entry.authDir === resolved && !["disconnected", "error"].includes(entry.status)) {
      return id;
    }
  }
  return null;
}

function endSocket(entry) {
  if (!entry.sock) return;
  try {
    entry.sock.end(undefined);
  } catch {
    /* ignore */
  }
  entry.sock = undefined;
}

/**
 * Create or recreate Baileys socket for an entry (QR pairing + post-scan reconnect).
 */
async function runSocket(linkId, entry) {
  const resolved = entry.authDir;
  fs.mkdirSync(resolved, { recursive: true });

  const { version } = await fetchLatestBaileysVersion();
  const { state, saveCreds } = await useMultiFileAuthState(resolved);

  if (state.creds?.registered) {
    entry.status = "connected";
    entry.phone = state.creds.me?.id?.split(":")[0] || state.creds.me?.id || "";
    entry.qrDataUrl = undefined;
    entry.error = null;
    return;
  }

  endSocket(entry);

  const sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: "silent" }),
    printQRInTerminal: false,
    syncFullHistory: false,
    markOnlineOnConnect: false,
  });
  entry.sock = sock;

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;
    const code = disconnectCode(lastDisconnect);

    if (qr) {
      entry.status = "qr";
      entry.error = null;
      entry.reconnectAttempts = 0;
      try {
        entry.qrDataUrl = await QRCode.toDataURL(qr, { margin: 1, width: 280 });
      } catch (e) {
        entry.error = String(e);
        entry.status = "error";
      }
    }

    if (connection === "connecting") {
      if (entry.status !== "connected") {
        entry.status = "connecting";
      }
    }

    if (connection === "open") {
      entry.status = "connected";
      entry.error = null;
      const me = sock.user;
      entry.phone = me?.id?.split(":")[0] || me?.id || "";
      entry.qrDataUrl = undefined;
      entry.reconnectAttempts = 0;
      try {
        await saveCreds();
      } catch {
        /* ignore */
      }
      endSocket(entry);
      log.info({ linkId, phone: entry.phone }, "WhatsApp linked");
      resumeAuthDir(resolved);
      return;
    }

    if (connection === "close") {
      log.info({ linkId, code, priorStatus: entry.status }, "connection closed");

      if (entry.status === "connected") {
        return;
      }

      endSocket(entry);

      if (!shouldReconnect(code)) {
        entry.status = code === DisconnectReason.loggedOut ? "disconnected" : "error";
        entry.error = friendlyDisconnectError(code, lastDisconnect?.error?.message);
        return;
      }

      const attempts = (entry.reconnectAttempts || 0) + 1;
      entry.reconnectAttempts = attempts;
      if (attempts > MAX_RECONNECTS) {
        entry.status = "error";
        entry.error = "Too many reconnect attempts. Use Retry linking.";
        return;
      }

      if (entry.reconnectScheduled) {
        return;
      }
      entry.reconnectScheduled = true;

      const delayMs = code === DisconnectReason.restartRequired ? 400 : 1500;
      entry.status = "connecting";
      if (code === DisconnectReason.restartRequired) {
        entry.error = null;
        entry.qrDataUrl = undefined;
      } else {
        entry.error = friendlyDisconnectError(code, lastDisconnect?.error?.message);
      }

      setTimeout(async () => {
        entry.reconnectScheduled = false;
        if (entry.status === "connected") return;
        try {
          await runSocket(linkId, entry);
        } catch (e) {
          entry.status = "error";
          entry.error = String(e?.message || e);
          log.error({ err: e, linkId }, "reconnect failed");
        }
      }, delayMs);
    }
  });
}

async function startLink(authDir) {
  const resolved = path.resolve(authDir);
  pauseAuthDir(resolved);
  const existing = findLinkIdByAuthDir(resolved);
  if (existing) {
    return existing;
  }

  for (const [id, e] of links) {
    if (e.authDir === resolved) {
      endSocket(e);
      links.delete(id);
    }
  }

  const linkId = newLinkId();
  /** @type {LinkEntry} */
  const entry = { authDir: resolved, status: "starting", reconnectAttempts: 0 };
  links.set(linkId, entry);

  try {
    await runSocket(linkId, entry);
  } catch (e) {
    entry.status = "error";
    entry.error = String(e?.message || e);
    log.error({ err: e, authDir: resolved }, "startLink failed");
  }

  return linkId;
}

const app = express();
app.use(express.json({ limit: "1mb" }));

app.get("/health", (_req, res) => {
  res.json({ ok: true, worker: workerStatus() });
});

app.post("/v1/link/start", async (req, res) => {
  const authDir = req.body?.auth_dir;
  if (!authDir || typeof authDir !== "string") {
    return res.status(400).json({ detail: "auth_dir required" });
  }
  const linkId = await startLink(authDir);
  const entry = links.get(linkId);
  res.json({ link_id: linkId, ...publicStatus(entry) });
});

app.get("/v1/link/:linkId/status", (req, res) => {
  const entry = links.get(req.params.linkId);
  if (!entry) return res.status(404).json({ detail: "link not found" });
  res.json(publicStatus(entry));
});

app.post("/v1/link/:linkId/stop", async (req, res) => {
  const entry = links.get(req.params.linkId);
  if (!entry) return res.status(404).json({ detail: "link not found" });
  endSocket(entry);
  const authDir = entry.authDir;
  links.delete(req.params.linkId);
  if (authDir) resumeAuthDir(authDir);
  res.json({ ok: true });
});

app.post("/v1/worker/send", async (req, res) => {
  const slug = req.body?.tenant_slug;
  const userId = req.body?.user_id;
  const text = req.body?.text;
  if (!slug || typeof slug !== "string") {
    return res.status(400).json({ detail: "tenant_slug required" });
  }
  if (!userId || typeof userId !== "string") {
    return res.status(400).json({ detail: "user_id required" });
  }
  if (!text || typeof text !== "string") {
    return res.status(400).json({ detail: "text required" });
  }
  try {
    const result = await sendWorkerOutbound({ slug, userId, text });
    if (!result.ok) {
      const code =
        result.error === "tenant_worker_not_found" || result.error === "whatsapp_not_connected"
          ? 503
          : 400;
      return res.status(code).json(result);
    }
    res.json(result);
  } catch (e) {
    log.error({ err: e, slug, userId }, "worker send failed");
    res.status(502).json({ ok: false, error: String(e?.message || e) });
  }
});

process.on("uncaughtException", (err) => {
  log.error({ err }, "uncaught exception — bridge stays up");
});

process.on("unhandledRejection", (reason) => {
  log.error({ err: reason }, "unhandled rejection — bridge stays up");
});

app.listen(PORT, HOST, () => {
  log.info(`WhatsApp bridge listening on http://${HOST}:${PORT}`);
  startWorkerManager();
});
