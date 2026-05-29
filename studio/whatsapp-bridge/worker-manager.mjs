/**
 * Multi-tenant persistent Baileys connections for inbound/outbound WhatsApp messaging.
 */
import fs from "fs";
import path from "path";
import pino from "pino";
import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";
import { discoverWhatsAppTenants } from "./tenant-discovery.mjs";
import { runKaiInbound } from "./inbound-kai.mjs";
import { persistContactMeta } from "./contact-persist.mjs";
import {
  contactMetaFromMessage,
  extractTextFromWAMessage,
  resolveInboundDm,
  resolveOutboundChatJid,
  userIdFromContactJid,
} from "./message-text.mjs";

const log = pino({ level: process.env.LOG_LEVEL || "info" });
const SCAN_MS = Number(process.env.WHATSAPP_WORKER_SCAN_MS || 15000);
const MAX_RECONNECTS = Number(process.env.WHATSAPP_WORKER_MAX_RECONNECTS || "12");
const WORKER_ENABLED = process.env.WHATSAPP_WORKER_ENABLED !== "0";

/** @type {Map<string, WorkerTenant>} */
const tenants = new Map();
/** Auth dirs reserved for QR linking (bridge server.mjs). */
const pausedAuthDirs = new Set();
/** Serialize inbound handling per tenant+user */
const inboundChains = new Map();
/** Replies generated while socket was down — flushed on reconnect. */
const pendingOutbound = new Map();
/** @type {ReturnType<typeof setInterval> | null} */
let scanTimer = null;

/**
 * @typedef {Object} WorkerTenant
 * @property {string} key
 * @property {string} slug
 * @property {string} home
 * @property {string} authDir
 * @property {string} state
 * @property {string} [phone]
 * @property {string} [error]
 * @property {any} [sock]
 * @property {number} reconnectAttempts
 * @property {boolean} reconnectScheduled
 * @property {number} [configMtime]
 */

function disconnectCode(lastDisconnect) {
  const err = lastDisconnect?.error;
  return err?.output?.statusCode ?? err?.data?.statusCode;
}

function shouldReconnect(code) {
  if (code == null) return true;
  if (code === DisconnectReason.loggedOut) return false;
  if (code === DisconnectReason.badSession) return false;
  if (code === DisconnectReason.forbidden) return false;
  return true;
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

function workspaceMtime(home) {
  try {
    return fs.statSync(path.join(home, "workspace.yaml")).mtimeMs;
  } catch {
    return 0;
  }
}

export function pauseAuthDir(authDir) {
  const resolved = path.resolve(authDir);
  pausedAuthDirs.add(resolved);
  for (const [key, entry] of tenants) {
    if (path.resolve(entry.authDir) === resolved) {
      log.info({ authDir: resolved, slug: entry.slug }, "pausing worker for QR link");
      stopTenant(key);
      break;
    }
  }
}

export function resumeAuthDir(authDir) {
  pausedAuthDirs.delete(path.resolve(authDir));
}

function stopTenant(key) {
  const entry = tenants.get(key);
  if (!entry) return;
  endSocket(entry);
  tenants.delete(key);
}

async function enqueueInbound(chainKey, fn) {
  const prev = inboundChains.get(chainKey) || Promise.resolve();
  const next = prev
    .then(() => fn())
    .catch((e) => {
      log.error({ err: e, chainKey }, "inbound handler error");
    });
  inboundChains.set(chainKey, next);
  return next;
}

async function handleInboundMessage(entry, chatJid, userId, text, msgId, contact = {}) {
  const chainKey = `${entry.slug}:${userId}`;

  await enqueueInbound(chainKey, async () => {
    log.info({ slug: entry.slug, userId, chatJid, msgId, len: text.length }, "inbound WhatsApp");
    const result = await runKaiInbound({
      home: entry.home,
      userId,
      text: text || "",
      contact,
    });

    if (!result.ok) {
      log.error({ slug: entry.slug, userId, error: result.error }, "kai_inbound failed");
      return;
    }

    if (result.skip_send || !result.answer) {
      log.info({ slug: entry.slug, userId, decision: result.decision }, "no reply to send");
      return;
    }

    if (!entry.sock) {
      pendingOutbound.set(chainKey, { chatJid, answer: result.answer });
      log.warn({ slug: entry.slug, userId }, "socket gone before send — queued for reconnect");
      return;
    }

    await sendWhatsAppText(entry, chatJid, result.answer, chainKey);
  });
}

function loadContactDirectory(home) {
  const p = path.join(home, "data", "whatsapp", "contact-directory.json");
  try {
    const raw = JSON.parse(fs.readFileSync(p, "utf8"));
    return raw && typeof raw === "object" ? raw : {};
  } catch {
    return {};
  }
}

/**
 * Send a human agent reply from Studio to a WhatsApp DM.
 * @returns {Promise<{ ok: boolean, error?: string, chat_jid?: string, queued?: boolean }>}
 */
export async function sendWorkerOutbound({ slug, userId, text }) {
  const entry = [...tenants.values()].find((t) => t.slug === slug);
  if (!entry) {
    return { ok: false, error: "tenant_worker_not_found" };
  }
  if (entry.state !== "connected" || !entry.sock) {
    return { ok: false, error: "whatsapp_not_connected" };
  }

  const body = String(text || "").trim();
  if (!body) {
    return { ok: false, error: "empty_message" };
  }

  const uid = String(userId || "").trim();
  if (!uid) {
    return { ok: false, error: "user_id_required" };
  }

  const directory = loadContactDirectory(entry.home);
  const chatJid = resolveOutboundChatJid(uid, directory);
  if (!chatJid) {
    return { ok: false, error: "invalid_user_id" };
  }

  const chainKey = `${entry.slug}:${uid}`;
  const hadPending = pendingOutbound.has(chainKey);
  await sendWhatsAppText(entry, chatJid, body, chainKey);
  const queued = hadPending || pendingOutbound.has(chainKey);

  log.info({ slug: entry.slug, userId: uid, chatJid, queued }, "studio outbound WhatsApp");
  return { ok: true, chat_jid: chatJid, queued };
}

async function sendWhatsAppText(entry, chatJid, text, chainKey) {
  if (!entry.sock) {
    pendingOutbound.set(chainKey, { chatJid, answer: text });
    return;
  }
  try {
    await entry.sock.sendMessage(chatJid, { text });
    pendingOutbound.delete(chainKey);
    log.info({ slug: entry.slug, chatJid, outLen: text.length }, "sent WhatsApp reply");
  } catch (e) {
    pendingOutbound.set(chainKey, { chatJid, answer: text });
    log.error({ err: e, slug: entry.slug, chatJid }, "sendMessage failed — queued for retry");
  }
}

async function flushPendingOutbound(entry) {
  if (!entry.sock) return;
  const prefix = `${entry.slug}:`;
  for (const [key, payload] of [...pendingOutbound.entries()]) {
    if (!key.startsWith(prefix)) continue;
    try {
      await entry.sock.sendMessage(payload.chatJid, { text: payload.answer });
      pendingOutbound.delete(key);
      log.info({ slug: entry.slug, chatJid: payload.chatJid }, "sent queued WhatsApp reply");
    } catch (e) {
      log.error({ err: e, slug: entry.slug, chatJid: payload.chatJid }, "queued reply send failed");
    }
  }
}

async function runWorkerSocket(entry) {
  const resolved = entry.authDir;
  if (pausedAuthDirs.has(resolved)) {
    entry.state = "paused_linking";
    return;
  }

  fs.mkdirSync(resolved, { recursive: true });
  const { version } = await fetchLatestBaileysVersion();
  const { state, saveCreds } = await useMultiFileAuthState(resolved);

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
  entry.state = "connecting";

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("contacts.update", (updates) => {
    for (const u of updates) {
      const notify = (u.notify || u.name || u.verifiedName || "").trim();
      if (!u.id) continue;
      const userId = userIdFromContactJid(u.id);
      if (!userId) continue;
      const phoneDigits = userId.replace(/\D/g, "");
      persistContactMeta(entry.home, userId, {
        pushName: notify,
        verifiedName: u.verifiedName || "",
        phone: phoneDigits.length >= 8 && phoneDigits.length <= 13 ? phoneDigits : "",
      });
    }
  });

  sock.ev.on("chats.phoneNumberShare", ({ lid, jid }) => {
    if (!lid || !jid) return;
    const userId = userIdFromContactJid(lid);
    const phone = (jid.split("@")[0] || "").trim();
    if (!userId || !/^\d{8,15}$/.test(phone)) return;
    persistContactMeta(entry.home, userId, { phone });
    log.info({ slug: entry.slug, userId, phone }, "stored phone from phoneNumberShare");
  });

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    // Only live messages — avoid auto-replying to history sync (type "append").
    if (type !== "notify") return;
    for (const msg of messages) {
      if (!msg.message || msg.key.fromMe) continue;
      const dm = resolveInboundDm(msg.key);
      if (!dm) {
        log.debug(
          { slug: entry.slug, remoteJid: msg.key.remoteJid, alt: msg.key.remoteJidAlt, type },
          "skip non-dm message",
        );
        continue;
      }

      const text = extractTextFromWAMessage(msg);
      const msgId = msg.key.id || "";
      const contact = contactMetaFromMessage(msg, dm);
      if (contact.pushName || contact.phone) {
        persistContactMeta(entry.home, dm.userId, contact);
      }
      try {
        await handleInboundMessage(entry, dm.chatJid, dm.userId, text, msgId, contact);
      } catch (e) {
        log.error(
          { err: e, slug: entry.slug, chatJid: dm.chatJid, userId: dm.userId },
          "handle inbound failed",
        );
      }
    }
  });

  sock.ev.on("connection.update", async (update) => {
    try {
      await handleConnectionUpdate(entry, sock, resolved, saveCreds, update);
    } catch (e) {
      log.error({ err: e, slug: entry.slug }, "connection.update handler error");
      entry.state = "error";
      entry.error = String(e?.message || e);
    }
  });
}

async function handleConnectionUpdate(entry, sock, resolved, saveCreds, update) {
    const { connection, lastDisconnect } = update;
    const code = disconnectCode(lastDisconnect);

    if (connection === "open") {
      entry.state = "connected";
      entry.error = undefined;
      entry.reconnectAttempts = 0;
      const me = sock.user;
      entry.phone = me?.id?.split(":")[0] || me?.id || entry.phone;
      log.info({ slug: entry.slug, phone: entry.phone }, "worker connected");
      try {
        await saveCreds();
      } catch {
        /* ignore */
      }
      await flushPendingOutbound(entry);
      return;
    }

    if (connection !== "close") return;

    log.info({ slug: entry.slug, code, state: entry.state }, "worker connection closed");
    endSocket(entry);

    if (pausedAuthDirs.has(resolved)) {
      entry.state = "paused_linking";
      return;
    }

    if (!shouldReconnect(code)) {
      entry.state = code === DisconnectReason.loggedOut ? "logged_out" : "error";
      entry.error = lastDisconnect?.error?.message || "Connection closed";
      return;
    }

    const attempts = (entry.reconnectAttempts || 0) + 1;
    entry.reconnectAttempts = attempts;
    if (attempts > MAX_RECONNECTS) {
      entry.state = "error";
      entry.error = "Too many reconnect attempts";
      return;
    }

    if (entry.reconnectScheduled) return;
    entry.reconnectScheduled = true;
    entry.state = "reconnecting";

    const delayMs = code === DisconnectReason.restartRequired ? 500 : 2000;
    setTimeout(async () => {
      entry.reconnectScheduled = false;
      if (pausedAuthDirs.has(resolved)) return;
      if (!tenants.has(entry.key)) return;
      try {
        await runWorkerSocket(entry);
      } catch (e) {
        entry.state = "error";
        entry.error = String(e?.message || e);
        log.error({ err: e, slug: entry.slug }, "worker reconnect failed");
      }
    }, delayMs);
}

async function startTenant(def) {
  if (pausedAuthDirs.has(def.authDir)) return;

  let entry = tenants.get(def.key);
  if (!entry) {
    entry = {
      key: def.key,
      slug: def.slug,
      home: def.home,
      authDir: def.authDir,
      state: "starting",
      phone: def.phone,
      reconnectAttempts: 0,
      reconnectScheduled: false,
      configMtime: workspaceMtime(def.home),
    };
    tenants.set(def.key, entry);
  } else {
    entry.home = def.home;
    entry.authDir = def.authDir;
    entry.configMtime = workspaceMtime(def.home);
  }

  if (entry.state === "logged_out") return;

  if (entry.sock && entry.state === "connected") return;

  if (entry.sock) return;

  try {
    await runWorkerSocket(entry);
  } catch (e) {
    entry.state = "error";
    entry.error = String(e?.message || e);
    log.error({ err: e, slug: def.slug }, "worker start failed");
  }
}

function syncTenants() {
  if (!WORKER_ENABLED) return;

  const discovered = discoverWhatsAppTenants();
  const wantKeys = new Set();

  for (const def of discovered) {
    wantKeys.add(def.key);
    const mtime = workspaceMtime(def.home);
    const existing = tenants.get(def.key);
    if (existing && existing.state === "connected" && existing.configMtime === mtime) {
      continue;
    }
    if (existing && existing.configMtime !== mtime) {
      log.info({ slug: def.slug }, "workspace.yaml changed — restarting worker socket");
      stopTenant(def.key);
    }
    startTenant(def);
  }

  for (const [key, entry] of tenants) {
    if (!wantKeys.has(key)) {
      log.info({ slug: entry.slug }, "tenant no longer configured for WhatsApp — stopping worker");
      stopTenant(key);
    }
  }
}

export function workerStatus() {
  return {
    enabled: WORKER_ENABLED,
    scan_interval_ms: SCAN_MS,
    paused_linking: [...pausedAuthDirs],
    tenants: [...tenants.values()].map((t) => ({
      slug: t.slug,
      state: t.state,
      phone: t.phone || null,
      error: t.error || null,
      home: t.home,
    })),
  };
}

export function startWorkerManager() {
  if (!WORKER_ENABLED) {
    log.info("WhatsApp worker disabled (WHATSAPP_WORKER_ENABLED=0)");
    return;
  }
  log.info({ scanMs: SCAN_MS }, "starting WhatsApp worker manager");
  syncTenants();
  scanTimer = setInterval(syncTenants, SCAN_MS);
}

export function stopWorkerManager() {
  if (scanTimer) clearInterval(scanTimer);
  scanTimer = null;
  for (const key of [...tenants.keys()]) {
    stopTenant(key);
  }
}
