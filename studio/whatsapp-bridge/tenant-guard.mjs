/**
 * Per-tenant baileys-antiban integration: health auto-pause, session monitor,
 * LID canonicalization, reconnect throttle, disconnect classification.
 */
import fs from "fs";
import path from "path";
import {
  AntiBan,
  classifyDisconnect,
  getStealthSocketConfig,
  rampPresenceAfterConnect,
  AbortError,
} from "baileys-antiban";

const TIMEZONE = process.env.WA_ANTIBAN_TIMEZONE || "Asia/Kuala_Lumpur";
const PRESET = process.env.WA_ANTIBAN_PRESET || "moderate";
const STEALTH_RAMP = process.env.WA_ANTIBAN_STEALTH_RAMP !== "0";

function antibanStatePath(home) {
  return path.join(home, "data", "whatsapp", "antiban-state.json");
}

function loadWarmUpState(home) {
  const p = antibanStatePath(home);
  try {
    const raw = JSON.parse(fs.readFileSync(p, "utf8"));
    return raw?.warmup ?? raw?.warmUp ?? null;
  } catch {
    return null;
  }
}

function saveWarmUpState(home, warmUpState) {
  if (!warmUpState) return;
  const p = antibanStatePath(home);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  let existing = {};
  try {
    existing = JSON.parse(fs.readFileSync(p, "utf8"));
  } catch {
    /* fresh */
  }
  fs.writeFileSync(p, JSON.stringify({ ...existing, warmup: warmUpState }, null, 2));
}

/**
 * @param {{ home: string, slug: string, log: import('pino').Logger }} opts
 */
export function createTenantGuard({ home, slug, log }) {
  const warmUpState = loadWarmUpState(home);

  /** @type {import('baileys-antiban').AntiBan} */
  let antiban;
  antiban = new AntiBan(
    {
      logging: false,
      rateLimiter: {
        maxPerMinute: Number(process.env.WA_ANTIBAN_MAX_PER_MINUTE || 15),
        maxPerHour: Number(process.env.WA_ANTIBAN_MAX_PER_HOUR || 400),
        maxPerDay: Number(process.env.WA_ANTIBAN_MAX_PER_DAY || 2000),
        minDelayMs: Number(process.env.WHATSAPP_REPLY_DELAY_MIN_MS || 2000),
        maxDelayMs: Number(process.env.WHATSAPP_REPLY_DELAY_MAX_MS || 60000),
        newChatDelayMs: Number(process.env.WA_ANTIBAN_NEW_CHAT_DELAY_MS || 2500),
      },
      warmUp: {
        warmUpDays: Number(process.env.WA_ANTIBAN_WARMUP_DAYS || 7),
        day1Limit: Number(process.env.WA_ANTIBAN_DAY1_LIMIT || 40),
      },
      health: {
        autoPauseAt: process.env.WA_ANTIBAN_AUTO_PAUSE_AT || "high",
        onRiskChange: (status) => {
          log.warn(
            {
              slug,
              risk: status.risk,
              score: status.score,
              paused: antiban.health.isPaused(),
              reasons: status.reasons,
            },
            "antiban health risk change",
          );
          if (antiban.health.isPaused()) {
            log.error(
              { slug, recommendation: status.recommendation },
              "antiban auto-pause active — outbound blocked",
            );
          }
        },
      },
      presence: {
        enabled: true,
        enableTypingModel: true,
        enableCircadianRhythm: true,
        timezone: TIMEZONE,
        typingMaxMs: Number(process.env.WA_ANTIBAN_TYPING_MAX_MS || 10000),
        typingMinMs: 600,
        typingWPM: Number(process.env.WA_ANTIBAN_TYPING_WPM || 45),
      },
      reconnectThrottle: {
        enabled: true,
        rampDurationMs: Number(process.env.WA_ANTIBAN_RECONNECT_RAMP_MS || 60000),
      },
      replyRatio: { enabled: false },
      contactGraph: { enabled: false },
      retryTracker: { enabled: true, spiralThreshold: 3 },
      jidCanonicalizer: {
        enabled: true,
        canonicalizeOutbound: false,
        resolverConfig: { canonical: "pn" },
      },
      sessionStability: {
        enabled: true,
        badMacThreshold: Number(process.env.WA_ANTIBAN_BAD_MAC_THRESHOLD || 3),
        badMacWindowMs: Number(process.env.WA_ANTIBAN_BAD_MAC_WINDOW_MS || 60000),
      },
      timelock: {},
    },
    warmUpState,
  );

  let presenceRampAbort = null;
  let persistTimer = null;

  function persistState() {
    try {
      saveWarmUpState(home, antiban.exportWarmUpState());
    } catch (e) {
      log.debug({ err: e, slug }, "antiban state persist failed");
    }
  }

  function startPersistInterval() {
    if (persistTimer) return;
    persistTimer = setInterval(persistState, 5 * 60_000);
    persistTimer.unref?.();
  }

  function stopPersistInterval() {
    if (persistTimer) clearInterval(persistTimer);
    persistTimer = null;
    persistState();
  }

  function onSessionDegraded(stats) {
    // Log only — do not auto-pause here. Delivery/read receipts were misread as MAC
    // errors when using status codes; health monitor still pauses at high/critical risk.
    log.warn(
      { slug, badMacCount: stats.badMacCount, isDegraded: stats.isDegraded },
      "session decrypt stress (Bad MAC signals) — monitor; outbound not auto-paused",
    );
  }

  function canonicalizeTarget(jid) {
    return antiban.jidCanonicalizer?.canonicalizeTarget(jid) || jid;
  }

  function wireSocketEvents(entry, sock) {
    const guard = antiban;

    const processEvents = async (events) => {
      if (events["connection.update"]) {
        const update = events["connection.update"];
        if (update.connection === "close") {
          const code =
            update.lastDisconnect?.error?.output?.statusCode ??
            update.lastDisconnect?.error?.data?.statusCode;
          guard.onDisconnect(code ?? "unknown");
          guard.destroy?.();
          presenceRampAbort?.abort();
          entry.pausedReason = guard.health.isPaused() ? "health" : entry.pausedReason;
        }
        if (update.connection === "open") {
          guard.onReconnect();
          entry.pausedReason = guard.health.isPaused() ? entry.pausedReason : undefined;
        }
        if (update.reachoutTimeLock) {
          guard.timelock.onTimelockUpdate({
            isActive: update.reachoutTimeLock.isActive,
            timeEnforcementEnds: update.reachoutTimeLock.timeEnforcementEnds,
            enforcementType: update.reachoutTimeLock.enforcementType,
          });
        }
      }

      if (events["messages.update"]) {
        const updates = events["messages.update"];
        for (const update of updates) {
          guard.retryTracker.onMessageUpdate(update);

          const params = update?.update?.messageStubParameters;
          if (Array.isArray(params) && (params.includes(463) || params.includes("463"))) {
            guard.timelock.record463Error();
          }

          // Only count decrypt/MAC failures from real errors — not ACK status codes (3,4,7…).
          if (guard.sessionStability && (update.status === 0 || update.error)) {
            const errMsg = String(
              update.error?.message || update.error?.text || update.update?.message || "",
            ).toLowerCase();
            if (errMsg.includes("bad mac") || errMsg.includes("decryption")) {
              guard.sessionStability.recordDecryptFail(errMsg.includes("bad mac"));
              if (guard.sessionStability.getStats().isDegraded) {
                onSessionDegraded(guard.sessionStability.getStats());
              }
            }
          }
        }
        guard.jidCanonicalizer?.onMessageUpdate(updates);
      }

      if (events["messages.upsert"]) {
        guard.jidCanonicalizer?.onIncomingEvent(events["messages.upsert"]);
        const { messages } = events["messages.upsert"];
        for (const msg of messages || []) {
          const jid = msg.key?.remoteJid;
          if (jid) guard.timelock.registerKnownChat(jid);
          if (!msg.key?.fromMe && jid) {
            guard.onIncomingMessage(jid);
          }
        }
      }
    };

    if (typeof sock.ev.process === "function") {
      sock.ev.process(processEvents);
    } else {
      sock.ev.on("connection.update", (update) => processEvents({ "connection.update": update }));
      sock.ev.on("messages.update", (updates) => processEvents({ "messages.update": updates }));
      sock.ev.on("messages.upsert", (upsert) => processEvents({ "messages.upsert": upsert }));
    }

    startPersistInterval();
  }

  async function rampPresence(sock) {
    if (!STEALTH_RAMP) return;
    presenceRampAbort?.abort();
    presenceRampAbort = new AbortController();
    try {
      await rampPresenceAfterConnect(sock, {
        minDelayMs: Number(process.env.WA_ANTIBAN_STEALTH_MIN_MS || 30000),
        maxDelayMs: Number(process.env.WA_ANTIBAN_STEALTH_MAX_MS || 90000),
        signal: presenceRampAbort.signal,
      });
    } catch (e) {
      if (!(e instanceof AbortError)) {
        log.debug({ err: e, slug }, "stealth presence ramp failed");
      }
    }
  }

  return {
    antiban,
    canonicalizeTarget,
    wireSocketEvents,
    rampPresence,
    stopPersistInterval,
    onSessionDegraded,
    getStats: () => antiban.getStats(),
    isOutboundPaused: () => antiban.health.isPaused(),
    classifyDisconnectCode: (code) => classifyDisconnect(Number(code) || 0),
    stealthSocketConfig: () => getStealthSocketConfig({ os: "Shadou Studio" }),
  };
}
