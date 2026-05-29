import { extractMessageContent, getContentType } from "@whiskeysockets/baileys";

/** @returns {string} */
export function extractTextFromWAMessage(msg) {
  if (!msg?.message) return "";
  const content = extractMessageContent(msg.message);
  if (!content) return "";
  if (typeof content === "string") return content;
  if (content.conversation) return content.conversation;
  if (content.extendedTextMessage?.text) return content.extendedTextMessage.text;
  if (content.imageMessage?.caption) return content.imageMessage.caption;
  if (content.videoMessage?.caption) return content.videoMessage.caption;
  return "";
}

/**
 * Resolve DM chat JID + stable user id for sessions (phone when available).
 * WhatsApp often sends remoteJid as @lid with phone in remoteJidAlt (Baileys 6.7+).
 *
 * @returns {{ chatJid: string, userId: string } | null}
 */
export function resolveInboundDm(key) {
  if (!key || typeof key !== "object") return null;
  const remote = key.remoteJid;
  const alt = key.remoteJidAlt;
  if (!remote || typeof remote !== "string") return null;

  if (remote.endsWith("@g.us") || remote.includes("@broadcast") || remote.endsWith("@newsletter")) {
    return null;
  }

  if (remote.endsWith("@s.whatsapp.net")) {
    const userId = remote.split("@")[0] || remote;
    return { chatJid: remote, userId };
  }

  if (remote.endsWith("@lid")) {
    let userId = remote.split("@")[0] || remote;
    if (typeof alt === "string" && alt.endsWith("@s.whatsapp.net")) {
      userId = alt.split("@")[0] || userId;
    }
    return { chatJid: remote, userId };
  }

  return null;
}

export function userIdFromJid(jid) {
  return jid.split("@")[0] || jid;
}

/**
 * Resolve DM chat JID for outbound Studio/agent messages.
 * Prefer @lid when the contact directory or user id indicates a LID session key.
 *
 * @param {string} userId — session user id (phone digits or WhatsApp @lid key)
 * @param {Record<string, object>} [directory] — tenant contact-directory.json
 * @returns {string | null}
 */
export function resolveOutboundChatJid(userId, directory = {}) {
  const uid = String(userId || "").trim();
  if (!uid) return null;

  if (uid.includes("@")) {
    if (uid.endsWith("@s.whatsapp.net") || uid.endsWith("@lid")) {
      return uid;
    }
    return null;
  }

  const digits = uid.replace(/\D/g, "");

  if (directory && typeof directory === "object" && directory[uid]) {
    return `${uid}@lid`;
  }

  if (isLikelyLidDigits(digits)) {
    return `${uid}@lid`;
  }

  if (digits.length >= 8 && digits.length <= 15) {
    return `${digits}@s.whatsapp.net`;
  }

  return `${uid}@s.whatsapp.net`;
}

/**
 * WhatsApp display name + phone when available (from pushName / @s.whatsapp.net alt).
 * @returns {{ pushName: string, phone: string }}
 */
function digitsFromPnOrJid(value) {
  if (!value || typeof value !== "string") return "";
  const digits = value.split("@")[0] || "";
  return /^\d{8,15}$/.test(digits) ? digits : "";
}

/** WhatsApp @lid internal ids are long numeric keys, not MSISDNs. */
export function isLikelyLidDigits(digits) {
  return typeof digits === "string" && digits.length >= 14;
}

export function contactMetaFromMessage(msg, dm) {
  const pushName = [
    typeof msg?.pushName === "string" ? msg.pushName : "",
    typeof msg?.verifiedBizName === "string" ? msg.verifiedBizName : "",
  ]
    .map((s) => s.trim())
    .find(Boolean) || "";

  const candidates = [
    digitsFromPnOrJid(msg?.key?.senderPn),
    digitsFromPnOrJid(msg?.key?.participantPn),
    digitsFromPnOrJid(dm?.userId),
    typeof msg?.key?.remoteJidAlt === "string" && msg.key.remoteJidAlt.endsWith("@s.whatsapp.net")
      ? digitsFromPnOrJid(msg.key.remoteJidAlt)
      : "",
  ];

  let phone = "";
  for (const d of candidates) {
    if (d && !isLikelyLidDigits(d)) {
      phone = d;
      break;
    }
  }

  return { pushName, phone };
}

/** Resolve session user id from a contact JID (for contacts.update events). */
export function userIdFromContactJid(jid) {
  const dm = resolveInboundDm({ remoteJid: jid });
  if (dm) return dm.userId;
  return userIdFromJid(jid);
}

export function messageType(msg) {
  try {
    return getContentType(msg.message);
  } catch {
    return undefined;
  }
}
