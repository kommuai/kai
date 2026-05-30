/**
 * Human-like inbound bot replies: antiban gaussian delay + WPM typing presence.
 * Uses Baileys composing/paused only — no decoy characters sent to the user.
 */
import pino from "pino";

const log = pino({ level: process.env.LOG_LEVEL || "info" });

export const HUMAN_REPLY_ENABLED = process.env.WHATSAPP_REPLY_HUMANIZE !== "0";
const MAX_TYPING_MS = Number(process.env.WA_ANTIBAN_TYPING_MAX_MS || 10000);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function planTotalMs(plan) {
  return (plan || []).reduce((sum, step) => sum + (step.durationMs || 0), 0);
}

/** Shrink typing plan so total duration does not exceed maxMs. */
function capTypingPlan(plan, maxMs) {
  const total = planTotalMs(plan);
  if (!plan?.length || total <= maxMs) return plan;
  const scale = maxMs / total;
  return plan.map((step) => ({
    ...step,
    durationMs: Math.max(300, Math.floor((step.durationMs || 0) * scale)),
  }));
}

/**
 * Inbound automatic reply pacing (not Studio manual sends).
 *
 * @returns {Promise<boolean>} true if the message was delivered to WhatsApp
 */
export async function humanizedWhatsAppSend({ entry, chatJid, text, chainKey, sendCore }) {
  const guard = entry.guard;
  // Use the inbound JID as-is (@lid). Rewriting to @s.whatsapp.net breaks E2E for many chats.
  const deliverJid = chatJid;

  if (!HUMAN_REPLY_ENABLED || !guard) {
    const r = await sendCore(entry, deliverJid, text, chainKey);
    return r?.sent === true;
  }

  const { antiban } = guard;

  if (antiban.health.isPaused()) {
    log.error(
      { slug: entry.slug, chatJid: deliverJid, risk: antiban.getStats().health?.risk },
      "outbound paused by antiban health — skipping bot reply",
    );
    return false;
  }

  const decision = await antiban.beforeSend(deliverJid, text);
  if (!decision.allowed) {
    log.warn(
      { slug: entry.slug, chatJid: deliverJid, reason: decision.reason },
      "antiban blocked inbound reply",
    );
    return false;
  }

  const choreo = antiban.presence;
  let typingPlan = choreo.computeTypingPlan(text.length);
  const typingBudgetMs = Math.min(decision.delayMs, MAX_TYPING_MS);
  typingPlan = capTypingPlan(typingPlan, typingBudgetMs);
  const typingMs = planTotalMs(typingPlan);
  const extraDelayMs = Math.max(0, decision.delayMs - typingMs);

  log.info(
    {
      slug: entry.slug,
      chatJid: deliverJid,
      gaussianDelayMs: decision.delayMs,
      typingMs,
      extraDelayMs,
    },
    "humanized reply started",
  );

  if (entry.sock && typingPlan.length > 0) {
    try {
      await choreo.executeTypingPlan(entry.sock, deliverJid, typingPlan);
    } catch (e) {
      log.debug({ err: e, slug: entry.slug }, "typing plan failed");
    }
  }

  if (extraDelayMs > 0) {
    await sleep(extraDelayMs);
  }

  if (antiban.health.isPaused()) {
    log.error({ slug: entry.slug, chatJid: deliverJid }, "outbound paused after typing — reply not sent");
    return false;
  }

  const result = await sendCore(entry, deliverJid, text, chainKey);
  if (result?.sent) {
    log.info({ slug: entry.slug, chatJid: deliverJid }, "humanized reply delivered");
    return true;
  }

  log.error(
    { slug: entry.slug, chatJid: deliverJid, reason: result?.reason },
    "humanized reply not delivered to WhatsApp (may still appear in Studio inbox)",
  );
  return false;
}

/**
 * Studio / direct outbound: respect pause + timelock + rate limits; skip WPM typing theatre.
 */
export async function guardedWhatsAppSend({ entry, chatJid, text, chainKey, sendCore }) {
  const guard = entry.guard;
  const deliverJid = chatJid;

  if (!guard) {
    const r = await sendCore(entry, deliverJid, text, chainKey);
    return r?.sent === true;
  }

  const { antiban } = guard;

  if (antiban.health.isPaused()) {
    throw new Error("whatsapp_outbound_paused_health");
  }

  const decision = await antiban.beforeSend(deliverJid, text);
  if (!decision.allowed) {
    throw new Error(decision.reason || "whatsapp_outbound_blocked");
  }

  const studioDelay = process.env.WHATSAPP_STUDIO_ANTIBAN_DELAY === "1" ? decision.delayMs : 0;
  if (studioDelay > 0) {
    await sleep(studioDelay);
  }

  const result = await sendCore(entry, deliverJid, text, chainKey);
  if (!result?.sent) {
    throw new Error(result?.reason || "whatsapp_send_failed");
  }
  return true;
}
