/**
 * Download inbound WhatsApp media to a temp file for Shadou STT / vision enrichment.
 */
import fs from "fs";
import os from "os";
import path from "path";
import { downloadMediaMessage } from "@whiskeysockets/baileys";
import pino from "pino";
import { messageType, mimetypeFromWAMessage } from "./message-text.mjs";

const log = pino({ level: process.env.LOG_LEVEL || "info" });

function extForMimetype(mimetype, modality) {
  const mt = String(mimetype || "").split(";")[0].trim().toLowerCase();
  const map = {
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/amr": "amr",
    "audio/webm": "webm",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
  };
  if (map[mt]) return map[mt];
  if (modality === "voice" || modality === "audio") return "ogg";
  if (modality === "image") return "jpg";
  return "bin";
}

/**
 * @param {import("@whiskeysockets/baileys").WASocket} sock
 * @param {import("@whiskeysockets/baileys").WAMessage} msg
 * @param {string} modality
 * @returns {Promise<{ path: string, mimetype: string, tmpDir: string }>}
 */
export async function downloadInboundMedia(sock, msg, modality) {
  const buffer = await downloadMediaMessage(
    msg,
    "buffer",
    {},
    {
      logger: pino({ level: "silent" }),
      reuploadRequest: sock.updateMediaMessage,
    },
  );
  if (!buffer?.length) {
    throw new Error("empty_media_buffer");
  }

  const mimetype = mimetypeFromWAMessage(msg);
  const ext = extForMimetype(mimetype, modality);
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "shadou-wa-media-"));
  const fileName = `${msg.key?.id || messageType(msg) || "media"}.${ext}`;
  const filePath = path.join(tmpDir, fileName);
  fs.writeFileSync(filePath, buffer);
  log.debug({ modality, mimetype, bytes: buffer.length, filePath }, "downloaded inbound media");
  return { path: filePath, mimetype, tmpDir };
}

/**
 * @param {string | undefined} tmpDir
 */
export function cleanupMediaTemp(tmpDir) {
  if (!tmpDir) return;
  try {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  } catch {
    /* ignore */
  }
}
